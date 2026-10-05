"""Chuyển kết quả nội bộ sang nội dung tiếng Việt dành cho người dùng."""

from __future__ import annotations

from typing import Any

from domain import DESIGN_LABELS, SCENARIO_LABELS


STATUS_LABELS = {
    "running": "đang xử lý",
    "completed": "đã hoàn tất",
    "handoff": "cần người dùng xử lý",
    "reserved": "đang giữ chỗ",
    "paid": "đã thanh toán",
    "succeeded": "thành công",
    "ok": "thành công",
    "error": "lỗi",
}

FIELD_LABELS = {
    "origin": "sân_bay_đi",
    "destination": "sân_bay_đến",
    "travel_date": "ngày_bay",
    "passengers": "số_hành_khách",
    "budget_per_person": "ngân_sách_tối_đa_mỗi_người",
    "auto_purchase": "cho_phép_tự_đặt_và_thanh_toán",
    "flight_id": "mã_chuyến_bay",
    "airline": "hãng_bay",
    "departure_date": "ngày_khởi_hành",
    "departure_time": "giờ_khởi_hành",
    "arrival_time": "giờ_đến",
    "price_per_person": "giá_vé_mỗi_người",
    "seats_available": "số_ghế_còn_lại_theo_dữ_liệu",
    "required": "số_ghế_cần",
    "seats_remaining": "số_ghế_còn_lại",
    "available": "còn_đủ_ghế",
    "count": "số_chuyến",
    "flights": "các_chuyến_bay",
    "status": "trạng_thái",
    "booking_id": "mã_đặt_chỗ",
    "total_amount": "tổng_tiền",
    "payment_id": "mã_thanh_toán",
    "amount": "số_tiền",
    "reason": "lý_do",
    "error": "lỗi",
}

TOOL_LABELS = {
    "search_flights": "tìm_chuyến_bay",
    "check_seats": "kiểm_tra_chỗ",
    "create_booking": "tạo_đặt_chỗ",
    "pay_booking": "thanh_toán_mô_phỏng",
}

ACTION_LABELS = {
    "SEARCH_FLIGHTS": "Tìm chuyến phù hợp",
    "CHECK_SEATS": "Kiểm tra số ghế còn lại",
    "CREATE_BOOKING": "Tạo đặt chỗ",
    "PAY_BOOKING": "Thanh toán mô phỏng",
    "VERIFY": "Kiểm tra điều kiện hoàn tất",
    "HANDOFF": "Bàn giao cho khách hàng",
}

PLAN_STEP_LABELS = {
    "search_flights": "Tìm chuyến theo hành trình, ngày bay và ngân sách",
    "check_all_candidates": "Kiểm tra số ghế của các chuyến phù hợp",
    "select_lowest_fare": "Chọn chuyến rẻ nhất còn đủ ghế",
    "check_seats": "Kiểm tra ghế chuyến đang xét",
    "create_booking": "Tạo đặt chỗ mô phỏng",
    "pay_booking": "Thanh toán mô phỏng",
    "verify_completion": "Xác minh hoàn tất bằng harness",
}

METRIC_LABELS = {
    "llm_calls": "số_lượt_mô_hình_ngôn_ngữ_giả",
    "tool_calls": "số_lượt_gọi_công_cụ",
    "replans": "số_lần_điều_chỉnh_kế_hoạch",
}

RESULT_LABELS = {
    "request": "yêu_cầu",
    "selected_flight": "chuyến_được_chọn",
    "flight_options": "các_lựa_chọn_chuyến_bay",
    "booking": "đặt_chỗ",
    "payment": "thanh_toán",
    "handoff": "bàn_giao",
    "handoff_reason": "lý_do_cần_bàn_giao",
    "completion_message": "xác_nhận_hoàn_tất",
    "tool_trace": "nhật_ký_công_cụ",
    "metrics": "số_liệu",
    "reason": "lý_do",
    "actions_attempted": "các_công_cụ_đã_thử",
    "current_state": "trạng_thái_hiện_tại",
    "question_for_user": "câu_hỏi_cho_bạn",
    "next_step": "bước_tiếp_theo",
    "decision_trace": "quyết_định_tác_tử",
    "plan_history": "lịch_sử_kế_hoạch",
    "plan": "kế_hoạch",
    "action": "hành_động",
    "tool": "công_cụ",
    "arguments": "tham_số",
    "result": "kết_quả",
    "required": "số_ghế_cần",
    "seats_remaining": "số_ghế_còn_lại",
    "available": "còn_đủ_ghế",
}


def localize_value(value: Any, *, parent_key: str | None = None) -> Any:
    """Dịch nhãn và các giá trị trạng thái trong cấu trúc kết quả sang tiếng Việt."""
    if isinstance(value, dict):
        localized: dict[str, Any] = {}
        for key, child in value.items():
            label = RESULT_LABELS.get(key, FIELD_LABELS.get(key, key))
            localized[label] = localize_value(child, parent_key=key)
        return localized
    if isinstance(value, list):
        if parent_key in {"plan", "plan_history"}:
            return [
                [PLAN_STEP_LABELS.get(step, step) for step in item]
                if isinstance(item, list)
                else PLAN_STEP_LABELS.get(item, item)
                for item in value
            ]
        return [localize_value(item, parent_key=parent_key) for item in value]
    if parent_key == "action" and isinstance(value, str):
        return ACTION_LABELS.get(value, value)
    if parent_key == "status" and isinstance(value, str):
        return STATUS_LABELS.get(value, value)
    if parent_key == "tool" and isinstance(value, str):
        return TOOL_LABELS.get(value, value)
    if parent_key == "available" and isinstance(value, bool):
        return "có" if value else "không"
    if parent_key == "auto_purchase" and isinstance(value, bool):
        return "có" if value else "không"
    return value


def _format_vnd(amount: int) -> str:
    """Định dạng số tiền nguyên theo quy ước phân tách hàng nghìn của Việt Nam."""
    return f"{amount:,}".replace(",", ".")


def format_result_vi(result: dict[str, Any]) -> dict[str, Any]:
    """Tạo câu trả lời có nhãn, trạng thái và chi tiết hoàn toàn bằng tiếng Việt."""
    status = result.get("status")
    if status == "completed":
        flight = result.get("selected_flight") or {}
        booking = result.get("booking") or {}
        answer = (
            f"Đã đặt và thanh toán thành công chuyến {flight.get('flight_id')} "
            f"của {flight.get('airline')}, giá "
            f"{_format_vnd(flight.get('price_per_person', 0))} VND/người; "
            f"tổng tiền {_format_vnd(booking.get('total_amount', 0))} VND."
        )
    else:
        answer = result.get("handoff_reason") or "Chưa thể hoàn tất yêu cầu đặt vé."

    localized_metrics = {
        METRIC_LABELS.get(key, key): value
        for key, value in result.get("metrics", {}).items()
    }
    localized_flight_options = localize_value(result.get("flight_options", []))
    return {
        "mẫu_tác_tử": DESIGN_LABELS.get(result.get("design"), result.get("design")),
        "trạng_thái": STATUS_LABELS.get(status, status),
        "câu_trả_lời": answer,
        "yêu_cầu": localize_value(result.get("request", {})),
        "các_lựa_chọn_chuyến_bay": localized_flight_options,
        "chuyến_được_chọn": localize_value(result.get("selected_flight")),
        "đặt_chỗ": localize_value(result.get("booking")),
        "thanh_toán": localize_value(result.get("payment")),
        "bàn_giao": localize_value(result.get("handoff")),
        "lý_do_cần_bàn_giao": result.get("handoff_reason"),
        "xác_nhận_hoàn_tất": result.get("completion_message"),
        "nhật_ký_công_cụ": localize_value(result.get("tool_trace", [])),
        "kế_hoạch": localize_value(result.get("plan", []), parent_key="plan"),
        "lịch_sử_kế_hoạch": localize_value(
            result.get("plan_history", []), parent_key="plan_history"
        ),
        "quyết_định_tác_tử": localize_value(result.get("decision_trace", [])),
        "số_liệu": localized_metrics,
    }


def _format_tool_event(event: dict[str, Any], index: int) -> str:
    """Tóm tắt một lần gọi công cụ theo dữ liệu thực tế trong nhật ký."""
    tool = event.get("tool")
    result = event.get("result", {})
    name = TOOL_LABELS.get(tool, str(tool))
    if result.get("status") == "error":
        return f"{index}. {name}: bị chặn/lỗi — {result.get('error')}"
    if tool == "search_flights":
        flights = result.get("flights", [])
        if not flights:
            detail = "không tìm thấy chuyến thỏa điều kiện."
        else:
            detail = f"tìm thấy {len(flights)} chuyến: " + ", ".join(
                f"{flight['flight_id']} ({_format_vnd(flight['price_per_person'])} VND/người)"
                for flight in flights
            )
        return f"{index}. {name}: {detail}"
    if tool == "check_seats":
        available = "đủ ghế" if result.get("available") else "không đủ ghế"
        return (
            f"{index}. {name} {result.get('flight_id')}: "
            f"{result.get('seats_remaining')} ghế còn / "
            f"{result.get('required')} khách cần — {available}."
        )
    if tool == "create_booking":
        return (
            f"{index}. {name}: mã {result.get('booking_id')}, "
            f"{_format_vnd(result.get('total_amount', 0))} VND, "
            f"{result.get('passengers')} hành khách."
        )
    if tool == "pay_booking":
        return (
            f"{index}. {name}: mã giao dịch {result.get('payment_id')}, "
            f"trạng thái {STATUS_LABELS.get(result.get('status'), result.get('status'))}."
        )
    return f"{index}. {name}: {result}"


def format_run_terminal(result: dict[str, Any], *, title: str | None = None) -> str:
    """Định dạng tiến trình, công cụ, kết quả harness và bàn giao cho terminal."""
    design = DESIGN_LABELS.get(result.get("design"), result.get("design"))
    request = result.get("request", {})
    handoff = result.get("handoff") or {}
    lines = [
        "=" * 78,
        title or f"{scenario_label(result.get('scenario', ''))} — {design}",
        "=" * 78,
        "YÊU CẦU",
        (
            f"  {request.get('origin', '—')} → {request.get('destination', '—')} | "
            f"Ngày: {request.get('travel_date', '—')} | "
            f"Hành khách: {request.get('passengers', 'chưa cung cấp')} | "
            f"Ngân sách: "
            f"{_format_vnd(request['budget_per_person']) + ' VND/người' if request.get('budget_per_person') is not None else 'chưa cung cấp'}"
        ),
        "",
        "KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH",
    ]
    if result.get("design") == "react":
        lines.append("  ReAct không lập kế hoạch cố định; MockLLM chọn hành động dựa trên kết quả từng bước.")
    else:
        histories = result.get("plan_history") or ([result.get("plan", [])] if result.get("plan") else [])
        if not histories:
            lines.append("  Chưa lập kế hoạch vì yêu cầu không qua kiểm tra đầu vào.")
        else:
            for history_index, plan in enumerate(histories, start=1):
                prefix = "Kế hoạch" if history_index == 1 else f"Kế hoạch điều chỉnh {history_index - 1}"
                lines.append(f"  {prefix}:")
                for step_index, step in enumerate(plan, start=1):
                    label = PLAN_STEP_LABELS.get(step, step.replace("_", " "))
                    lines.append(f"    {step_index}. {label}")
        if result.get("design") == "hybrid":
            lines.append("  Lai: cập nhật bước tiếp theo khi có kết quả quan sát mới.")

    decisions = result.get("decision_trace", [])
    if decisions:
        lines.extend(["", "QUYẾT ĐỊNH / HÀNH ĐỘNG CỦA TÁC TỬ"])
        for index, decision in enumerate(decisions, start=1):
            action = ACTION_LABELS.get(decision.get("action"), decision.get("action"))
            flight_id = decision.get("flight_id")
            detail = f" — chuyến {flight_id}" if flight_id else ""
            reason = decision.get("reason")
            if reason:
                detail += f" — {reason}"
            lines.append(f"  {index}. {action}{detail}")

    lines.extend(["", "THỰC THI CÔNG CỤ"])
    trace = result.get("tool_trace", [])
    if trace:
        lines.extend(f"  {line}" for line in (
            _format_tool_event(event, index)
            for index, event in enumerate(trace, start=1)
        ))
    else:
        lines.append("  Không gọi công cụ.")

    validation_errors = result.get("validation_errors", [])
    lines.extend(
        [
            "",
            "KẾT QUẢ KIỂM TRA HARNESS",
            f"  1. Ràng buộc đầu vào: {'KHÔNG ĐẠT' if validation_errors else 'ĐẠT'}"
            + (f" — {' '.join(validation_errors)}" if validation_errors else ""),
            f"  2. Ràng buộc dữ liệu chuyến: "
            f"{'ĐẠT' if result.get('searched') else 'Không áp dụng/chưa tìm chuyến'}",
            f"  3. Phân quyền đặt và thanh toán: "
            f"{'ĐẠT' if result.get('booking') and result.get('payment') else 'Không thực hiện' + (' do yêu cầu đầu vào không hợp lệ' if validation_errors else ' do không có chuyến đủ điều kiện')}",
            f"  4. Tiêu chí hoàn tất bằng mã: "
            f"{'ĐẠT' if result.get('status') == 'completed' else 'CHƯA ĐẠT'}"
            + (f" — {result.get('completion_message')}" if result.get("completion_message") else ""),
        ]
    )
    lines.extend(["", "KẾT QUẢ"])
    if result.get("status") == "completed":
        flight = result.get("selected_flight") or {}
        booking = result.get("booking") or {}
        lines.append(
            f"  ĐẶT VÉ THÀNH CÔNG: {flight.get('flight_id')} — {flight.get('airline')}, "
            f"{_format_vnd(flight.get('price_per_person', 0))} VND/người; "
            f"tổng {_format_vnd(booking.get('total_amount', 0))} VND."
        )
    else:
        lines.append(f"  CHƯA ĐẶT VÉ: {result.get('handoff_reason') or 'Cần người dùng xử lý.'}")
        if handoff.get("question_for_user"):
            lines.append(f"  Câu hỏi làm rõ: {handoff['question_for_user']}")
        if handoff.get("next_step"):
            lines.append(f"  Bàn giao: {handoff['next_step']}")
    metrics = result.get("metrics", {})
    lines.extend(
        [
            "",
            "SỐ LIỆU",
            f"  MockLLM: {metrics.get('llm_calls', 0)} lượt | "
            f"Công cụ: {metrics.get('tool_calls', 0)} lượt | "
            f"Điều chỉnh kế hoạch: {metrics.get('replans', 0)}",
        ]
    )
    return "\n".join(lines)


def format_evaluation_terminal(results: list[dict[str, Any]]) -> str:
    """In bảng so sánh tổng quan và tiến trình có cấu trúc của từng lượt."""
    lines = [
        "SO SÁNH TỔNG QUAN — 3 THIẾT KẾ × CÁC TÌNH HUỐNG",
        "-" * 78,
        f"{'Tình huống':38} {'Thiết kế':31} {'Trạng thái':22} "
        f"{'LLM':>4} {'Tools':>5} {'Replan':>6}",
        "-" * 112,
    ]
    for result in results:
        lines.append(
            f"{scenario_label(result['scenario']):38} "
            f"{DESIGN_LABELS.get(result['design'], result['design']):31} "
            f"{STATUS_LABELS.get(result['status'], result['status']):22} "
            f"{result['metrics']['llm_calls']:>4} "
            f"{result['metrics']['tool_calls']:>5} "
            f"{result['metrics']['replans']:>6}"
        )
    lines.append("")
    for index, result in enumerate(results, start=1):
        title = (
            f"LƯỢT {index}/9 — {scenario_label(result['scenario'])} — "
            f"{DESIGN_LABELS.get(result['design'], result['design'])}"
        )
        lines.append(format_run_terminal(result, title=title))
        lines.append("")
    return "\n".join(lines)


def scenario_label(name: str) -> str:
    """Trả tên tiếng Việt dễ đọc cho mã kịch bản đánh giá."""
    return SCENARIO_LABELS.get(name, name)


def status_label(status: str) -> str:
    """Trả nhãn tiếng Việt dễ đọc cho trạng thái nội bộ."""
    return STATUS_LABELS.get(status, status)
