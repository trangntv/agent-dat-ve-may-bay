"""Mô hình hội thoại LangChain giả lập, xác định, thay cho dịch vụ LLM bên ngoài."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr


class MockFlightLLM(BaseChatModel):
    """Chính sách theo kịch bản có thể tái lập; không suy luận tổng quát."""

    _call_count: int = PrivateAttr(default=0)

    @property
    def call_count(self) -> int:
        """Trả số lần mô hình giả đã tạo quyết định."""
        return self._call_count

    @property
    def _llm_type(self) -> str:
        """Cung cấp định danh mô hình theo giao diện BaseChatModel."""
        return "se373-deterministic-flight-mock"

    def complete(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Gửi thao tác và dữ liệu có cấu trúc vào mô hình, rồi đọc câu trả lời JSON."""
        response = self.invoke(
            [
                SystemMessage(content=f"OP={operation}"),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]
        )
        if not isinstance(response, AIMessage):
            raise TypeError("MockFlightLLM returned an unexpected message type.")
        value = json.loads(str(response.content))
        if not isinstance(value, dict):
            raise ValueError("MockFlightLLM response must be a JSON object.")
        return value

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Triển khai điểm sinh phản hồi LangChain theo thao tác được yêu cầu."""
        del stop, run_manager, kwargs
        self._call_count += 1
        operation = next(
            (
                str(message.content).removeprefix("OP=")
                for message in messages
                if isinstance(message, SystemMessage)
                and str(message.content).startswith("OP=")
            ),
            None,
        )
        prompt = next(
            (str(message.content) for message in reversed(messages) if isinstance(message, HumanMessage)),
            None,
        )
        if operation is None or prompt is None:
            raise ValueError("MockFlightLLM expects an operation and JSON payload.")
        payload = json.loads(prompt)
        if not isinstance(payload, dict):
            raise ValueError("MockFlightLLM payload must be a JSON object.")

        if operation == "plan":
            answer = {
                "steps": [
                    "search_flights",
                    "check_all_candidates",
                    "select_lowest_fare",
                    "create_booking",
                    "pay_booking",
                    "verify_completion",
                ]
            }
        elif operation == "hybrid_plan":
            answer = {
                "steps": ["search_flights", "check_seats", "create_booking", "pay_booking"],
                "adapt_after_each_observation": True,
            }
        elif operation in {"react_decision", "hybrid_decision"}:
            answer = self._choose_action(payload)
            if operation == "hybrid_decision":
                answer["revised_plan"] = self._revise_plan(
                    payload,
                    answer["action"],
                    flight_id=answer.get("flight_id"),
                )
        else:
            raise ValueError(f"Unsupported MockFlightLLM operation: {operation}.")

        message = AIMessage(content=json.dumps(answer, ensure_ascii=False))
        return ChatResult(generations=[ChatGeneration(message=message)])

    @staticmethod
    def _choose_action(payload: dict[str, Any]) -> dict[str, Any]:
        """Chọn hành động ReAct kế tiếp từ kết quả tìm kiếm, ghế và giao dịch."""
        if payload.get("payment_id"):
            return {"action": "VERIFY"}
        if payload.get("booking_id"):
            return {"action": "PAY_BOOKING"}
        if payload.get("selected_flight_id"):
            return {"action": "CREATE_BOOKING"}
        if not payload.get("searched"):
            return {"action": "SEARCH_FLIGHTS"}

        flights = payload.get("search_results", [])
        if not flights:
            return {"action": "HANDOFF", "reason": "Không tìm thấy chuyến trong ngân sách."}

        checked = payload.get("checked_seats", {})
        for flight in flights:
            flight_id = flight["flight_id"]
            if flight_id not in checked:
                return {"action": "CHECK_SEATS", "flight_id": flight_id}
            if checked[flight_id].get("available") is True:
                return {"action": "CREATE_BOOKING", "flight_id": flight_id}

        return {
            "action": "HANDOFF",
            "reason": "Các chuyến trong ngân sách đều không còn đủ ghế.",
        }

    @staticmethod
    def _revise_plan(
        payload: dict[str, Any],
        action: str,
        *,
        flight_id: str | None = None,
    ) -> list[str]:
        """Điều chỉnh các bước dự kiến của mẫu Lai sau kết quả quan sát mới."""
        if action == "SEARCH_FLIGHTS":
            return ["search_flights", "check_seats", "create_booking", "pay_booking"]
        if action == "CHECK_SEATS":
            return [
                f"check_seats:{flight_id}",
                "reassess_candidates",
                "create_booking",
                "pay_booking",
                "verify_completion",
            ]
        if action == "CREATE_BOOKING":
            return ["create_booking", "pay_booking", "verify_completion"]
        if action == "PAY_BOOKING":
            return ["pay_booking", "verify_completion"]
        if action == "VERIFY":
            return ["verify_completion"]
        return ["handoff"]
