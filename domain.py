"""Mô hình nghiệp vụ và các kịch bản đánh giá có thể chạy lặp lại."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Flight:
    """Lưu mã chuyến, hãng, hành trình, lịch bay, giá mỗi người và số ghế."""

    flight_id: str
    airline: str
    origin: str
    destination: str
    departure_date: str
    departure_time: str
    arrival_time: str
    price_per_person: int
    seats_available: int

    def to_dict(self) -> dict[str, Any]:
        """Chuyển thông tin chuyến bay thành bản ghi từ điển cho tool và báo cáo."""
        return {
            "flight_id": self.flight_id,
            "airline": self.airline,
            "origin": self.origin,
            "destination": self.destination,
            "departure_date": self.departure_date,
            "departure_time": self.departure_time,
            "arrival_time": self.arrival_time,
            "price_per_person": self.price_per_person,
            "seats_available": self.seats_available,
        }


@dataclass(frozen=True)
class Booking:
    """Lưu mã đặt chỗ, chuyến, số hành khách, tổng tiền và trạng thái đặt vé."""

    booking_id: str
    flight_id: str
    passengers: int
    total_amount: int
    status: str


@dataclass(frozen=True)
class Payment:
    """Lưu mã giao dịch giả lập, mã đặt chỗ, số tiền và trạng thái thanh toán."""

    payment_id: str
    booking_id: str
    amount: int
    status: str


@dataclass(frozen=True)
class Scenario:
    """Mô tả đầu vào, kỳ vọng và mục tiêu của một lượt đánh giá."""

    name: str
    description: str
    request: dict[str, Any]
    expected_status: str


DESIGN_LABELS = {
    "react": "ReAct",
    "plan_then_execute": "Lập kế hoạch rồi thực thi",
    "hybrid": "Lai: lập kế hoạch và thích ứng",
}

SCENARIO_LABELS = {
    "successful_booking": "Đặt vé thành công",
    "over_budget": "Không có chuyến trong ngân sách",
    "missing_passenger_count": "Thiếu số lượng hành khách",
}


SCENARIOS = (
    Scenario(
        name="successful_booking",
        description="Chuyến rẻ nhất không đủ ghế; tác tử cần chọn chuyến phù hợp kế tiếp.",
        request={
            "origin": "SGN",
            "destination": "HAN",
            "travel_date": "2026-11-15",
            "passengers": 2,
            "budget_per_person": 6_000_000,
            "auto_purchase": True,
        },
        expected_status="completed",
    ),
    Scenario(
        name="over_budget",
        description="Không chuyến nào nằm trong ngân sách mỗi người; tác tử phải bàn giao.",
        request={
            "origin": "SGN",
            "destination": "HAN",
            "travel_date": "2026-11-15",
            "passengers": 2,
            "budget_per_person": 3_500_000,
            "auto_purchase": True,
        },
        expected_status="handoff",
    ),
    Scenario(
        name="missing_passenger_count",
        description="Thiếu số lượng hành khách; tác tử phải hỏi lại trước khi gọi công cụ.",
        request={
            "origin": "SGN",
            "destination": "HAN",
            "travel_date": "2026-11-15",
            "passengers": None,
            "budget_per_person": 6_000_000,
            "auto_purchase": True,
        },
        expected_status="handoff",
    ),
)
