# BTVN#3 — Tác tử đặt vé máy bay

Bài làm minh họa ba mẫu thiết kế tác tử trên cùng một bài toán đặt vé. Chuyến bay, số ghế, đặt chỗ và thanh toán đều được giả lập trong bộ nhớ; chương trình không gọi dịch vụ bên ngoài và không xử lý giao dịch thật.

## Cài đặt và chạy trên Windows PowerShell

Mở PowerShell tại thư mục này, sau đó chạy:

```powershell
python -m pip install -r requirements.txt
python -m unittest -v
python evaluate.py
```

Lệnh cuối chạy cùng các tình huống kiểm thử trên cả ba mẫu, in bảng tổng quan và tiến trình chi tiết của cả 9 lượt (kế hoạch/quyết định, hành động, kết quả harness, bàn giao), cập nhật `REPORT.md` và tạo `result_comparing.md`.

Để xem toàn bộ kết quả và nhật ký từng lượt dưới dạng JSON tiếng Việt:

```powershell
python evaluate.py --json
```

Để chỉ in bảng tổng quan:

```powershell
python evaluate.py --compact
```

Để nhập yêu cầu và chạy tương tác một mẫu tác tử:

```powershell
python main.py --design react
```

Giá trị `--design` là `react`, `plan_then_execute` hoặc `hybrid`. Chương trình lần lượt hỏi sân bay khởi hành, sân bay đến, ngày bay, số hành khách và ngân sách tối đa mỗi người. Khi thiếu dữ liệu, chương trình bàn giao và hỏi bổ sung. Nếu không có chuyến phù hợp, chương trình thông báo khách tự đặt qua hãng bay/đại lý và không hỏi lại. Thanh toán chỉ được mô phỏng.

## Cấu trúc chương trình

- `domain.py`: mô hình dữ liệu, nhãn tiếng Việt và tình huống đánh giá.
- `flight_data.py`: kho chuyến bay giả lập có kết quả ổn định.
- `tools.py`: công cụ LangChain để tìm chuyến, kiểm tra ghế, đặt chỗ và thanh toán mô phỏng.
- `harness.py`: kiểm chứng dữ liệu, tiêu chí hoàn tất bằng mã, quyền đặt/mua và gói bàn giao.
- `mock_llm.py`: mô hình hội thoại giả lập xác định, không cần khóa API.
- `agents.py`: ba luồng LangGraph dùng chung công cụ và harness.
- `presentation.py`: chuyển yêu cầu, kết quả, nhật ký và trạng thái nội bộ thành tiếng Việt.
- `main.py`: giao diện dòng lệnh để nhập một yêu cầu đặt vé.
- `evaluate.py`: chạy các kịch bản, so sánh chỉ số và tạo báo cáo.
- `test_assignment.py`: kiểm thử harness và luồng đặt vé đầu-cuối.
- `REPORT.md`: báo cáo phương pháp và kết quả lần chạy gần nhất.
- Báo cáo cũng mô tả phạm vi đề tài, kiến trúc hệ thống, các tệp thành phần và cấu trúc output của ba thiết kế agent.

## Bốn lớp harness

1. **Ràng buộc dữ liệu:** chỉ chấp nhận chuyến và giá có trong kho dữ liệu, khớp hành trình, ngày bay và ngân sách.
2. **Kiểm tra hoàn tất bằng mã:** chỉ báo đặt vé thành công nếu đặt chỗ đã thanh toán, giao dịch thành công và số tiền/chuyến/hành khách khớp yêu cầu.
3. **Kiểm tra quyền:** chỉ cho đặt và thanh toán giả lập khi khách bật quyền tự động, chuyến đã được xác minh, còn đủ ghế và nằm trong ngân sách.
4. **Bàn giao:** khi thiếu dữ liệu hoặc không có chuyến phù hợp, trả lý do, các công cụ đã thử, trạng thái hiện tại và câu hỏi cần khách trả lời.

## Giới hạn của mô hình giả lập

Mô hình giả lập dùng các quy tắc theo kịch bản để kết quả luôn tái lập được. Đây không phải mô hình ngôn ngữ tổng quát: chương trình nhận các trường có cấu trúc, không tự hiểu hội thoại tự do. Vì vậy, số lượt gọi và kết quả trong báo cáo chỉ so sánh ba luồng trên bộ dữ liệu nhỏ này; không thể dùng để kết luận mẫu nào luôn tốt hơn khi chạy với mô hình thật.

Ngân sách là giới hạn tối đa **cho mỗi hành khách**. `auto_purchase=True` trong yêu cầu kiểm thử cho phép chương trình tự đặt chỗ và thanh toán mô phỏng; harness vẫn từ chối nếu chuyến không đạt điều kiện. Không nhập hoặc lưu thông tin thẻ thật.
