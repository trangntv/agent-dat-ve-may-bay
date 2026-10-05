# Báo cáo BTVN#3 — Agent đặt vé máy bay

## Môi trường và giả định

- Toàn bộ chuyến bay, chỗ ngồi, đặt chỗ và thanh toán được giả lập trong bộ nhớ.
- `MockFlightLLM` là mô hình hội thoại LangChain xác định theo kịch bản; không gọi API bên ngoài và không phải mô hình ngôn ngữ tổng quát.
- Ba thiết kế dùng chung dữ liệu, công cụ, lớp bảo vệ và yêu cầu đầu vào; cùng áp dụng chính sách chọn chuyến rẻ nhất còn đủ ghế.
- Ngân sách là mức tối đa **mỗi hành khách**; tổng tiền đặt vé bằng giá mỗi người nhân số hành khách.
- Thanh toán chỉ được mô phỏng; chương trình không dùng hoặc lưu thông tin thẻ.

## Phạm vi đề tài

- Đầu vào của khách hàng gồm sân bay đi/đến theo mã IATA, ngày bay, số hành khách, ngân sách tối đa mỗi người và quyền cho phép tự đặt/thanh toán.
- Agent tìm các chuyến bay phù hợp, kiểm tra sức chứa, chọn chuyến giá thấp nhất còn đủ chỗ, tạo booking và thanh toán giả lập; kết quả nêu hãng bay, giá mỗi người, lịch bay và tổng tiền.
- Nếu thiếu hoặc sai dữ liệu, agent dừng trước khi gọi công cụ và hỏi khách bổ sung thông tin tương ứng.
- Nếu không có chuyến trong ngân sách hoặc các chuyến đều không đủ ghế, agent không tạo booking/thanh toán, không hỏi lại khi dữ liệu đã đầy đủ, và bàn giao để khách tự đặt qua hãng hàng không hoặc đại lý.
- Phạm vi chỉ là mô phỏng trong bộ nhớ: không truy cập hệ thống hãng bay, không giữ chỗ hay thanh toán thật; `MockFlightLLM` chạy theo quy tắc xác định và không hiểu hội thoại tự do.

## Thiết kế hệ thống

1. **Miền nghiệp vụ và dữ liệu:** `domain.py` định nghĩa chuyến bay, booking, payment và kịch bản; `flight_data.py` cung cấp inventory cố định để các lượt đánh giá có thể lặp lại.
2. **Mô hình và công cụ:** `mock_llm.py` cung cấp quyết định/kế hoạch xác định qua giao diện LangChain; `tools.py` đóng gói tìm chuyến, kiểm tra ghế, tạo booking và thanh toán thành công cụ LangChain.
3. **Lớp bảo vệ:** `harness.py` kiểm tra đầu vào, dữ liệu chuyến chuẩn, quyền thao tác, điều kiện hoàn tất và nội dung bàn giao. Các thao tác tạo booking/thanh toán chỉ tiếp tục khi được phép và chuyến đã được xác minh.
4. **Điều phối tác tử:** `agents.py` xây dựng ba graph LangGraph. ReAct quyết định sau từng quan sát; Plan-then-Execute tạo kế hoạch có bước được cho phép rồi thực thi; Lai khởi đầu bằng kế hoạch và cập nhật hành động/kế hoạch theo quan sát.
5. **Trình bày và đánh giá:** `presentation.py` chuyển state/trace thành thông tin tiếng Việt dễ đọc; `evaluate.py` chạy ma trận kịch bản × thiết kế, tổng hợp chỉ số và tạo `REPORT.md` cùng `result_comparing.md`; `main.py` hỗ trợ chạy một yêu cầu tương tác.

## Các lớp bảo vệ (harness) được triển khai

1. **Ràng buộc dữ liệu:** xác minh từng kết quả chuyến với dữ liệu chuẩn, hành trình/ngày/ngân sách; thông tin đặt chỗ và thanh toán do công cụ tạo.
2. **Tiêu chí hoàn thành bằng mã:** chỉ xác nhận thành công khi đặt chỗ đã thanh toán, giao dịch thành công và khớp mã đặt chỗ, số tiền, chuyến cùng số hành khách.
3. **Kiểm tra quyền:** chỉ tìm kiếm với yêu cầu hợp lệ; đặt vé/thanh toán cần quyền tự động, chuyến đã xác minh, đủ ghế và trong ngân sách.
4. **Bàn giao:** khi thiếu dữ liệu, nêu trường còn thiếu và hỏi khách bổ sung; khi không có chuyến phù hợp nhưng dữ liệu đã đủ, thông báo khách tự đặt qua hãng/đại lý mà không hỏi lại. Cả hai trường hợp đều giữ lý do và thao tác đã thử.

## Phân tích các tệp và output của agents

### `agents.py` — Điều phối ba thiết kế tác tử

`run_agent(design, request)` tạo `FlightService`, lấy harness từ service, tạo `MockFlightLLM`, dựng graph được chọn và chạy graph trên một `AgentState`. State chứa yêu cầu, lỗi xác thực, kết quả tìm chuyến/kiểm tra ghế, chuyến chọn, booking/payment, kế hoạch, quyết định, tool trace và trạng thái bàn giao.

- **ReAct:** xác thực đầu vào, gọi MockLLM để chọn một hành động, chạy node tương ứng rồi quay lại quyết định dựa trên quan sát mới.
- **Plan-then-Execute:** xác thực, sinh kế hoạch, chỉ chấp nhận các bước trong danh sách cho phép, sau đó thực thi từng bước cho tới khi hoàn tất hoặc bàn giao.
- **Lai:** sinh kế hoạch ban đầu, rồi cập nhật quyết định và kế hoạch theo trạng thái/quan sát mới.

`_format_result(...)` tổng hợp kết quả thành dictionary gồm `status`, `request`, `validation_errors`, `searched`, `flight_options`, `selected_flight`, `booking`, `payment`, `handoff_reason`, `handoff`, `tool_trace`, `plan`, `plan_history`, `decision_trace` và `metrics`. `completed` nghĩa là đã qua xác minh cuối; `handoff` nghĩa là dừng và cần người dùng xử lý, không phải đặt vé thành công.

### `mock_llm.py` — Mô hình quyết định/kế hoạch giả lập

`MockFlightLLM` kế thừa `BaseChatModel` của LangChain, do đó agent gọi được qua giao diện mô hình chuẩn mà không cần API key. `complete(...)` gửi operation cùng payload JSON; `_generate(...)` tạo phản hồi theo operation và tăng `call_count`.

- Operation `plan` trả các bước cho Plan-then-Execute; `hybrid_plan` tạo kế hoạch ban đầu cho mẫu Lai.
- `_choose_action(...)` chọn bước kế tiếp dựa trên state: tìm chuyến, kiểm tra ghế, tạo booking, thanh toán, xác minh hoặc bàn giao.
- `_revise_plan(...)` cung cấp kế hoạch điều chỉnh cho mẫu Lai.

Đây là chính sách xác định theo các kịch bản, không phải LLM tổng quát và không tự hiểu hội thoại tự do. `call_count` chỉ đo số lần mô hình giả được gọi trong lượt chạy.

### `flight_data.py` — Kho chuyến bay dùng chung

`FLIGHTS` là tuple gồm năm đối tượng `Flight` bất biến; `FLIGHTS_BY_ID` là dictionary tra cứu nhanh theo mã chuyến. Dữ liệu gồm VN101, VJ201, QH301 (SGN–HAN), VN202 (HAN–SGN) và VJ401 (SGN–DAD), mỗi chuyến có hãng, ngày/giờ, giá và số ghế.

Inventory cố định giúp so sánh công bằng, lặp lại được giữa ba agent. Trong ca thành công, VN101 rẻ nhất nhưng chỉ còn một ghế cho hai khách; VJ201 là chuyến kế tiếp đủ ghế. Dữ liệu chỉ nhằm mô phỏng, không lấy từ hãng bay trực tiếp.

### `harness.py` — Các chốt kiểm soát nghiệp vụ

`FlightHarness` độc lập với quyết định của agent và thực hiện bốn nhóm kiểm tra:

1. `validate_request(...)`: kiểm tra trường bắt buộc, mã IATA, ngày ISO, số khách từ 1–6, ngân sách dương và quyền `auto_purchase`.
2. `validate_search_results(...)`: đối chiếu chuyến với nguồn dữ liệu chuẩn, chặn chuyến trùng/sai hành trình-ngày/giá hoặc mã chuyến không hợp lệ.
3. `authorize(...)`: chỉ cho tạo booking khi chuyến nằm trong kết quả tìm đã xác minh, đủ ghế, đúng số khách/ngân sách; chỉ cho thanh toán booking giữ chỗ hợp lệ và đúng tổng tiền.
4. `verify_completion(...)`: xác nhận trạng thái booking/payment, liên kết booking, số tiền, số khách, chuyến, hành trình, ngày bay và ngân sách.

`handoff(...)` đóng gói lý do, các tool đã thử, trạng thái hiện tại, câu hỏi tùy chọn và bước tiếp theo. Nếu thiếu dữ liệu thì hỏi khách bổ sung; nếu dữ liệu đủ nhưng không có chuyến phù hợp thì không hỏi lại, hướng khách tự đặt qua hãng/đại lý.

### `domain.py` — Mô hình dữ liệu và kịch bản

Các dataclass bất biến `Flight`, `Booking`, `Payment`, `Scenario` định nghĩa schema thống nhất cho chuyến, booking, payment và lượt đánh giá. `Flight.to_dict()` chuyển chuyến thành dictionary cho tool/harness. `DESIGN_LABELS` và `SCENARIO_LABELS` ánh xạ mã nội bộ sang tên hiển thị.

`SCENARIOS` định nghĩa ba ca với kỳ vọng: đặt vé thành công (`completed`), vượt ngân sách (`handoff`) và thiếu số hành khách (`handoff`). Đây là đầu vào cố định cho đánh giá, không phải hội thoại tự do.

### `tools.py` — Công cụ nghiệp vụ LangChain

`FlightService` khởi tạo inventory/ghế còn lại, kết quả tìm kiếm, kiểm tra ghế, booking và payment trong bộ nhớ; `_build_tools()` đóng gói bốn phương thức thành `StructuredTool`, còn `invoke_tool(...)` gọi tool theo tên.

- `search_flights(...)`: lọc theo sân bay, ngày và ngân sách/người; sắp xếp theo giá rồi giờ bay; xác minh kết quả qua harness.
- `check_seats(...)`: so số ghế còn với số khách và lưu kết quả kiểm tra.
- `create_booking(...)`: gọi authorize, xác nhận đủ ghế rồi tạo booking và tính tổng tiền trong bộ nhớ.
- `pay_booking(...)`: gọi authorize, tạo payment giả lập và đổi booking từ `reserved` sang `paid`.

Các tool trả dictionary để graph cập nhật state và ghi `tool_trace`. Không tool nào kết nối hãng bay, cổng thanh toán hay xử lý tiền thật.

### Luồng phối hợp và ý nghĩa output

`domain.py`/`flight_data.py` cung cấp kiểu dữ liệu và inventory → `agents.py` kiểm tra yêu cầu bằng harness → `mock_llm.py` chọn hành động/kế hoạch → agent gọi `tools.py` → harness kiểm tra quyền/dữ liệu/kết quả → agent trả dictionary kết quả → lớp trình bày hiển thị cho người dùng hoặc `evaluate.py` dùng để so sánh và sinh báo cáo.

| Trường output | Ý nghĩa |
|---|---|
| `status` | `completed` chỉ khi booking và payment đạt xác minh; `handoff` nghĩa là agent dừng, cần khách bổ sung dữ liệu hoặc tự đặt vé. |
| `flight_options`, `selected_flight` | Danh sách chuyến phù hợp và chuyến được chọn; các lựa chọn có thể kèm số ghế/kiểm tra ghế. |
| `booking`, `payment` | Chi tiết đặt chỗ và giao dịch giả lập; không có nếu agent dừng trước thao tác đặt hoặc thanh toán. |
| `tool_trace` | Nhật ký có thứ tự gồm tên tool, tham số và kết quả/lỗi của từng lần gọi. |
| `plan`, `plan_history`, `decision_trace` | Kế hoạch hiện tại, lịch sử lập/điều chỉnh kế hoạch và các hành động đã chọn; ReAct ra quyết định từng bước thay vì có kế hoạch cố định. |
| `handoff_reason`, `handoff` | Lý do và gói bàn giao; thiếu dữ liệu thì có câu hỏi, hết chuyến phù hợp khi đủ dữ kiện thì chỉ hướng khách tự đặt, không hỏi lại. |
| `metrics` | `llm_calls`, `tool_calls`, `replans`; chỉ dùng so sánh ba thiết kế trên mô phỏng này, không phải số đo production. |


### Phân tích kết quả đầu ra

- Với yêu cầu hợp lệ và có chuyến: cả ba thiết kế hoàn tất giả lập. Chuyến rẻ nhất `VN101` chỉ còn một ghế cho hai khách nên bị loại; cả ba chọn `VJ201` của VietJet Air, 5.000.000 VND/người, tổng 10.000.000 VND.
- Plan-then-Execute kiểm tra đủ ba ứng viên trước khi chọn chuyến rẻ nhất còn ghế; ReAct và Lai kiểm tra tuần tự và dừng ở chuyến đầu tiên đủ điều kiện theo thứ tự giá.
- Khi không có chuyến trong ngân sách: cả ba trả trạng thái bàn giao, không có booking/payment và không hỏi lại; nội dung chỉ dẫn khách tự đặt qua hãng bay/đại lý.
- Khi thiếu số hành khách: cả ba dừng trước khi gọi tool, trả trạng thái bàn giao và hỏi đúng số lượng hành khách cần bổ sung.
- Các trường `tool_trace`, `plan_history`, `decision_trace` và `metrics` giúp kiểm tra đường đi của từng agent; `metrics` gồm số lượt MockLLM, số lượt tool và số lần điều chỉnh kế hoạch. Những con số này chỉ phản ánh mô hình giả và inventory nhỏ của bài.

## Kịch bản và kết quả

| Tình huống | Mẫu tác tử | Trạng thái mong đợi | Trạng thái thực tế | Chuyến chọn | Tổng vé (VND) | Lượt mô hình giả | Lượt gọi công cụ | Lần điều chỉnh kế hoạch |
|---|---|---:|---:|---|---:|---:|---:|---:|
| Đặt vé thành công | ReAct | đã hoàn tất | đã hoàn tất | VJ201 | 10000000 | 6 | 5 | 0 |
| Đặt vé thành công | Plan-then-Execute | đã hoàn tất | đã hoàn tất | VJ201 | 10000000 | 1 | 6 | 0 |
| Đặt vé thành công | Hybrid | đã hoàn tất | đã hoàn tất | VJ201 | 10000000 | 7 | 5 | 1 |
| Không có chuyến trong ngân sách | ReAct | cần người dùng xử lý | cần người dùng xử lý | — | — | 2 | 1 | 0 |
| Không có chuyến trong ngân sách | Plan-then-Execute | cần người dùng xử lý | cần người dùng xử lý | — | — | 1 | 1 | 0 |
| Không có chuyến trong ngân sách | Hybrid | cần người dùng xử lý | cần người dùng xử lý | — | — | 3 | 1 | 0 |
| Thiếu số lượng hành khách | ReAct | cần người dùng xử lý | cần người dùng xử lý | — | — | 0 | 0 | 0 |
| Thiếu số lượng hành khách | Plan-then-Execute | cần người dùng xử lý | cần người dùng xử lý | — | — | 0 | 0 | 0 |
| Thiếu số lượng hành khách | Hybrid | cần người dùng xử lý | cần người dùng xử lý | — | — | 0 | 0 | 0 |

## Quan sát

- Ở tình huống thành công, chuyến rẻ nhất chỉ còn 1 ghế cho 2 người. Tác tử bỏ qua chuyến đó, kiểm tra chuyến kế tiếp, rồi đặt chỗ và thanh toán giả lập.
- Mẫu lập kế hoạch rồi thực thi kiểm tra mọi lựa chọn trước khi chọn chuyến rẻ nhất còn đủ ghế; ReAct và mẫu Lai dừng khi thấy chuyến đầu tiên phù hợp theo thứ tự giá.
- ReAct gọi mô hình giả sau mỗi kết quả công cụ; mẫu lập kế hoạch rồi thực thi lập kế hoạch một lần; mẫu Lai cập nhật kế hoạch theo kết quả từng bước.
- Cả ba chọn `VJ201` (VietJet Air), giá 5.000.000 VND/người; tổng tiền đặt chỗ giả lập là 10.000.000 VND cho 2 hành khách.
- Ngân sách thấp khiến tác tử bàn giao, không tạo đặt chỗ hoặc giao dịch. Thiếu số hành khách khiến tác tử yêu cầu bổ sung trước khi gọi công cụ.
- Số lượt gọi trong báo cáo được đo trên mô hình giả và kho dữ liệu nhỏ này; không đại diện cho hiệu năng của mô hình ngôn ngữ thật hoặc dữ liệu hãng bay thật.
- Số lượt có trạng thái đúng như kỳ vọng trong lần chạy này: 9/9.

## Cách chạy

```powershell
python -m pip install -r requirements.txt
python -m unittest -v
python evaluate.py
```

Chạy `evaluate.py` để xem tiến trình có cấu trúc; dùng `evaluate.py --json` để xuất JSON hoặc `evaluate.py --compact` để chỉ xem bảng tổng quan.
