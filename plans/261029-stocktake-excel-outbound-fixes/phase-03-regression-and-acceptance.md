# Phase 3 — Hồi quy và nghiệm thu theo luồng thật

Trạng thái: Completed. Ưu tiên: P1. Ước lượng: 1.5h. Phụ thuộc: [phase 1](./phase-01-excel-roundtrip.md), [phase 2](./phase-02-stocktake-ui-and-request-roles.md).

## Mục đích

Xác nhận các lỗi được sửa từ tải file, render form đến phân quyền và xử lý yêu cầu. Không dùng HTTP 200 hoặc test parser riêng để thay thế nghiệm thu toàn luồng.

## Tệp dự kiến bổ sung kết quả

| Hành động | Đường dẫn tuyệt đối | Nội dung |
|---|---|---|
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/docs/TEST_RESULTS.md` | Lệnh, kết quả thực, môi trường và giới hạn |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/plans/261029-stocktake-excel-outbound-fixes/plan.md` | Tiến độ sau khi xác minh |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/plans/261029-stocktake-excel-outbound-fixes/phase-01-excel-roundtrip.md` | Checklist phase 1 |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/plans/261029-stocktake-excel-outbound-fixes/phase-02-stocktake-ui-and-request-roles.md` | Checklist phase 2 |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/plans/261029-stocktake-excel-outbound-fixes/phase-03-regression-and-acceptance.md` | Checklist nghiệm thu |

## Kiểm tra tự động

Chạy tại `C:/Users/HaiChu/Documents/GitHub/oldschool` với database test riêng do pytest-django quản lý:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_stocktake_excel_request_regressions.py tests/test_stocktakes.py tests/test_purchasing.py tests/test_sales_outbound.py tests/test_ui_views.py tests/test_accounts.py tests/test_notifications.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe manage.py check
```

1. Rà test mới trước sửa để biết chúng bắt đúng nguyên nhân; sau sửa chạy suite mục tiêu.
2. Kiểm tra tải mẫu HTTP thật rồi POST upload ở cả 3 phân hệ, file tên cột dòng 1 và dòng 4, dòng lỗi giữ đúng số thứ tự.
3. Đối chiếu số lượng phiếu/dòng/stock movement trước và sau preview: không thay đổi. Chỉ thao tác lưu/duyệt/ghi nhận theo nghiệp vụ mới được ghi dữ liệu.
4. Test số thực tế 0, tồn bằng 0, thiếu tồn xuất, SKU sai/trùng, cột thiếu/trùng và header đổi thứ tự.
5. Test Admin, Quản lý CS1/CS2, Nhân viên CS1/CS2 cho menu, form, POST, service và truy cập chéo cơ sở.
6. Test yêu cầu mới và yêu cầu tồn tại từ trước: lập phiếu, từ chối, liên kết thông báo và redirect đều còn dùng được.
7. Chạy toàn suite sau khi suite mục tiêu đạt. Tách lỗi môi trường hoặc lỗi đã có khỏi lỗi phát sinh; không sửa lan phạm vi chỉ để có báo cáo xanh.

## QA trình duyệt

| Màn hình/luồng | Tài khoản | Kiểm tra |
|---|---|---|
| Tạo kiểm kê | Admin chọn CS1 rồi CS2; Quản lý CS1/CS2 | Nút trống biến mất; một nút lưu có icon/nhãn đúng; tồn riêng đúng cơ sở |
| Dòng kiểm kê | Các tài khoản được kiểm kê | Dòng mặc định, thêm/xóa dòng, thay SKU, SKU tồn 0; số đếm đã nhập không bị ghi đè |
| Upload kiểm kê và POST lỗi | Admin/Quản lý | Tồn riêng đúng với các SKU đọc từ Excel; dữ liệu giữ được khi validation thất bại |
| Sửa kiểm kê chưa duyệt | Admin/Quản lý được phép | Cột tồn nhất quán với semantics tồn hiện tại; lưu dùng service; chi tiết giữ snapshot đã lưu |
| Nhập Excel | Admin, Quản lý CS1 | Tải mẫu trên chính trang → điền → tải lên → preview; Quản lý CS2 vẫn bị chặn nhập NCC |
| Xuất Excel | Admin, Quản lý CS1/CS2 | Tải mẫu → điền số hợp lệ → preview; vượt tồn báo đúng lỗi thiếu tồn |
| Menu xuất bán | Admin, Quản lý CS1/CS2 | Không còn mục từ quầy và shortcut; vẫn có tạo phiếu xuất trực tiếp |
| Yêu cầu từ quầy | Nhân viên CS1/CS2 | Menu còn; gửi thành công đúng cơ sở; không có quyền tạo phiếu trực tiếp |
| Xử lý yêu cầu | Quản lý cùng cơ sở/Admin | Mở từ thẻ chờ hoặc thông báo; không có form tạo; lập phiếu/từ chối hoạt động |
| Bảng kiểm kê hẹp | Admin/Quản lý | Tên SKU dễ đọc, số tồn rõ, cuộn ngang hợp lý, nút thao tác không bị che |

Chụp ảnh sau sửa ở những vị trí tương ứng ảnh báo lỗi; kiểm tra console không có lỗi JS khi đổi SKU hoặc thêm dòng. Dùng tài khoản/dữ liệu demo để tránh tạo phiếu nghiệp vụ thật trong QA.

## Review và điều kiện hoàn tất

- Rà diff chỉ gồm thay đổi có chủ đích; giữ nguyên các sửa đổi có sẵn của người khác.
- Không còn HTML button lồng nhau; cột tồn không tạo truy vấn theo từng SKU.
- Helper Excel dùng chung, bảo toàn offset và phản hồi lỗi; không nới validation hoặc bỏ cơ chế bảo vệ upload/export.
- Quyền tạo được chặn tại view và service, quyền xử lý vẫn thuộc Admin/Quản lý và cô lập cơ sở.
- Tài liệu ghi rõ test pass/fail/skip và những kiểm tra trình duyệt thực sự đã thực hiện. Không ghi `completed` khi còn case bắt buộc chưa kiểm tra.

## Checklist

- [x] Suite mục tiêu đạt; kết quả được lưu.
- [x] Toàn suite và `manage.py check` được chạy, kết quả được phân loại.
- [x] QA trình duyệt đủ vai trò và luồng download → upload.
- [x] Không phát sinh phiếu/tồn trong thao tác preview.
- [x] Luồng Nhân viên → Quản lý xử lý vẫn đạt.
- [x] Review diff, cập nhật quyền và kết quả test.
- [x] Đồng bộ trạng thái cả ba phase và plan sau khi tất cả tiêu chí đạt.

## Câu hỏi còn mở

Không có câu hỏi kỹ thuật còn mở trong phạm vi đã duyệt. Cách hiểu giữ phần xử lý yêu cầu cho Admin/Quản lý đã ghi tại `plan.md`; nếu người dùng muốn bỏ cả quyền xử lý thì cần đổi thiết kế luồng nhận yêu cầu của Nhân viên trước khi triển khai phần đó.

## Kết quả hiện tại

- Suite mục tiêu: 37 passed, 84.29s, gồm 19 test hồi quy mới.
- `manage.py check`: 0 vấn đề.
- Edge/SQLite riêng: 46/46 checks đạt, 0 JavaScript page errors; [báo cáo](./reports/browser-qa.md), [JSON](./reports/browser-results.json). Root đã xem ảnh desktop và màn hình hẹp.
- Rà code và `git diff --check` đạt; chưa phát hiện lỗi chặn.
- Toàn suite: **54 passed, 1 skipped**, 115.16s. Skip dự kiến tại `tests/test_concurrency.py:38–39`: kiểm thử `select_for_update` đồng thời yêu cầu PostgreSQL live, môi trường hiện dùng SQLite. Không tuyên bố đã xác minh khóa đồng thời trên PostgreSQL.
- Giới hạn: browser kiểm tra chuyển yêu cầu sang trang lập phiếu và từ chối; không hoàn tất phiếu xuất trong browser. Các test nghiệp vụ hiện hữu kiểm tra hoàn tất/trừ tồn. Admin tạo kiểm kê kiểm tra CS1 mặc định; Quản lý CS2 kiểm tra cơ sở khác.
- Server QA đã dừng. Dọn runtime QA bị automatic approval review từ chối (`blocked by policy`); thư mục tạm còn lại, database ứng dụng không bị dùng. Đây là giới hạn housekeeping, không phải lỗi ứng dụng.
