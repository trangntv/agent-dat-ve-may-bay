"""Bốn lớp bảo vệ: ràng buộc dữ liệu, kiểm tra hoàn tất, phân quyền và bàn giao."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from domain import Booking, Flight, Payment


class HarnessViolation(Exception):
    """Báo hành động của tác tử vi phạm dữ liệu, quyền hoặc quy tắc đặt vé."""


class FlightToolError(Exception):
    """Báo công cụ giả lập không thể hoàn thành thao tác được yêu cầu."""


class FlightHarness:
    """Thực thi các kiểm tra dữ liệu, quyền mua, hoàn tất và bàn giao."""

    def __init__(self, flights_by_id: dict[str, Flight]) -> None:
        """Lưu kho chuyến bay chuẩn dùng để xác minh mọi kết quả và giao dịch."""
        self.flights_by_id = flights_by_id

    @staticmethod
    def validate_request(request: dict[str, Any]) -> list[str]:
        """Kiểm tra trường bắt buộc và định dạng trước khi cho phép chạy công cụ."""
        errors: list[str] = []
        for key in ("origin", "destination", "travel_date", "passengers", "budget_per_person"):
            if request.get(key) in (None, ""):
                errors.append(f"Thiếu thông tin bắt buộc: {key}.")

        origin = request.get("origin")
        destination = request.get("destination")
        if origin and not re.fullmatch(r"[A-Z]{3}", str(origin)):
            errors.append("Sân bay đi phải là mã IATA gồm ba chữ in hoa.")
        if destination and not re.fullmatch(r"[A-Z]{3}", str(destination)):
            errors.append("Sân bay đến phải là mã IATA gồm ba chữ in hoa.")
        if origin and destination and origin == destination:
            errors.append("Sân bay đi và đến không được trùng nhau.")

        travel_date = request.get("travel_date")
        if travel_date:
            try:
                date.fromisoformat(str(travel_date))
            except ValueError:
                errors.append("Ngày bay phải theo định dạng YYYY-MM-DD.")

        passengers = request.get("passengers")
        if passengers is not None and (
            isinstance(passengers, bool) or not isinstance(passengers, int) or not 1 <= passengers <= 6
        ):
            errors.append("Số hành khách phải là số nguyên từ 1 đến 6.")

        budget = request.get("budget_per_person")
        if budget is not None and (
            isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0
        ):
            errors.append("Ngân sách mỗi hành khách phải là số nguyên dương.")

        if request.get("auto_purchase") is not True:
            errors.append("Yêu cầu chưa cho phép agent tự đặt vé và thanh toán.")
        return errors

    def validate_search_results(
        self, rows: list[dict[str, Any]], request: dict[str, Any]
    ) -> None:
        """Đối chiếu kết quả tìm kiếm với kho chuẩn, hành trình, ngày và ngân sách."""
        seen: set[str] = set()
        for row in rows:
            flight_id = row.get("flight_id")
            flight = self.flights_by_id.get(str(flight_id))
            if flight is None:
                raise HarnessViolation(f"Dữ liệu chuyến bay không tồn tại: {flight_id!r}.")
            if flight_id in seen:
                raise HarnessViolation(f"Kết quả tìm kiếm bị trùng chuyến: {flight_id}.")
            seen.add(str(flight_id))
            if row != flight.to_dict():
                raise HarnessViolation(f"Thông tin chuyến {flight_id} không khớp dữ liệu chuẩn.")
            if (flight.origin, flight.destination, flight.departure_date) != (
                request["origin"],
                request["destination"],
                request["travel_date"],
            ):
                raise HarnessViolation(f"Chuyến {flight_id} không khớp hành trình/ngày yêu cầu.")
            if flight.price_per_person > request["budget_per_person"]:
                raise HarnessViolation(f"Chuyến {flight_id} vượt ngân sách mỗi hành khách.")

    def authorize(
        self,
        action: str,
        request: dict[str, Any],
        *,
        flight_id: str | None = None,
        search_results: list[dict[str, Any]] | None = None,
        checked_seats: dict[str, dict[str, Any]] | None = None,
        booking: Booking | None = None,
    ) -> None:
        """Chặn hành động nếu thiếu quyền, thiếu căn cứ chuyến hoặc vi phạm ngân sách."""
        if action in {"create_booking", "pay_booking"} and request.get("auto_purchase") is not True:
            raise HarnessViolation("Không được đặt hoặc thanh toán khi khách chưa cho phép tự động.")

        if action == "search_flights":
            if FlightHarness.validate_request(request):
                raise HarnessViolation("Không thể tìm chuyến khi yêu cầu còn thiếu hoặc không hợp lệ.")
            return

        if action == "check_seats":
            self._require_search_candidate(flight_id, search_results)
            if request.get("passengers") is None:
                raise HarnessViolation("Thiếu số hành khách để kiểm tra ghế.")
            return

        if action == "create_booking":
            flight = self._require_search_candidate(flight_id, search_results)
            seat_check = (checked_seats or {}).get(str(flight_id))
            if not seat_check or seat_check.get("available") is not True:
                raise HarnessViolation("Chỉ được đặt chuyến đã kiểm tra và còn đủ ghế.")
            if seat_check.get("required") != request["passengers"]:
                raise HarnessViolation("Số ghế kiểm tra không khớp số hành khách.")
            if flight.price_per_person > request["budget_per_person"]:
                raise HarnessViolation("Giá vé vượt ngân sách tối đa mỗi hành khách.")
            return

        if action == "pay_booking":
            if booking is None:
                raise HarnessViolation("Không tìm thấy booking cần thanh toán.")
            if booking.status != "reserved":
                raise HarnessViolation("Chỉ booking đang giữ chỗ mới được thanh toán.")
            flight = self.flights_by_id.get(booking.flight_id)
            if flight is None or flight.price_per_person > request["budget_per_person"]:
                raise HarnessViolation("Booking không nằm trong phạm vi ngân sách được phép.")
            if booking.passengers != request["passengers"]:
                raise HarnessViolation("Booking không khớp số hành khách được yêu cầu.")
            if booking.total_amount != flight.price_per_person * request["passengers"]:
                raise HarnessViolation("Tổng tiền booking không khớp giá chuẩn.")
            return

        raise HarnessViolation(f"Hành động không nằm trong danh sách được phép: {action}.")

    def verify_completion(
        self,
        request: dict[str, Any],
        booking: Booking | None,
        payment: Payment | None,
    ) -> tuple[bool, str]:
        """Xác nhận booking và thanh toán thỏa toàn bộ tiêu chí nghiệp vụ."""
        if booking is None or payment is None:
            return False, "Chưa có booking và thanh toán để xác nhận hoàn tất."
        flight = self.flights_by_id.get(booking.flight_id)
        if flight is None:
            return False, "Booking tham chiếu chuyến bay không tồn tại."
        if booking.status != "paid" or payment.status != "succeeded":
            return False, "Booking hoặc thanh toán chưa ở trạng thái thành công."
        if payment.booking_id != booking.booking_id:
            return False, "Thanh toán không thuộc booking đang kiểm tra."
        if payment.amount != booking.total_amount:
            return False, "Số tiền thanh toán không khớp tổng tiền booking."
        if booking.passengers != request.get("passengers"):
            return False, "Số hành khách trong booking không khớp yêu cầu."
        if (flight.origin, flight.destination, flight.departure_date) != (
            request.get("origin"),
            request.get("destination"),
            request.get("travel_date"),
        ):
            return False, "Booking không khớp hành trình và ngày bay đã yêu cầu."
        if flight.price_per_person > request.get("budget_per_person", 0):
            return False, "Giá vé mỗi hành khách vượt ngân sách."
        if booking.total_amount != flight.price_per_person * booking.passengers:
            return False, "Tổng tiền booking không khớp giá vé trong dữ liệu."
        return True, "Đặt chỗ và thanh toán đã được xác minh bằng mã."

    def handoff(
        self,
        reason: str,
        tool_trace: list[dict[str, Any]],
        *,
        question: str | None,
        next_step: str,
    ) -> dict[str, Any]:
        """Tạo gói bàn giao gồm lý do, thao tác, câu hỏi tùy chọn và bước tiếp theo."""
        return {
            "reason": reason,
            "actions_attempted": [event["tool"] for event in tool_trace],
            "current_state": tool_trace[-1]["result"] if tool_trace else "Chưa gọi tool nào.",
            "question_for_user": question,
            "next_step": next_step,
        }

    @staticmethod
    def clarification_question(request: dict[str, Any]) -> str:
        """Tạo câu hỏi làm rõ các trường còn thiếu hoặc hỏi hướng xử lý tiếp theo."""
        questions = {
            "origin": "Bạn muốn khởi hành từ sân bay nào?",
            "destination": "Bạn muốn bay đến sân bay nào?",
            "travel_date": "Bạn muốn bay vào ngày nào (YYYY-MM-DD)?",
            "passengers": "Bạn cần đặt vé cho bao nhiêu hành khách?",
            "budget_per_person": "Ngân sách tối đa cho mỗi hành khách là bao nhiêu?",
        }
        missing = [questions[key] for key in questions if request.get(key) in (None, "")]
        if missing:
            return " ".join(missing)
        return (
            "Bạn muốn đổi ngày/hành trình/ngân sách, chọn nguồn chuyến khác, "
            "hay dừng yêu cầu đặt vé?"
        )

    def _require_search_candidate(
        self, flight_id: str | None, search_results: list[dict[str, Any]] | None
    ) -> Flight:
        """Chỉ trả về chuyến nằm trong kết quả tìm kiếm đã được xác minh."""
        if not flight_id:
            raise HarnessViolation("Thiếu mã chuyến bay.")
        for row in search_results or []:
            if row.get("flight_id") == flight_id:
                flight = self.flights_by_id.get(flight_id)
                if flight is None or row != flight.to_dict():
                    raise HarnessViolation("Thông tin chuyến bay không có căn cứ trong dữ liệu chuẩn.")
                return flight
        raise HarnessViolation(f"Chuyến {flight_id} không nằm trong kết quả tìm kiếm đã xác minh.")
