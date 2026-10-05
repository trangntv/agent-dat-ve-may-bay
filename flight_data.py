"""Kho chuyến bay giả lập nhỏ, có dữ liệu xác định để kiểm thử."""

from domain import Flight


# Tập chuyến cố định giúp các lần chạy và so sánh tác tử có cùng dữ liệu đầu vào.
FLIGHTS = (
    Flight(
        flight_id="VN101",
        airline="Vietnam Airlines",
        origin="SGN",
        destination="HAN",
        departure_date="2026-11-15",
        departure_time="07:30",
        arrival_time="09:40",
        price_per_person=4_200_000,
        seats_available=1,
    ),
    Flight(
        flight_id="VJ201",
        airline="VietJet Air",
        origin="SGN",
        destination="HAN",
        departure_date="2026-11-15",
        departure_time="10:15",
        arrival_time="12:25",
        price_per_person=5_000_000,
        seats_available=5,
    ),
    Flight(
        flight_id="QH301",
        airline="Bamboo Airways",
        origin="SGN",
        destination="HAN",
        departure_date="2026-11-15",
        departure_time="14:00",
        arrival_time="16:10",
        price_per_person=5_800_000,
        seats_available=8,
    ),
    Flight(
        flight_id="VN202",
        airline="Vietnam Airlines",
        origin="HAN",
        destination="SGN",
        departure_date="2026-11-15",
        departure_time="18:00",
        arrival_time="20:10",
        price_per_person=4_100_000,
        seats_available=7,
    ),
    Flight(
        flight_id="VJ401",
        airline="VietJet Air",
        origin="SGN",
        destination="DAD",
        departure_date="2026-11-15",
        departure_time="08:20",
        arrival_time="09:45",
        price_per_person=1_900_000,
        seats_available=9,
    ),
)

# Tra cứu nhanh chuyến theo mã để harness kiểm tra booking và kết quả tìm kiếm.
FLIGHTS_BY_ID = {flight.flight_id: flight for flight in FLIGHTS}
