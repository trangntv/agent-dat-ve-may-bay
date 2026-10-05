"""Điểm vào tương tác để thử một trong ba thiết kế tác tử đặt vé."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from agents import AGENT_DESIGNS, run_agent
from domain import DESIGN_LABELS
from presentation import format_run_terminal


def _read_passengers() -> int | None:
    """Đọc số lượng hành khách từ bàn phím; để trống nếu người dùng chưa biết."""
    value = input("Số lượng hành khách: ").strip()
    if not value:
        return None
    return int(value)


def _read_budget() -> int | None:
    """Đọc ngân sách tối đa mỗi hành khách và chuẩn hóa số nguyên VND."""
    value = input("Ngân sách tối đa mỗi hành khách (VND, nhập số nguyên): ").strip()
    if not value:
        return None
    return int(value.replace(",", "").replace(" ", ""))


def main() -> int:
    """Nhận yêu cầu đặt vé, chạy mẫu tác tử được chọn và in kết quả tiếng Việt."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Chạy thử tác tử đặt vé máy bay với dữ liệu và thanh toán giả lập."
    )
    parser.add_argument(
        "--design",
        choices=AGENT_DESIGNS,
        default="react",
        help="Mẫu tác tử cần chạy: " + ", ".join(
            f"{key} ({value})" for key, value in DESIGN_LABELS.items()
        ),
    )
    args = parser.parse_args()

    print("Đặt vé máy bay mô phỏng — không có thanh toán thật.")
    try:
        request: dict[str, Any] = {
            "origin": input("Sân bay khởi hành (mã IATA, ví dụ SGN): ").strip().upper(),
            "destination": input("Sân bay đến (mã IATA, ví dụ HAN): ").strip().upper(),
            "travel_date": input("Ngày khởi hành (YYYY-MM-DD): ").strip(),
            "passengers": _read_passengers(),
            "budget_per_person": _read_budget(),
            "auto_purchase": True,
        }
    except (EOFError, ValueError):
        print(
            "Thông tin nhập chưa hợp lệ. Số hành khách và ngân sách phải là số nguyên.",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_agent(args.design, request)
    except ValueError as error:
        print(f"Không thể xử lý yêu cầu: {error}", file=sys.stderr)
        return 2

    print(format_run_terminal(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
