# Kết quả so sánh ba thiết kế tác tử

Báo cáo này được tạo từ một lần chạy thực tế của `evaluate.py`. Mỗi thiết kế chạy trên cùng ba tình huống; phần nhật ký giữ lại đầu vào, kết quả, các bước gọi công cụ và số liệu của từng lượt.

## Bảng so sánh hiệu năng

| Thiết kế | Lượt MockLLM (tổng) | Trung bình/lượt | Lượt gọi công cụ (tổng) | Trung bình/lượt | Kết quả đúng kỳ vọng | Điều chỉnh kế hoạch | Nhận xét |
|---|---:|---:|---:|---:|---:|---:|---|
| ReAct | 8 | 2.67 | 6 | 2.00 | 3/3 | 0 | Ra quyết định từng bước; dùng nhiều lượt mô hình hơn khi cần phản hồi sau công cụ. |
| Lập kế hoạch rồi thực thi | 2 | 0.67 | 7 | 2.33 | 3/3 | 0 | Ít lượt mô hình nhất nhờ lập kế hoạch một lần; gọi nhiều công cụ hơn để kiểm tra toàn bộ ứng viên. |
| Lai: lập kế hoạch và thích ứng | 10 | 3.33 | 6 | 2.00 | 3/3 | 1 | Thích ứng và điều chỉnh kế hoạch khi phát hiện thiếu ghế; lượt mô hình cao nhất trong ca đặt vé thành công. |

**Tổng thể:** 9/9 lượt có trạng thái đúng kỳ vọng.

### Diễn giải

- Theo số lượt MockLLM, `plan_then_execute` tiết kiệm lời gọi mô hình nhất trong bộ kịch bản này; điều đó không tự động đồng nghĩa với độ trễ thấp hơn trong hệ thống thật.
- Theo số lượt gọi công cụ, ReAct và Lai thường dừng sau khi tìm được chuyến khả thi; lập kế hoạch rồi thực thi kiểm tra toàn bộ ứng viên trước khi chọn.
- Mẫu Lai thể hiện khả năng điều chỉnh kế hoạch trong tình huống chuyến rẻ nhất không đủ ghế. Chi phí mô hình tăng để đổi lấy bước suy luận thích ứng này.
- Cả ba được đánh giá trên cùng dữ liệu giả lập, và kết quả đúng kỳ vọng không chứng minh chất lượng với LLM hoặc dữ liệu chuyến bay thực.

## Nhật ký chi tiết 9 lượt chạy

Các trace dưới đây dùng cùng định dạng dễ đọc như terminal: yêu cầu, kế hoạch/quyết định, hành động công cụ, kết quả kiểm tra harness, kết quả và số liệu.

### 1. Đặt vé thành công — ReAct

```text
==============================================================================
LƯỢT 1/9 — Đặt vé thành công — ReAct
==============================================================================
YÊU CẦU
  SGN → HAN | Ngày: 2026-11-15 | Hành khách: 2 | Ngân sách: 6.000.000 VND/người

KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH
  ReAct không lập kế hoạch cố định; MockLLM chọn hành động dựa trên kết quả từng bước.

QUYẾT ĐỊNH / HÀNH ĐỘNG CỦA TÁC TỬ
  1. Tìm chuyến phù hợp
  2. Kiểm tra số ghế còn lại — chuyến VN101
  3. Kiểm tra số ghế còn lại — chuyến VJ201
  4. Tạo đặt chỗ
  5. Thanh toán mô phỏng
  6. Kiểm tra điều kiện hoàn tất

THỰC THI CÔNG CỤ
  1. tìm_chuyến_bay: tìm thấy 3 chuyến: VN101 (4.200.000 VND/người), VJ201 (5.000.000 VND/người), QH301 (5.800.000 VND/người)
  2. kiểm_tra_chỗ VN101: 1 ghế còn / 2 khách cần — không đủ ghế.
  3. kiểm_tra_chỗ VJ201: 5 ghế còn / 2 khách cần — đủ ghế.
  4. tạo_đặt_chỗ: mã BKG-1001, 10.000.000 VND, 2 hành khách.
  5. thanh_toán_mô_phỏng: mã giao dịch PAY-2001, trạng thái thành công.

KẾT QUẢ KIỂM TRA HARNESS
  1. Ràng buộc đầu vào: ĐẠT
  2. Ràng buộc dữ liệu chuyến: ĐẠT
  3. Phân quyền đặt và thanh toán: ĐẠT
  4. Tiêu chí hoàn tất bằng mã: ĐẠT — Đặt chỗ và thanh toán đã được xác minh bằng mã.

KẾT QUẢ
  ĐẶT VÉ THÀNH CÔNG: VJ201 — VietJet Air, 5.000.000 VND/người; tổng 10.000.000 VND.

SỐ LIỆU
  MockLLM: 6 lượt | Công cụ: 5 lượt | Điều chỉnh kế hoạch: 0
```

### 2. Đặt vé thành công — Lập kế hoạch rồi thực thi

```text
==============================================================================
LƯỢT 2/9 — Đặt vé thành công — Lập kế hoạch rồi thực thi
==============================================================================
YÊU CẦU
  SGN → HAN | Ngày: 2026-11-15 | Hành khách: 2 | Ngân sách: 6.000.000 VND/người

KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH
  Kế hoạch:
    1. Tìm chuyến theo hành trình, ngày bay và ngân sách
    2. Kiểm tra số ghế của các chuyến phù hợp
    3. Chọn chuyến rẻ nhất còn đủ ghế
    4. Tạo đặt chỗ mô phỏng
    5. Thanh toán mô phỏng
    6. Xác minh hoàn tất bằng harness

THỰC THI CÔNG CỤ
  1. tìm_chuyến_bay: tìm thấy 3 chuyến: VN101 (4.200.000 VND/người), VJ201 (5.000.000 VND/người), QH301 (5.800.000 VND/người)
  2. kiểm_tra_chỗ VN101: 1 ghế còn / 2 khách cần — không đủ ghế.
  3. kiểm_tra_chỗ VJ201: 5 ghế còn / 2 khách cần — đủ ghế.
  4. kiểm_tra_chỗ QH301: 8 ghế còn / 2 khách cần — đủ ghế.
  5. tạo_đặt_chỗ: mã BKG-1001, 10.000.000 VND, 2 hành khách.
  6. thanh_toán_mô_phỏng: mã giao dịch PAY-2001, trạng thái thành công.

KẾT QUẢ KIỂM TRA HARNESS
  1. Ràng buộc đầu vào: ĐẠT
  2. Ràng buộc dữ liệu chuyến: ĐẠT
  3. Phân quyền đặt và thanh toán: ĐẠT
  4. Tiêu chí hoàn tất bằng mã: ĐẠT — Đặt chỗ và thanh toán đã được xác minh bằng mã.

KẾT QUẢ
  ĐẶT VÉ THÀNH CÔNG: VJ201 — VietJet Air, 5.000.000 VND/người; tổng 10.000.000 VND.

SỐ LIỆU
  MockLLM: 1 lượt | Công cụ: 6 lượt | Điều chỉnh kế hoạch: 0
```

### 3. Đặt vé thành công — Lai: lập kế hoạch và thích ứng

```text
==============================================================================
LƯỢT 3/9 — Đặt vé thành công — Lai: lập kế hoạch và thích ứng
==============================================================================
YÊU CẦU
  SGN → HAN | Ngày: 2026-11-15 | Hành khách: 2 | Ngân sách: 6.000.000 VND/người

KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH
  Kế hoạch:
    1. Tìm chuyến theo hành trình, ngày bay và ngân sách
    2. Kiểm tra ghế chuyến đang xét
    3. Tạo đặt chỗ mô phỏng
    4. Thanh toán mô phỏng
  Kế hoạch điều chỉnh 1:
    1. check seats:VN101
    2. reassess candidates
    3. Tạo đặt chỗ mô phỏng
    4. Thanh toán mô phỏng
    5. Xác minh hoàn tất bằng harness
  Kế hoạch điều chỉnh 2:
    1. check seats:VJ201
    2. reassess candidates
    3. Tạo đặt chỗ mô phỏng
    4. Thanh toán mô phỏng
    5. Xác minh hoàn tất bằng harness
  Kế hoạch điều chỉnh 3:
    1. Tạo đặt chỗ mô phỏng
    2. Thanh toán mô phỏng
    3. Xác minh hoàn tất bằng harness
  Kế hoạch điều chỉnh 4:
    1. Thanh toán mô phỏng
    2. Xác minh hoàn tất bằng harness
  Kế hoạch điều chỉnh 5:
    1. Xác minh hoàn tất bằng harness
  Lai: cập nhật bước tiếp theo khi có kết quả quan sát mới.

QUYẾT ĐỊNH / HÀNH ĐỘNG CỦA TÁC TỬ
  1. Tìm chuyến phù hợp
  2. Kiểm tra số ghế còn lại — chuyến VN101
  3. Kiểm tra số ghế còn lại — chuyến VJ201
  4. Tạo đặt chỗ
  5. Thanh toán mô phỏng
  6. Kiểm tra điều kiện hoàn tất

THỰC THI CÔNG CỤ
  1. tìm_chuyến_bay: tìm thấy 3 chuyến: VN101 (4.200.000 VND/người), VJ201 (5.000.000 VND/người), QH301 (5.800.000 VND/người)
  2. kiểm_tra_chỗ VN101: 1 ghế còn / 2 khách cần — không đủ ghế.
  3. kiểm_tra_chỗ VJ201: 5 ghế còn / 2 khách cần — đủ ghế.
  4. tạo_đặt_chỗ: mã BKG-1001, 10.000.000 VND, 2 hành khách.
  5. thanh_toán_mô_phỏng: mã giao dịch PAY-2001, trạng thái thành công.

KẾT QUẢ KIỂM TRA HARNESS
  1. Ràng buộc đầu vào: ĐẠT
  2. Ràng buộc dữ liệu chuyến: ĐẠT
  3. Phân quyền đặt và thanh toán: ĐẠT
  4. Tiêu chí hoàn tất bằng mã: ĐẠT — Đặt chỗ và thanh toán đã được xác minh bằng mã.

KẾT QUẢ
  ĐẶT VÉ THÀNH CÔNG: VJ201 — VietJet Air, 5.000.000 VND/người; tổng 10.000.000 VND.

SỐ LIỆU
  MockLLM: 7 lượt | Công cụ: 5 lượt | Điều chỉnh kế hoạch: 1
```

### 4. Không có chuyến trong ngân sách — ReAct

```text
==============================================================================
LƯỢT 4/9 — Không có chuyến trong ngân sách — ReAct
==============================================================================
YÊU CẦU
  SGN → HAN | Ngày: 2026-11-15 | Hành khách: 2 | Ngân sách: 3.500.000 VND/người

KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH
  ReAct không lập kế hoạch cố định; MockLLM chọn hành động dựa trên kết quả từng bước.

QUYẾT ĐỊNH / HÀNH ĐỘNG CỦA TÁC TỬ
  1. Tìm chuyến phù hợp
  2. Bàn giao cho khách hàng — Không tìm thấy chuyến trong ngân sách.

THỰC THI CÔNG CỤ
  1. tìm_chuyến_bay: không tìm thấy chuyến thỏa điều kiện.

KẾT QUẢ KIỂM TRA HARNESS
  1. Ràng buộc đầu vào: ĐẠT
  2. Ràng buộc dữ liệu chuyến: ĐẠT
  3. Phân quyền đặt và thanh toán: Không thực hiện do không có chuyến đủ điều kiện
  4. Tiêu chí hoàn tất bằng mã: CHƯA ĐẠT

KẾT QUẢ
  CHƯA ĐẶT VÉ: Không tìm thấy chuyến trong ngân sách.
  Bàn giao: Không cần cung cấp thêm thông tin. Hãy tự đặt vé qua hãng hàng không hoặc đại lý phù hợp; agent không thể đặt chuyến theo các điều kiện hiện tại.

SỐ LIỆU
  MockLLM: 2 lượt | Công cụ: 1 lượt | Điều chỉnh kế hoạch: 0
```

### 5. Không có chuyến trong ngân sách — Lập kế hoạch rồi thực thi

```text
==============================================================================
LƯỢT 5/9 — Không có chuyến trong ngân sách — Lập kế hoạch rồi thực thi
==============================================================================
YÊU CẦU
  SGN → HAN | Ngày: 2026-11-15 | Hành khách: 2 | Ngân sách: 3.500.000 VND/người

KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH
  Kế hoạch:
    1. Tìm chuyến theo hành trình, ngày bay và ngân sách
    2. Kiểm tra số ghế của các chuyến phù hợp
    3. Chọn chuyến rẻ nhất còn đủ ghế
    4. Tạo đặt chỗ mô phỏng
    5. Thanh toán mô phỏng
    6. Xác minh hoàn tất bằng harness

THỰC THI CÔNG CỤ
  1. tìm_chuyến_bay: không tìm thấy chuyến thỏa điều kiện.

KẾT QUẢ KIỂM TRA HARNESS
  1. Ràng buộc đầu vào: ĐẠT
  2. Ràng buộc dữ liệu chuyến: ĐẠT
  3. Phân quyền đặt và thanh toán: Không thực hiện do không có chuyến đủ điều kiện
  4. Tiêu chí hoàn tất bằng mã: CHƯA ĐẠT

KẾT QUẢ
  CHƯA ĐẶT VÉ: Không tìm thấy chuyến trong ngân sách mỗi hành khách.
  Bàn giao: Không cần cung cấp thêm thông tin. Hãy tự đặt vé qua hãng hàng không hoặc đại lý phù hợp; agent không thể đặt chuyến theo các điều kiện hiện tại.

SỐ LIỆU
  MockLLM: 1 lượt | Công cụ: 1 lượt | Điều chỉnh kế hoạch: 0
```

### 6. Không có chuyến trong ngân sách — Lai: lập kế hoạch và thích ứng

```text
==============================================================================
LƯỢT 6/9 — Không có chuyến trong ngân sách — Lai: lập kế hoạch và thích ứng
==============================================================================
YÊU CẦU
  SGN → HAN | Ngày: 2026-11-15 | Hành khách: 2 | Ngân sách: 3.500.000 VND/người

KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH
  Kế hoạch:
    1. Tìm chuyến theo hành trình, ngày bay và ngân sách
    2. Kiểm tra ghế chuyến đang xét
    3. Tạo đặt chỗ mô phỏng
    4. Thanh toán mô phỏng
  Kế hoạch điều chỉnh 1:
    1. handoff
  Lai: cập nhật bước tiếp theo khi có kết quả quan sát mới.

QUYẾT ĐỊNH / HÀNH ĐỘNG CỦA TÁC TỬ
  1. Tìm chuyến phù hợp
  2. Bàn giao cho khách hàng — Không tìm thấy chuyến trong ngân sách.

THỰC THI CÔNG CỤ
  1. tìm_chuyến_bay: không tìm thấy chuyến thỏa điều kiện.

KẾT QUẢ KIỂM TRA HARNESS
  1. Ràng buộc đầu vào: ĐẠT
  2. Ràng buộc dữ liệu chuyến: ĐẠT
  3. Phân quyền đặt và thanh toán: Không thực hiện do không có chuyến đủ điều kiện
  4. Tiêu chí hoàn tất bằng mã: CHƯA ĐẠT

KẾT QUẢ
  CHƯA ĐẶT VÉ: Không tìm thấy chuyến trong ngân sách.
  Bàn giao: Không cần cung cấp thêm thông tin. Hãy tự đặt vé qua hãng hàng không hoặc đại lý phù hợp; agent không thể đặt chuyến theo các điều kiện hiện tại.

SỐ LIỆU
  MockLLM: 3 lượt | Công cụ: 1 lượt | Điều chỉnh kế hoạch: 0
```

### 7. Thiếu số lượng hành khách — ReAct

```text
==============================================================================
LƯỢT 7/9 — Thiếu số lượng hành khách — ReAct
==============================================================================
YÊU CẦU
  SGN → HAN | Ngày: 2026-11-15 | Hành khách: None | Ngân sách: 6.000.000 VND/người

KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH
  ReAct không lập kế hoạch cố định; MockLLM chọn hành động dựa trên kết quả từng bước.

THỰC THI CÔNG CỤ
  Không gọi công cụ.

KẾT QUẢ KIỂM TRA HARNESS
  1. Ràng buộc đầu vào: KHÔNG ĐẠT — Thiếu thông tin bắt buộc: passengers.
  2. Ràng buộc dữ liệu chuyến: Không áp dụng/chưa tìm chuyến
  3. Phân quyền đặt và thanh toán: Không thực hiện do yêu cầu đầu vào không hợp lệ
  4. Tiêu chí hoàn tất bằng mã: CHƯA ĐẠT

KẾT QUẢ
  CHƯA ĐẶT VÉ: Thiếu thông tin bắt buộc: passengers.
  Câu hỏi làm rõ: Bạn cần đặt vé cho bao nhiêu hành khách?
  Bàn giao: Vui lòng trả lời câu hỏi làm rõ để agent có thể tiếp tục.

SỐ LIỆU
  MockLLM: 0 lượt | Công cụ: 0 lượt | Điều chỉnh kế hoạch: 0
```

### 8. Thiếu số lượng hành khách — Lập kế hoạch rồi thực thi

```text
==============================================================================
LƯỢT 8/9 — Thiếu số lượng hành khách — Lập kế hoạch rồi thực thi
==============================================================================
YÊU CẦU
  SGN → HAN | Ngày: 2026-11-15 | Hành khách: None | Ngân sách: 6.000.000 VND/người

KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH
  Chưa lập kế hoạch vì yêu cầu không qua kiểm tra đầu vào.

THỰC THI CÔNG CỤ
  Không gọi công cụ.

KẾT QUẢ KIỂM TRA HARNESS
  1. Ràng buộc đầu vào: KHÔNG ĐẠT — Thiếu thông tin bắt buộc: passengers.
  2. Ràng buộc dữ liệu chuyến: Không áp dụng/chưa tìm chuyến
  3. Phân quyền đặt và thanh toán: Không thực hiện do yêu cầu đầu vào không hợp lệ
  4. Tiêu chí hoàn tất bằng mã: CHƯA ĐẠT

KẾT QUẢ
  CHƯA ĐẶT VÉ: Thiếu thông tin bắt buộc: passengers.
  Câu hỏi làm rõ: Bạn cần đặt vé cho bao nhiêu hành khách?
  Bàn giao: Vui lòng trả lời câu hỏi làm rõ để agent có thể tiếp tục.

SỐ LIỆU
  MockLLM: 0 lượt | Công cụ: 0 lượt | Điều chỉnh kế hoạch: 0
```

### 9. Thiếu số lượng hành khách — Lai: lập kế hoạch và thích ứng

```text
==============================================================================
LƯỢT 9/9 — Thiếu số lượng hành khách — Lai: lập kế hoạch và thích ứng
==============================================================================
YÊU CẦU
  SGN → HAN | Ngày: 2026-11-15 | Hành khách: None | Ngân sách: 6.000.000 VND/người

KẾ HOẠCH / CÁCH RA QUYẾT ĐỊNH
  Chưa lập kế hoạch vì yêu cầu không qua kiểm tra đầu vào.
  Lai: cập nhật bước tiếp theo khi có kết quả quan sát mới.

THỰC THI CÔNG CỤ
  Không gọi công cụ.

KẾT QUẢ KIỂM TRA HARNESS
  1. Ràng buộc đầu vào: KHÔNG ĐẠT — Thiếu thông tin bắt buộc: passengers.
  2. Ràng buộc dữ liệu chuyến: Không áp dụng/chưa tìm chuyến
  3. Phân quyền đặt và thanh toán: Không thực hiện do yêu cầu đầu vào không hợp lệ
  4. Tiêu chí hoàn tất bằng mã: CHƯA ĐẠT

KẾT QUẢ
  CHƯA ĐẶT VÉ: Thiếu thông tin bắt buộc: passengers.
  Câu hỏi làm rõ: Bạn cần đặt vé cho bao nhiêu hành khách?
  Bàn giao: Vui lòng trả lời câu hỏi làm rõ để agent có thể tiếp tục.

SỐ LIỆU
  MockLLM: 0 lượt | Công cụ: 0 lượt | Điều chỉnh kế hoạch: 0
```
