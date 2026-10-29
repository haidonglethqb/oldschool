# Phase 2 — Kiểm kê rõ ràng và đúng quyền tạo yêu cầu từ quầy

Trạng thái: Completed. Ưu tiên: P1. Ước lượng: 2.5h. Bối cảnh: [plan.md](./plan.md).

## Bằng chứng và kiến trúc

- `stocktake_form.html` dòng 123–125 có `<button>` ngoài bọc hai nhánh nút theo vai trò. HTML không hợp lệ gây nút nâu trống; không phải thiếu icon đơn thuần.
- Option SKU ghép số tồn ở ba nơi: `initial_lines`, dòng mặc định và `stocktakeLineTemplate`.
- `_get_branch_variants_for_stocktake` đã cung cấp `v.system_qty` từ tồn cơ sở; không cần thêm truy vấn từng dòng hay endpoint mới.
- `base.html` dòng 63 và `outbound_list.html` dòng 13–15 hiện hiển thị liên kết yêu cầu từ quầy cho mọi vai trò. Trang `request_list.html` luôn có form tạo; view và `create_outbound_request` đều cho Admin/Quản lý tạo.
- Thẻ yêu cầu chờ, chuyển thành phiếu qua `from_request`, từ chối và thông báo là luồng xử lý cần giữ cho yêu cầu Nhân viên.

## Tệp dự kiến sửa

| Hành động | Đường dẫn tuyệt đối | Nội dung |
|---|---|---|
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/templates/stocktakes/stocktake_form.html` | Một nút lưu; cột tồn riêng và đồng bộ dòng |
| Modify nếu cần | `C:/Users/HaiChu/Documents/GitHub/oldschool/apps/stocktakes/views.py` | Chỉ chuẩn bị dữ liệu hiển thị tồn theo hàng khi template cần |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/templates/base.html` | Link tạo yêu cầu từ quầy chỉ cho STAFF |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/templates/sales_outbound/outbound_list.html` | Shortcut từ quầy chỉ cho STAFF; giữ thẻ chờ xử lý |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/templates/sales_outbound/request_list.html` | Form tạo chỉ STAFF; Admin/Quản lý có danh sách xử lý đầy đủ chiều rộng |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/apps/sales_outbound/views.py` | Chặn POST tạo của Admin/Quản lý; giữ GET xử lý và scope cơ sở |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/apps/sales_outbound/services.py` | `create_outbound_request` chỉ nhận actor STAFF |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/docs/PERMISSIONS.md` | Tách quyền tạo của STAFF khỏi quyền xem/xử lý của Admin/Quản lý |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/tests/test_ui_views.py` | Render, số nút, nhãn, cột và các vai trò |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/tests/test_sales_outbound.py` | Quyền HTTP/service, tạo và xử lý yêu cầu |
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/tests/test_accounts.py` | Cô lập cơ sở và POST trái quyền |
| Modify nếu cần | `C:/Users/HaiChu/Documents/GitHub/oldschool/tests/test_notifications.py` | Điều hướng thông báo vẫn đến nơi xử lý |

Không xóa model, URL, yêu cầu cũ hoặc quyền tạo phiếu xuất trực tiếp. Không cần migration.

## Các bước sửa kiểm kê

1. Bỏ button bọc ngoài. Dùng một submit button với icon/text điều kiện bên trong: Admin `Lưu`; Quản lý `Lưu & Gửi chờ phê duyệt`. Giữ `name=form_action`, `value=submit`; không đổi nghiệp vụ hiện hữu: tạo kiểm kê bởi Admin tự `APPROVED`, bởi Quản lý là `PENDING`.
2. Đổi heading thành `Sản phẩm / SKU`; thêm `Tồn hệ thống tại <cơ sở>` ngay trước `Số lượng thực tế`. Cân lại độ rộng, căn số, giữ bảng cuộn ngang trên màn hình hẹp.
3. Bỏ `[Hệ thống: ...]` khỏi cả ba bộ option. Gắn `data-system-qty` hoặc bản đồ SKU → tồn từ dữ liệu server đã có; ô tồn là text/read-only, không nhận giá trị POST làm dữ liệu chuẩn.
4. Khởi tạo ô tồn cho mọi dòng được render: mặc định, upload Excel, edit và POST lỗi validation. Khi thay SKU, chỉ cập nhật ô tồn; giữ nguyên số kiểm đếm người dùng đã nhập.
5. Khi thêm dòng, ô tồn hiển thị `—` đến lúc chọn SKU; chọn SKU có tồn bằng 0 phải hiện `0`. Dùng một hàm đồng bộ và event delegation để dòng mới có cùng hành vi.
6. Chọn semantics hiện tại: cột trên form tạo/sửa hiển thị tồn hiện tại lúc tải trang. Service kiểm kê tiếp tục lấy tồn lại khi lưu; trang chi tiết dùng snapshot đã lưu. Không ghi đè logic snapshot từ phía trình duyệt.

## Các bước sửa quyền yêu cầu từ quầy

1. Bọc menu và shortcut có nhãn `Yêu cầu xuất từ quầy...` bằng điều kiện `role == STAFF`.
2. Render form tạo trong `request_list.html` chỉ cho STAFF. Admin/Quản lý vẫn GET danh sách xử lý, có `Lập phiếu`/`Từ chối` cho yêu cầu chờ đúng quyền.
3. Trong view dùng chung, chặn POST tạo với actor không phải STAFF bằng `PermissionDenied` trước validate form hoặc ghi dữ liệu. Không gắn decorator chỉ STAFF lên cả view vì sẽ làm hỏng GET xử lý của quản lý và các thông báo hiện hữu.
4. Trong `create_outbound_request`, thu hẹp `assert_roles` còn STAFF; tiếp tục `assert_branch_access`. Cập nhật docstring phù hợp. Caller trong `seed_oldschool.py` khoảng dòng 345 đã dùng `staff_cs2`, không cần sửa seed cho thay đổi quyền này.
5. Giữ `create_outbound_receipt` từ yêu cầu và `reject_outbound_request` cho Admin/Quản lý. Rà liên kết từ thông báo và redirect sau từ chối; chúng vẫn tới GET xử lý được, không xuất hiện form tạo.
6. Cập nhật ma trận quyền: STAFF tạo; Admin/Quản lý xem/xử lý theo cơ sở và tạo phiếu trực tiếp. Thay yêu cầu cũ trong tài liệu bằng quy tắc người dùng mới chỉ ở phần liên quan.

## Ma trận vai trò

| Vai trò | Menu/shortcut từ quầy | Form/POST tạo | Service tạo | GET/xử lý yêu cầu | Tạo phiếu xuất trực tiếp |
|---|---|---|---|---|---|
| Admin | Ẩn | Ẩn/403 | Từ chối | Theo phạm vi Admin | Có |
| Quản lý CS1 | Ẩn | Ẩn/403 | Từ chối | Chỉ CS1 | Có |
| Quản lý CS2 | Ẩn | Ẩn/403 | Từ chối | Chỉ CS2 | Có |
| Nhân viên CS1 | Có | Có | Có, chỉ CS1 | Xem theo quyền hiện hữu; không xử lý | Không |
| Nhân viên CS2 | Có | Có | Có, chỉ CS2 | Xem theo quyền hiện hữu; không xử lý | Không |

## Nghiệm thu và rủi ro

- Test đúng một submit `form_action=submit` có nhãn/icon cho mỗi vai trò; kiểm tra DOM không có button lồng nhau trong trình duyệt.
- Bảng có cột tồn riêng ở đủ bốn đường đi: mở mới, thêm dòng, upload, form lỗi/edit. Chọn SKU khác không làm mất số đếm.
- Nhân viên gửi → Quản lý nhận thông báo → lập phiếu → hoàn tất vẫn chạy; trường hợp từ chối vẫn báo cho Nhân viên.
- POST giả bằng tài khoản Admin/Quản lý không sinh `YeuCauXuatHang`, dòng hàng hay thông báo. Chặn tương tự ở service để không chỉ ẩn UI.
- Cơ sở sai bị chặn như hiện tại. Tránh thay tất cả quyền đọc/xử lý thành STAFF vì sẽ cắt luồng quản lý.

## Checklist

- [x] Nút lưu hợp lệ, cột tồn đồng bộ cả dòng tĩnh và động.
- [x] Menu/shortcut/form tạo đúng vai trò.
- [x] POST và service chặn Admin/Quản lý tạo.
- [x] GET quản lý, thông báo, lập phiếu và từ chối vẫn hoạt động.
- [x] Tài liệu quyền khớp quy tắc mới.

Tiếp theo: [phase 3](./phase-03-regression-and-acceptance.md).

## Kết quả xác minh

Nút lưu, cột tồn và tương tác dòng đã triển khai; giữ nguyên số kiểm đếm khi đổi SKU. View/service chặn Admin/Quản lý tạo yêu cầu; danh sách xử lý và scope Admin ALL/CS1/CS2 được giữ. Các test mới gom tại `tests/test_stocktake_excel_request_regressions.py`; không cần sửa stocktake view, seed hay các tệp test cũ. Suite mục tiêu 37 passed, QA Edge 46/46 đạt, reviewer không có phát hiện chặn. [Kết quả](../../docs/TEST_RESULTS.md), [QA](./reports/browser-qa.md).
