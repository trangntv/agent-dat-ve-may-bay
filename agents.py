"""Ba thiết kế tác tử LangGraph dùng chung mô hình giả, công cụ và lớp bảo vệ."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from flight_data import FLIGHTS_BY_ID
from harness import FlightHarness, FlightToolError, HarnessViolation
from mock_llm import MockFlightLLM
from tools import FlightService


class AgentState(TypedDict, total=False):
    """Lưu yêu cầu, kết quả công cụ, kế hoạch, giao dịch và trạng thái tác tử."""

    request: dict[str, Any]
    validation_errors: list[str]
    searched: bool
    search_results: list[dict[str, Any]]
    checked_seats: dict[str, dict[str, Any]]
    selected_flight_id: str | None
    action_flight_id: str | None
    booking_id: str | None
    payment_id: str | None
    tool_trace: list[dict[str, Any]]
    handoff_reason: str | None
    handoff: dict[str, Any] | None
    status: str
    action: str
    plan: list[str]
    plan_history: list[list[str]]
    decision_trace: list[dict[str, Any]]
    plan_index: int
    replan_count: int
    completion_message: str | None


AGENT_DESIGNS = ("react", "plan_then_execute", "hybrid")


def run_agent(design: str, request: dict[str, Any]) -> dict[str, Any]:
    """Chạy mẫu tác tử được chọn với kho dữ liệu, harness và mô hình giả riêng."""
    if design not in AGENT_DESIGNS:
        raise ValueError(f"Unknown agent design: {design}.")

    service = FlightService(request)
    harness = service.harness
    model = MockFlightLLM()
    if design == "plan_then_execute":
        graph = _build_plan_graph(service, harness, model)
    else:
        graph = _build_react_or_hybrid_graph(design, service, harness, model)

    initial_state: AgentState = {
        "request": dict(request),
        "validation_errors": [],
        "searched": False,
        "search_results": [],
        "checked_seats": {},
        "selected_flight_id": None,
        "action_flight_id": None,
        "booking_id": None,
        "payment_id": None,
        "tool_trace": [],
        "handoff_reason": None,
        "handoff": None,
        "status": "running",
        "plan": [],
        "plan_history": [],
        "decision_trace": [],
        "plan_index": 0,
        "replan_count": 0,
    }
    state = graph.invoke(initial_state, config={"recursion_limit": 100})
    return _format_result(design, state, service, model)


def _build_react_or_hybrid_graph(
    design: str,
    service: FlightService,
    harness: FlightHarness,
    model: MockFlightLLM,
):
    """Tạo graph ReAct hoặc Lai, nối các nút quyết định, công cụ và bàn giao."""
    builder = StateGraph(AgentState)
    builder.add_node("validate", _validate_node)

    def plan_node(state: AgentState) -> dict[str, Any]:
        """Sinh kế hoạch ban đầu cho tác tử Lai trước vòng quyết định thích ứng."""
        plan = model.complete("hybrid_plan", {"request": state["request"]})
        steps = plan.get("steps")
        if not isinstance(steps, list) or not all(isinstance(step, str) for step in steps):
            raise ValueError("Hybrid planner returned an invalid plan.")
        return {"plan": steps, "plan_history": [steps], "plan_index": 0}

    builder.add_node("plan", plan_node)
    builder.add_node("decide", _decision_node(design, model))
    builder.add_node("search", _search_node(service, harness))
    builder.add_node("check_seats", _check_seats_node(service))
    builder.add_node("create_booking", _booking_node(service))
    builder.add_node("pay_booking", _payment_node(service))
    builder.add_node("verify", _verify_node(harness, service))
    builder.add_node("handoff", _handoff_node(harness))

    builder.add_edge(START, "validate")
    builder.add_conditional_edges(
        "validate",
        lambda state: "handoff" if state.get("handoff_reason") else (
            "plan" if design == "hybrid" else "decide"
        ),
        {"handoff": "handoff", "plan": "plan", "decide": "decide"},
    )
    if design == "hybrid":
        builder.add_edge("plan", "decide")
    builder.add_conditional_edges(
        "decide",
        _dispatch_action,
        {
            "search": "search",
            "check_seats": "check_seats",
            "create_booking": "create_booking",
            "pay_booking": "pay_booking",
            "verify": "verify",
            "handoff": "handoff",
        },
    )
    for node in ("search", "check_seats", "create_booking", "pay_booking"):
        builder.add_edge(node, "decide")
    builder.add_conditional_edges(
        "verify",
        lambda state: "done" if state.get("status") == "completed" else "handoff",
        {"done": END, "handoff": "handoff"},
    )
    builder.add_edge("handoff", END)
    return builder.compile()


def _build_plan_graph(
    service: FlightService, harness: FlightHarness, model: MockFlightLLM
):
    """Tạo graph lập kế hoạch trước rồi thực thi từng bước đã được cho phép."""
    builder = StateGraph(AgentState)
    builder.add_node("validate", _validate_node)

    def make_plan(state: AgentState) -> dict[str, Any]:
        """Yêu cầu kế hoạch và từ chối các bước nằm ngoài danh sách nghiệp vụ."""
        result = model.complete("plan", {"request": state["request"]})
        steps = result.get("steps")
        allowed = {
            "search_flights",
            "check_all_candidates",
            "select_lowest_fare",
            "create_booking",
            "pay_booking",
            "verify_completion",
        }
        if not isinstance(steps, list) or not steps or any(step not in allowed for step in steps):
            raise ValueError("Planner returned steps outside the approved flight-booking plan.")
        return {"plan": steps, "plan_history": [steps], "plan_index": 0}

    builder.add_node("plan", make_plan)
    builder.add_node("execute_step", _execute_plan_step(service, harness))
    builder.add_node("handoff", _handoff_node(harness))
    builder.add_edge(START, "validate")
    builder.add_conditional_edges(
        "validate",
        lambda state: "handoff" if state.get("handoff_reason") else "plan",
        {"handoff": "handoff", "plan": "plan"},
    )
    builder.add_edge("plan", "execute_step")
    builder.add_conditional_edges(
        "execute_step",
        lambda state: (
            "handoff"
            if state.get("handoff_reason")
            else "done"
            if state.get("status") == "completed"
            else "execute"
        ),
        {"handoff": "handoff", "done": END, "execute": "execute_step"},
    )
    builder.add_edge("handoff", END)
    return builder.compile()


def _validate_node(state: AgentState) -> dict[str, Any]:
    """Xác thực đầu vào và đánh dấu bàn giao nếu yêu cầu thiếu hoặc sai định dạng."""
    errors = FlightHarness.validate_request(state["request"])
    if not errors:
        return {"validation_errors": []}
    reason = " ".join(errors)
    return {
        "validation_errors": errors,
        "handoff_reason": reason,
        "status": "handoff",
    }


def _decision_node(design: str, model: MockFlightLLM):
    """Tạo callback chọn bước kế tiếp; mẫu Lai đồng thời cập nhật kế hoạch còn lại."""
    operation = "react_decision" if design == "react" else "hybrid_decision"

    def decide(state: AgentState) -> dict[str, Any]:
        """Đưa trạng thái hiện tại cho mô hình giả và cập nhật quyết định vào graph."""
        answer = model.complete(operation, _decision_payload(state))
        action = answer.get("action")
        if not isinstance(action, str):
            raise ValueError(f"{design} decision did not return an action.")
        update: dict[str, Any] = {
            "action": action,
            "action_flight_id": answer.get("flight_id"),
            "handoff_reason": answer.get("reason") if action == "HANDOFF" else None,
            "decision_trace": [
                *state.get("decision_trace", []),
                {
                    "action": action,
                    "flight_id": answer.get("flight_id"),
                    "reason": answer.get("reason"),
                },
            ],
        }
        if design == "hybrid":
            revised_plan = answer.get("revised_plan")
            if not isinstance(revised_plan, list) or not all(
                isinstance(step, str) for step in revised_plan
            ):
                raise ValueError("Hybrid agent returned an invalid revised plan.")
            update["plan"] = revised_plan
            if revised_plan != state.get("plan", []):
                update["plan_history"] = [
                    *state.get("plan_history", []),
                    revised_plan,
                ]
        return update

    return decide


def _decision_payload(state: AgentState) -> dict[str, Any]:
    """Chọn các dữ kiện liên quan trong graph state để mô hình ra quyết định."""
    return {
        "request": state["request"],
        "searched": state.get("searched", False),
        "search_results": state.get("search_results", []),
        "checked_seats": state.get("checked_seats", {}),
        "selected_flight_id": state.get("selected_flight_id"),
        "booking_id": state.get("booking_id"),
        "payment_id": state.get("payment_id"),
        "plan": state.get("plan", []),
        "replan_count": state.get("replan_count", 0),
    }


def _dispatch_action(state: AgentState) -> str:
    """Ánh xạ hành động do mô hình chọn sang tên nút graph cần chạy."""
    action = state.get("action")
    routes = {
        "SEARCH_FLIGHTS": "search",
        "CHECK_SEATS": "check_seats",
        "CREATE_BOOKING": "create_booking",
        "PAY_BOOKING": "pay_booking",
        "VERIFY": "verify",
        "HANDOFF": "handoff",
    }
    if action not in routes:
        raise ValueError(f"Agent requested an unsupported action: {action!r}.")
    return routes[action]


def _search_node(service: FlightService, harness: FlightHarness):
    """Tạo callback tìm chuyến, kiểm chứng dữ liệu và ghi lại kết quả công cụ."""
    def search(state: AgentState) -> dict[str, Any]:
        """Gọi công cụ tìm chuyến với đúng yêu cầu đã được harness xác thực."""
        request = state["request"]
        args = {
            "origin": request["origin"],
            "destination": request["destination"],
            "travel_date": request["travel_date"],
            "budget_per_person": request["budget_per_person"],
        }
        try:
            result = service.invoke_tool("search_flights", args)
            if not isinstance(result, dict) or not isinstance(result.get("flights"), list):
                raise FlightToolError("Search tool returned an invalid response.")
            harness.validate_search_results(result["flights"], request)
        except (HarnessViolation, FlightToolError) as error:
            return _to_handoff(state, "search_flights", args, str(error))
        return {
            "searched": True,
            "search_results": result["flights"],
            "tool_trace": _append_trace(state, "search_flights", args, result),
        }

    return search


def _check_seats_node(service: FlightService):
    """Tạo callback kiểm tra ghế và lưu quyết định đủ chỗ vào graph state."""
    def check(state: AgentState) -> dict[str, Any]:
        """Kiểm tra sức chứa cho chuyến đang xét và ghi nhận lần thử."""
        flight_id = state.get("action_flight_id")
        args = {"flight_id": flight_id, "passengers": state["request"].get("passengers")}
        try:
            result = service.invoke_tool("check_seats", args)
            if not isinstance(result, dict):
                raise FlightToolError("Seat-check tool returned an invalid response.")
        except (HarnessViolation, FlightToolError) as error:
            return _to_handoff(state, "check_seats", args, str(error))

        checked = dict(state.get("checked_seats", {}))
        checked[str(flight_id)] = result
        update: dict[str, Any] = {
            "checked_seats": checked,
            "tool_trace": _append_trace(state, "check_seats", args, result),
        }
        if result.get("available") is True:
            update["selected_flight_id"] = str(flight_id)
        elif state.get("plan") and state.get("plan_index", 0) == 0:
            update["replan_count"] = state.get("replan_count", 0) + 1
        return update

    return check


def _booking_node(service: FlightService):
    """Tạo callback đặt chỗ sau khi dữ liệu, quyền và số ghế đã được kiểm tra."""
    def create(state: AgentState) -> dict[str, Any]:
        """Tạo booking giả lập và lưu mã đặt chỗ cùng nhật ký công cụ."""
        flight_id = state.get("selected_flight_id")
        args = {"flight_id": flight_id, "passengers": state["request"].get("passengers")}
        try:
            result = service.invoke_tool("create_booking", args)
            if not isinstance(result, dict) or not result.get("booking_id"):
                raise FlightToolError("Booking tool did not confirm a booking ID.")
        except (HarnessViolation, FlightToolError) as error:
            return _to_handoff(state, "create_booking", args, str(error))
        return {
            "booking_id": str(result["booking_id"]),
            "tool_trace": _append_trace(state, "create_booking", args, result),
        }

    return create


def _payment_node(service: FlightService):
    """Tạo callback thanh toán giả lập cho booking đã được harness cho phép."""
    def pay(state: AgentState) -> dict[str, Any]:
        """Thanh toán booking hiện tại và lưu mã giao dịch vào graph state."""
        args = {"booking_id": state.get("booking_id")}
        try:
            result = service.invoke_tool("pay_booking", args)
            if not isinstance(result, dict) or not result.get("payment_id"):
                raise FlightToolError("Payment tool did not confirm a payment ID.")
        except (HarnessViolation, FlightToolError) as error:
            return _to_handoff(state, "pay_booking", args, str(error))
        return {
            "payment_id": str(result["payment_id"]),
            "tool_trace": _append_trace(state, "pay_booking", args, result),
        }

    return pay


def _verify_node(harness: FlightHarness, service: FlightService):
    """Tạo callback kiểm tra bằng mã liệu booking và thanh toán đã hoàn tất."""
    def verify(state: AgentState) -> dict[str, Any]:
        """Đặt trạng thái hoàn tất chỉ khi booking và payment đạt mọi điều kiện."""
        booking = service.bookings.get(str(state.get("booking_id")))
        payment = service.payments.get(str(state.get("payment_id")))
        completed, message = harness.verify_completion(state["request"], booking, payment)
        return {
            "status": "completed" if completed else "handoff",
            "completion_message": message,
            "handoff_reason": None if completed else message,
        }

    return verify


def _execute_plan_step(service: FlightService, harness: FlightHarness):
    """Tạo bộ thực thi từng bước kế hoạch và dừng khi lỗi hoặc cần bàn giao."""
    def execute(state: AgentState) -> dict[str, Any]:
        """Thực hiện bước hiện tại, cập nhật trạng thái và tăng chỉ số kế hoạch."""
        plan = state.get("plan", [])
        index = state.get("plan_index", 0)
        if index >= len(plan):
            return {
                "status": "handoff",
                "handoff_reason": "Kế hoạch kết thúc nhưng tiêu chí hoàn thành chưa đạt.",
            }

        step = plan[index]
        request = state["request"]
        if step == "search_flights":
            args = {
                "origin": request["origin"],
                "destination": request["destination"],
                "travel_date": request["travel_date"],
                "budget_per_person": request["budget_per_person"],
            }
            try:
                result = service.invoke_tool(step, args)
                harness.validate_search_results(result["flights"], request)
            except (HarnessViolation, FlightToolError) as error:
                return _to_handoff(state, step, args, str(error))
            if not result["flights"]:
                return {
                    "searched": True,
                    "search_results": [],
                    "handoff_reason": "Không tìm thấy chuyến trong ngân sách mỗi hành khách.",
                    "status": "handoff",
                    "plan_index": index + 1,
                    "tool_trace": _append_trace(state, step, args, result),
                }
            return {
                "searched": True,
                "search_results": result["flights"],
                "plan_index": index + 1,
                "tool_trace": _append_trace(state, step, args, result),
            }

        if step == "check_all_candidates":
            checked = dict(state.get("checked_seats", {}))
            next_flight = next(
                (
                    row["flight_id"]
                    for row in state.get("search_results", [])
                    if row["flight_id"] not in checked
                ),
                None,
            )
            if next_flight is None:
                return {"plan_index": index + 1}
            args = {"flight_id": next_flight, "passengers": request["passengers"]}
            try:
                result = service.invoke_tool("check_seats", args)
            except (HarnessViolation, FlightToolError) as error:
                return _to_handoff(state, step, args, str(error))
            checked[next_flight] = result
            return {
                "checked_seats": checked,
                "tool_trace": _append_trace(state, "check_seats", args, result),
            }

        if step == "select_lowest_fare":
            eligible = [
                row
                for row in state.get("search_results", [])
                if state.get("checked_seats", {}).get(row["flight_id"], {}).get("available")
            ]
            if not eligible:
                return _to_handoff(
                    state, step, {}, "Không có chuyến nào còn đủ ghế cho số hành khách."
                )
            selected = min(eligible, key=lambda row: (row["price_per_person"], row["departure_time"]))
            return {"selected_flight_id": selected["flight_id"], "plan_index": index + 1}

        if step == "create_booking":
            flight_id = state.get("selected_flight_id")
            args = {"flight_id": flight_id, "passengers": request["passengers"]}
            try:
                result = service.invoke_tool(step, args)
            except (HarnessViolation, FlightToolError) as error:
                return _to_handoff(state, step, args, str(error))
            return {
                "booking_id": result["booking_id"],
                "plan_index": index + 1,
                "tool_trace": _append_trace(state, step, args, result),
            }

        if step == "pay_booking":
            args = {"booking_id": state.get("booking_id")}
            try:
                result = service.invoke_tool(step, args)
            except (HarnessViolation, FlightToolError) as error:
                return _to_handoff(state, step, args, str(error))
            return {
                "payment_id": result["payment_id"],
                "plan_index": index + 1,
                "tool_trace": _append_trace(state, step, args, result),
            }

        if step == "verify_completion":
            booking = service.bookings.get(str(state.get("booking_id")))
            payment = service.payments.get(str(state.get("payment_id")))
            completed, message = harness.verify_completion(request, booking, payment)
            return {
                "status": "completed" if completed else "handoff",
                "completion_message": message,
                "handoff_reason": None if completed else message,
                "plan_index": index + 1,
            }

        raise ValueError(f"Unsupported plan step: {step}.")

    return execute


def _handoff_node(harness: FlightHarness):
    """Tạo callback kết thúc graph bằng gói bàn giao có ngữ cảnh cho người dùng."""
    def handoff(state: AgentState) -> dict[str, Any]:
        """Tổng hợp lý do, lịch sử thao tác, trạng thái và câu hỏi cần làm rõ."""
        reason = state.get("handoff_reason") or "Agent cần người dùng quyết định bước tiếp theo."
        search_results = state.get("search_results", [])
        checked_seats = state.get("checked_seats", {})
        no_feasible_flight = state.get("searched", False) and (
            not search_results
            or (
                all(row["flight_id"] in checked_seats for row in search_results)
                and not any(
                    check.get("available") is True
                    for check in checked_seats.values()
                )
            )
        )
        if no_feasible_flight:
            question = None
            next_step = (
                "Không cần cung cấp thêm thông tin. Hãy tự đặt vé qua hãng hàng không "
                "hoặc đại lý phù hợp; agent không thể đặt chuyến theo các điều kiện hiện tại."
            )
        else:
            question = harness.clarification_question(state["request"])
            next_step = "Vui lòng trả lời câu hỏi làm rõ để agent có thể tiếp tục."
        package = harness.handoff(
            reason,
            state.get("tool_trace", []),
            question=question,
            next_step=next_step,
        )
        return {"status": "handoff", "handoff": package}

    return handoff


def _to_handoff(
    state: AgentState, tool_name: str, arguments: dict[str, Any], reason: str
) -> dict[str, Any]:
    """Đánh dấu trạng thái cần bàn giao và thêm lỗi công cụ vào nhật ký."""
    return {
        "handoff_reason": reason,
        "status": "handoff",
        "tool_trace": _append_trace(
            state,
            tool_name,
            arguments,
            {"status": "error", "error": reason},
        ),
    }


def _append_trace(
    state: AgentState, tool_name: str, arguments: dict[str, Any], result: Any
) -> list[dict[str, Any]]:
    """Tạo nhật ký mới có thêm tên công cụ, tham số và kết quả vừa nhận."""
    trace = list(state.get("tool_trace", []))
    trace.append({"tool": tool_name, "arguments": arguments, "result": result})
    return trace


def _format_result(
    design: str,
    state: AgentState,
    service: FlightService,
    model: MockFlightLLM,
) -> dict[str, Any]:
    """Tổng hợp lựa chọn, giao dịch, bàn giao, nhật ký và số liệu đánh giá."""
    booking = service.bookings.get(str(state.get("booking_id")))
    payment = service.payments.get(str(state.get("payment_id")))
    selected = FLIGHTS_BY_ID.get(str(state.get("selected_flight_id")))
    return {
        "design": design,
        "status": state.get("status", "handoff"),
        "request": state["request"],
        "validation_errors": state.get("validation_errors", []),
        "searched": state.get("searched", False),
        "selected_flight": selected.to_dict() if selected else None,
        "flight_options": [
            {
                **row,
                "seat_check": state.get("checked_seats", {}).get(row["flight_id"]),
            }
            for row in state.get("search_results", [])
        ],
        "booking": (
            {
                "booking_id": booking.booking_id,
                "flight_id": booking.flight_id,
                "passengers": booking.passengers,
                "total_amount": booking.total_amount,
                "status": booking.status,
            }
            if booking
            else None
        ),
        "payment": (
            {
                "payment_id": payment.payment_id,
                "booking_id": payment.booking_id,
                "amount": payment.amount,
                "status": payment.status,
            }
            if payment
            else None
        ),
        "handoff": state.get("handoff"),
        "handoff_reason": state.get("handoff_reason"),
        "completion_message": state.get("completion_message"),
        "tool_trace": state.get("tool_trace", []),
        "plan": state.get("plan", []),
        "plan_history": state.get("plan_history", []),
        "decision_trace": state.get("decision_trace", []),
        "metrics": {
            "llm_calls": model.call_count,
            "tool_calls": len(state.get("tool_trace", [])),
            "replans": state.get("replan_count", 0),
        },
    }
