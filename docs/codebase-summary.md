# Tóm tắt Mã nguồn Hệ thống (Codebase Summary)

Tài liệu này cung cấp cái nhìn tổng quan về cấu trúc thư mục, trách nhiệm của từng module và danh sách tệp tin trong dự án **Old School Inventory Management System**.

---

## 1. Kiến trúc Phân tầng (Layered Architecture)
Mỗi phân hệ nghiệp vụ trong `apps/` tuân thủ nghiêm ngặt kiến trúc **Service & Selector Layer**:
- `models.py`: Định nghĩa thực thể dữ liệu, ràng buộc toàn vẹn (`CheckConstraint`, `UniqueConstraint`), chỉ mục (`Index`) và trạng thái (`TextChoices`), không chứa side-effect phức tạp trong `save()`.
- `selectors.py`: Chứa toàn bộ truy vấn đọc dữ liệu (`QuerySet`), lọc theo cơ sở (`filter_queryset_by_branch`), tìm kiếm, lọc theo khoảng thời gian và tổng hợp số liệu.
- `services.py`: Chứa toàn bộ giao dịch ghi dữ liệu (`@transaction.atomic`), kiểm tra điều kiện biên, khóa dòng (`select_for_update`), chuyển trạng thái phiếu và ghi sổ cái tồn kho.
- `forms.py`: Xác thực dữ liệu đầu vào từ phía người dùng và hiển thị thông báo lỗi tiếng Việt.
- `views.py`: Xử lý HTTP request/response, kiểm tra phân quyền (`@role_required`, `enforce_branch_access`) và kết xuất template.

---

## 2. Bảng Tổng hợp Các Module trong `apps/`

| App Module | Models Chính | Services Chính | Selectors Chính | Templates (`templates/`) |
| :--- | :--- | :--- | :--- | :--- |
| `apps.branches` | `CoSo` | — | — | Dùng chung trên thanh điều hướng `base.html` |
| `apps.accounts` | `User` | Logic khóa/mở khóa đăng nhập trong `AuthenticationForm` & `views.py` | — | `accounts/login.html`, `accounts/logout_confirm.html`, `403.html` |
| `apps.catalog` | `SanPham`, `BienThe` | `create_product_with_variants`, `update_product_with_variants`, `delete_or_discontinue_product`, `discontinue_product` | `list_products_for_branch`, `get_product_detail_for_branch` | `catalog/product_list.html`, `product_detail.html`, `product_form.html` |
| `apps.inventory` | `TonKho`, `StockMovement` | `apply_stock_movements`, `set_opening_stock`, `excel.py` | `get_stock_for_variant_and_branch`, `list_branch_stock`, `get_low_stock_items` | Dùng chung qua API tồn kho và xuất/nhập Excel |
| `apps.purchasing` | `NhaCungCap`, `PhieuNhapKho`, `ChiTietPhieuNhapKho` | `create_import_receipt`, `update_import_receipt`, `delete_import_receipt`, `approve_import_receipt`, `return_import_receipt` | `list_import_receipts`, `get_import_receipt_detail`, `get_import_activity_summary` | `purchasing/import_list.html`, `import_detail.html`, `import_form.html`, `supplier_list.html` |
| `apps.sales_outbound` | `YeuCauXuatHang`, `ChiTietYeuCauXuatHang`, `PhieuXuatHangBan`, `ChiTietPhieuXuatHangBan` | `create_outbound_request`, `reject_outbound_request`, `create_outbound_receipt`, `update_outbound_receipt`, `finalize_outbound_receipt`, `delete_outbound_receipt` | `list_outbound_requests`, `list_outbound_receipts`, `get_outbound_receipt_detail` | `sales_outbound/outbound_list.html`, `outbound_detail.html`, `outbound_form.html`, `outbound_print.html`, `request_list.html` |
| `apps.transfers` | `PhieuDieuChuyen`, `ChiTietPhieuDieuChuyen` | `create_transfer_request`, `accept_transfer_request`, `reject_transfer_request`, `dispatch_transfer`, `receive_transfer` | `list_transfers`, `get_transfer_detail` | `transfers/transfer_list.html`, `transfer_detail.html`, `transfer_form.html` |
| `apps.stocktakes` | `KiemKe`, `ChiTietKiemKe` | `create_stocktake`, `update_stocktake`, `delete_stocktake`, `approve_stocktake`, `reject_stocktake` | `list_stocktakes`, `get_stocktake_detail` | `stocktakes/stocktake_list.html`, `stocktake_detail.html`, `stocktake_form.html` |
| `apps.reports` | `BaoCao` | `save_report_snapshot` | `get_inventory_report`, `get_variant_movement_history` | `reports/report_dashboard.html`, `report_variant_detail.html` |
| `apps.notifications` | `ThongBao` | `sync_low_stock_alert`, `mark_notification_read`, `mark_all_notifications_read` | `get_unread_notifications_for_user` (trong `context_processors.py`) | `notifications/notification_list.html` + Dropdown chuông trên `base.html` |

---

## 3. Bộ Kiểm thử Tự động (`tests/`)
- `tests/conftest.py`: Khởi tạo fixtures chuẩn (`branch_cs1`, `branch_cs2`, `admin_user`, `manager_cs1`, `manager_cs2`, `staff_cs1`, `staff_cs2`, `supplier`, `product_with_variants`).
- `tests/test_accounts.py`: Kiểm thử đăng nhập, khóa tài khoản tạm thời sau 5 lần sai mật khẩu, phân quyền RBAC và chặn truy cập chéo cơ sở (bao gồm chặn `POST` trực tiếp trái phép).
- `tests/test_catalog.py`: Kiểm thử thêm/sửa sản phẩm & biến thể, xóa vật lý khi chưa có giao dịch, chặn xóa và chuyển ngừng kinh doanh khi đã có giao dịch.
- `tests/test_purchasing.py`: Kiểm thử tạo phiếu nhập kho tại CS1, chặn CS2 tạo phiếu nhập NCC, sửa/xóa phiếu chờ duyệt, phê duyệt tăng tồn kho, trả lại phiếu, nhập/xuất Excel và báo cáo hoạt động nhập kho.
- `tests/test_sales_outbound.py`: Kiểm thử luồng nhân viên tạo yêu cầu xuất kho $\rightarrow$ quản lý tạo phiếu xuất $\rightarrow$ ghi nhận hoàn tất trừ tồn kho, chặn xuất vượt tồn và in phiếu.
- `tests/test_transfers.py`: Kiểm thử điều chuyển liên cơ sở 2 bước (`CS1 -> CS2`), nhận đủ hàng và nhận thiếu hàng kèm cảnh báo.
- `tests/test_stocktakes.py`: Kiểm thử chụp snapshot tồn kho, tính chênh lệch `Khớp/Thiếu/Thừa`, nhập Excel kiểm kê và Chủ cửa hàng duyệt/từ chối biên bản.
- `tests/test_reports.py`: Kiểm thử công thức cân bằng tồn kho $\text{Đầu kỳ} + \text{Nhập} - \text{Xuất} = \text{Cuối kỳ}$ và xuất báo cáo Excel.
- `tests/test_notifications.py`: Kiểm thử sinh cảnh báo tồn kho thấp tự động, chống trùng lặp cảnh báo và tự động đóng cảnh báo khi nhập bù.
- `tests/test_concurrency.py`: Kiểm thử khóa dòng `select_for_update()` khi hoàn tất phiếu xuất, đảm bảo không bao giờ âm tồn kho.
- `tests/test_ui_views.py`: Kiểm thử kết xuất giao diện HTML, lọc khoảng thời gian hợp lệ/không hợp lệ và phân quyền giao diện.
