"""Focused tests for the four harness layers and all three LangGraph designs."""

from __future__ import annotations

import unittest

from agents import AGENT_DESIGNS, run_agent
from domain import Booking, Payment, SCENARIOS
from flight_data import FLIGHTS_BY_ID
from harness import FlightHarness, HarnessViolation
from presentation import format_result_vi


class HarnessTests(unittest.TestCase):
    """Kiểm tra riêng các chốt dữ liệu, quyền mua và điều kiện hoàn tất."""

    def setUp(self) -> None:
        """Tạo harness và yêu cầu hợp lệ dùng chung cho từng phép thử."""
        self.harness = FlightHarness(FLIGHTS_BY_ID)
        self.request = dict(SCENARIOS[0].request)

    def test_missing_request_data_is_rejected_before_tools(self) -> None:
        """Đảm bảo yêu cầu thiếu số hành khách không qua được kiểm tra đầu vào."""
        request = dict(self.request, passengers=None)
        self.assertTrue(FlightHarness.validate_request(request))

    def test_search_result_must_match_source_and_budget(self) -> None:
        """Đảm bảo harness phát hiện giá trong kết quả bị sửa sai so với dữ liệu."""
        forged = [dict(FLIGHTS_BY_ID["VJ201"].to_dict(), price_per_person=1)]
        with self.assertRaises(HarnessViolation):
            self.harness.validate_search_results(forged, self.request)

    def test_purchase_is_rejected_without_explicit_authority(self) -> None:
        """Đảm bảo không thể đặt chỗ nếu yêu cầu không cấp quyền mua tự động."""
        request = dict(self.request, auto_purchase=False)
        with self.assertRaises(HarnessViolation):
            self.harness.authorize(
                "create_booking",
                request,
                flight_id="VJ201",
                search_results=[FLIGHTS_BY_ID["VJ201"].to_dict()],
                checked_seats={"VJ201": {"available": True, "required": 2}},
            )

    def test_purchase_is_rejected_above_per_passenger_budget(self) -> None:
        """Đảm bảo harness chặn chuyến vượt ngân sách tối đa mỗi hành khách."""
        request = dict(self.request, budget_per_person=3_500_000)
        with self.assertRaises(HarnessViolation):
            self.harness.authorize(
                "create_booking",
                request,
                flight_id="VJ201",
                search_results=[FLIGHTS_BY_ID["VJ201"].to_dict()],
                checked_seats={"VJ201": {"available": True, "required": 2}},
            )

    def test_completion_gate_rejects_unpaid_booking(self) -> None:
        """Đảm bảo booking mới giữ chỗ không bị báo nhầm là giao dịch hoàn tất."""
        booking = Booking("BKG-1", "VJ201", 2, 10_000_000, "reserved")
        payment = Payment("PAY-1", "BKG-1", 10_000_000, "succeeded")
        completed, _ = self.harness.verify_completion(self.request, booking, payment)
        self.assertFalse(completed)

    def test_completion_gate_rejects_booking_for_wrong_itinerary(self) -> None:
        """Đảm bảo bộ kiểm tra từ chối booking có hành trình ngược yêu cầu."""
        booking = Booking("BKG-1", "VN202", 2, 8_200_000, "paid")
        payment = Payment("PAY-1", "BKG-1", 8_200_000, "succeeded")
        completed, _ = self.harness.verify_completion(self.request, booking, payment)
        self.assertFalse(completed)


class AgentDesignTests(unittest.TestCase):
    """Kiểm tra đầu ra tiếng Việt và luồng đầu-cuối của ba mẫu tác tử."""

    def test_displayed_answer_and_status_are_vietnamese(self) -> None:
        """Kiểm tra câu trả lời đặt vé thành công hiển thị bằng tiếng Việt."""
        raw = run_agent("react", SCENARIOS[0].request)
        displayed = format_result_vi(raw)
        self.assertEqual(displayed["trạng_thái"], "đã hoàn tất")
        self.assertIn("Đã đặt và thanh toán thành công", displayed["câu_trả_lời"])
        self.assertIn("5.000.000 VND/người", displayed["câu_trả_lời"])
        self.assertIn("đặt_chỗ", displayed)

    def test_displayed_handoff_status_is_vietnamese(self) -> None:
        """Kiểm tra trạng thái và lý do bàn giao được chuyển thành tiếng Việt."""
        raw = run_agent("react", SCENARIOS[1].request)
        displayed = format_result_vi(raw)
        self.assertEqual(displayed["trạng_thái"], "cần người dùng xử lý")
        self.assertIn("lý_do", displayed["bàn_giao"])

    def test_no_flight_handoff_does_not_ask_for_more_details(self) -> None:
        """Đảm bảo hết chuyến phù hợp thì báo khách tự đặt, không hỏi lại."""
        for design in AGENT_DESIGNS:
            with self.subTest(design=design):
                result = run_agent(design, SCENARIOS[1].request)
                handoff = result["handoff"]
                self.assertIsNone(handoff["question_for_user"])
                self.assertIn("tự đặt vé", handoff["next_step"])

    def test_all_designs_complete_the_same_valid_purchase(self) -> None:
        """Đảm bảo mỗi mẫu chọn cùng chuyến hợp lệ và hoàn tất thanh toán giả lập."""
        for design in AGENT_DESIGNS:
            with self.subTest(design=design):
                result = run_agent(design, SCENARIOS[0].request)
                self.assertEqual(result["status"], "completed")
                self.assertEqual(result["selected_flight"]["flight_id"], "VJ201")
                self.assertEqual(len(result["flight_options"]), 3)
                self.assertTrue(
                    result["flight_options"][0]["seat_check"]["available"] is False
                )
                self.assertEqual(result["booking"]["status"], "paid")
                self.assertEqual(result["payment"]["status"], "succeeded")

    def test_all_designs_handoff_when_over_budget(self) -> None:
        """Đảm bảo mọi mẫu bàn giao và không tạo giao dịch vượt ngân sách."""
        for design in AGENT_DESIGNS:
            with self.subTest(design=design):
                result = run_agent(design, SCENARIOS[1].request)
                self.assertEqual(result["status"], "handoff")
                self.assertIsNotNone(result["handoff"])
                self.assertIsNone(result["booking"])
                self.assertIsNone(result["payment"])
                self.assertEqual(result["tool_trace"][0]["result"]["status"], "ok")
                self.assertEqual(result["tool_trace"][0]["result"]["flights"], [])

    def test_all_designs_handoff_on_ambiguous_request_without_tool_calls(self) -> None:
        """Đảm bảo thiếu dữ kiện làm tác tử hỏi lại trước khi gọi công cụ."""
        for design in AGENT_DESIGNS:
            with self.subTest(design=design):
                result = run_agent(design, SCENARIOS[2].request)
                self.assertEqual(result["status"], "handoff")
                self.assertEqual(result["tool_trace"], [])
                self.assertIn("bao nhiêu hành khách", result["handoff"]["question_for_user"])

    def test_hybrid_replans_after_a_candidate_has_too_few_seats(self) -> None:
        """Đảm bảo mẫu Lai điều chỉnh kế hoạch sau khi chuyến đầu không đủ ghế."""
        result = run_agent("hybrid", SCENARIOS[0].request)
        self.assertEqual(result["metrics"]["replans"], 1)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(
            any("check_seats:VN101" in plan for plan in result["plan_history"])
        )


if __name__ == "__main__":
    unittest.main()
