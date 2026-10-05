"""Các công cụ LangChain dùng kho chuyến bay và thanh toán giả lập trong bộ nhớ."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool

from domain import Booking, Flight, Payment
from flight_data import FLIGHTS
from harness import FlightHarness, FlightToolError, HarnessViolation


class FlightService:
    """Cung cấp các công cụ LangChain trên kho chuyến và giao dịch giả lập."""

    def __init__(self, request: dict[str, Any]) -> None:
        """Khởi tạo kho ghế, booking, thanh toán và công cụ cho một yêu cầu."""
        self.request = dict(request)
        self.flights: dict[str, Flight] = {flight.flight_id: flight for flight in FLIGHTS}
        self.remaining_seats = {
            flight.flight_id: flight.seats_available for flight in FLIGHTS
        }
        self.harness = FlightHarness(self.flights)
        self.search_results: list[dict[str, Any]] = []
        self.checked_seats: dict[str, dict[str, Any]] = {}
        self.bookings: dict[str, Booking] = {}
        self.payments: dict[str, Payment] = {}
        self._booking_sequence = 1000
        self._payment_sequence = 2000
        self.tools = self._build_tools()

    def search_flights(
        self,
        origin: str,
        destination: str,
        travel_date: str,
        budget_per_person: int,
    ) -> dict[str, Any]:
        """Lọc và sắp xếp chuyến khớp hành trình, ngày bay và ngân sách mỗi người."""
        self.harness.authorize("search_flights", self.request)
        if (
            origin != self.request["origin"]
            or destination != self.request["destination"]
            or travel_date != self.request["travel_date"]
            or budget_per_person != self.request["budget_per_person"]
        ):
            raise HarnessViolation("Tham số tìm kiếm khác với yêu cầu đã được xác thực.")

        rows = [
            flight.to_dict()
            for flight in self.flights.values()
            if flight.origin == origin
            and flight.destination == destination
            and flight.departure_date == travel_date
            and flight.price_per_person <= budget_per_person
        ]
        rows.sort(key=lambda row: (row["price_per_person"], row["departure_time"]))
        self.harness.validate_search_results(rows, self.request)
        self.search_results = rows
        return {"status": "ok", "count": len(rows), "flights": rows}

    def check_seats(self, flight_id: str, passengers: int) -> dict[str, Any]:
        """Trả số ghế còn lại và xác định chuyến có đủ chỗ cho cả nhóm hay không."""
        self.harness.authorize(
            "check_seats",
            self.request,
            flight_id=flight_id,
            search_results=self.search_results,
        )
        if passengers != self.request["passengers"]:
            raise HarnessViolation("Số hành khách yêu cầu kiểm tra không khớp.")
        available = self.remaining_seats.get(flight_id, 0)
        result = {
            "flight_id": flight_id,
            "required": passengers,
            "seats_remaining": available,
            "available": available >= passengers,
        }
        self.checked_seats[flight_id] = result
        return result

    def create_booking(self, flight_id: str, passengers: int) -> dict[str, Any]:
        """Giữ chỗ trong bộ nhớ sau khi harness cho phép và ghế đã được kiểm tra."""
        self.harness.authorize(
            "create_booking",
            self.request,
            flight_id=flight_id,
            search_results=self.search_results,
            checked_seats=self.checked_seats,
        )
        if passengers != self.request["passengers"]:
            raise HarnessViolation("Số hành khách đặt chỗ không khớp yêu cầu.")
        flight = self.flights[flight_id]
        if self.remaining_seats[flight_id] < passengers:
            raise FlightToolError(f"Chuyến {flight_id} không còn đủ ghế.")

        self._booking_sequence += 1
        booking = Booking(
            booking_id=f"BKG-{self._booking_sequence}",
            flight_id=flight_id,
            passengers=passengers,
            total_amount=flight.price_per_person * passengers,
            status="reserved",
        )
        self.remaining_seats[flight_id] -= passengers
        self.bookings[booking.booking_id] = booking
        return {
            "booking_id": booking.booking_id,
            "flight_id": booking.flight_id,
            "passengers": booking.passengers,
            "total_amount": booking.total_amount,
            "status": booking.status,
        }

    def pay_booking(self, booking_id: str) -> dict[str, Any]:
        """Tạo thanh toán giả lập và cập nhật booking sang trạng thái đã thanh toán."""
        booking = self.bookings.get(booking_id)
        self.harness.authorize("pay_booking", self.request, booking=booking)
        if booking is None:
            raise HarnessViolation("Không tìm thấy booking để thanh toán.")
        self._payment_sequence += 1
        payment = Payment(
            payment_id=f"PAY-{self._payment_sequence}",
            booking_id=booking.booking_id,
            amount=booking.total_amount,
            status="succeeded",
        )
        paid_booking = Booking(
            booking_id=booking.booking_id,
            flight_id=booking.flight_id,
            passengers=booking.passengers,
            total_amount=booking.total_amount,
            status="paid",
        )
        self.bookings[booking.booking_id] = paid_booking
        self.payments[payment.payment_id] = payment
        return {
            "payment_id": payment.payment_id,
            "booking_id": payment.booking_id,
            "amount": payment.amount,
            "status": payment.status,
        }

    def _build_tools(self) -> dict[str, StructuredTool]:
        """Đóng gói các thao tác dịch vụ thành công cụ có schema cho LangChain."""
        return {
            "search_flights": StructuredTool.from_function(
                func=self.search_flights,
                name="search_flights",
                description="Tìm chuyến đúng hành trình, ngày bay và ngân sách mỗi người.",
            ),
            "check_seats": StructuredTool.from_function(
                func=self.check_seats,
                name="check_seats",
                description="Kiểm tra số ghế còn lại cho mã chuyến và số hành khách.",
            ),
            "create_booking": StructuredTool.from_function(
                func=self.create_booking,
                name="create_booking",
                description="Tạo giữ chỗ sau khi kiểm tra đủ ghế và quyền mua.",
            ),
            "pay_booking": StructuredTool.from_function(
                func=self.pay_booking,
                name="pay_booking",
                description="Mô phỏng thanh toán cho booking hợp lệ.",
            ),
        }

    def invoke_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Tìm và gọi công cụ theo tên; báo lỗi nếu tên công cụ không được đăng ký."""
        tool = self.tools.get(name)
        if tool is None:
            raise HarnessViolation(f"Tool không được khai báo: {name}.")
        return tool.invoke(arguments)
