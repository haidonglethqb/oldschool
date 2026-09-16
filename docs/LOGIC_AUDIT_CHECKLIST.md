# Bảng Kiểm Tra Rà Soát Logic Toàn Diện (Comprehensive Logic Audit Checklist)

Tài liệu này ghi nhận kết quả rà soát logic từng dòng mã nguồn (Models, Services, Selectors, Forms, Views, Templates) đối chiếu với tài liệu đặc tả [docs/System.md](file:///D:/Documents/GitHub/oldschool/docs/System.md), báo cáo gốc `50K22.3-Nhom09-ChuDe6-BCTD2.docx` và kế hoạch triển khai 10 Phases.

---

## 1. Checklist Kiến trúc Cơ sở Dữ liệu & Động cơ Tồn kho Nguyên tử (Database & Atomic Stock Engine)

| Hạng mục Kiểm tra | Quy tắc Nghiệp vụ & Kỹ thuật | Tệp Triển khai | Kết quả |
| :--- | :--- | :--- | :--- |
| **DB-01** | Sử dụng **PostgreSQL 16** làm cơ sở dữ liệu chính thức (không dùng SQLite) | `config/settings.py`, `.env` | `[x] ĐẠT` |
| **DB-02** | Đầy đủ **19 thực thể dữ liệu** (14 bảng ERD gốc trong DOCX + 5 bảng mở rộng cho quy trình đề xuất Hình 4–6) | `apps/*/models.py`, `docs/DATABASE_DESIGN.md` | `[x] ĐẠT` |
| **DB-03** | Ràng buộc mức CSDL `CheckConstraint(so_luong >= 0)` trên `TonKho` — tuyệt đối không cho phép tồn kho âm | `apps/inventory/models.py` (`tonkho_so_luong_gte_0`) | `[x] ĐẠT` |
| **DB-04** | Ràng buộc duy nhất `UniqueConstraint(bien_the, co_so)` trên `TonKho` | `apps/inventory/models.py` (`unique_tonkho_bienthe_coso`) | `[x] ĐẠT` |
| **DB-05** | Khóa dòng bi quan `select_for_update()` theo thứ tự định sẵn (`ORDER BY bien_the_id ASC`) để chống Race Condition và Deadlock | `apps/inventory/services.py` (`apply_stock_movements`) | `[x] ĐẠT` |
| **DB-06** | Tương thích PostgreSQL `SELECT ... FOR UPDATE` khi đi kèm `select_related` trên khóa ngoại nullable (`of=("self",)`) | `apps/sales_outbound/services.py` (`finalize_outbound_receipt`) | `[x] ĐẠT` |
| **DB-07** | Mọi biến động tồn kho đều ghi nhận vào sổ cái bất biến `StockMovement` kèm `idempotency_key` chống ghi trùng | `apps/inventory/models.py`, `apps/inventory/services.py` | `[x] ĐẠT` |
| **DB-08** | Zero pending migrations (`python manage.py makemigrations --check --dry-run` trả về `No changes detected`) | `apps/*/migrations/` | `[x] ĐẠT` |

---

## 2. Checklist Phân quyền RBAC & Cô lập Dữ liệu Đa Cơ sở (Security & Multi-Branch Isolation)

| Hạng mục Kiểm tra | Quy tắc Nghiệp vụ & Kỹ thuật | Tệp Triển khai | Kết quả |
| :--- | :--- | :--- | :--- |
| **SEC-01** | Khóa tài khoản tạm thời 15 phút (`locked_until`) sau 5 lần đăng nhập sai liên tiếp (`UC-1`) | `apps/accounts/models.py`, `apps/accounts/views.py` | `[x] ĐẠT` |
| **SEC-02** | Hộp thoại xác nhận đăng xuất ("Có" / "Không") trên thanh điều hướng và trang xác nhận (`UC-2`) | `templates/base.html`, `templates/accounts/logout_confirm.html` | `[x] ĐẠT` |
| **SEC-03** | Chỉ `ADMIN` được phép chuyển đổi ngữ cảnh xem giữa `Toàn chuỗi`, `CS1` và `CS2`; `MANAGER` và `STAFF` bị khóa chặt vào `user.branch` | `apps/accounts/permissions.py`, `apps/accounts/views.py` | `[x] ĐẠT` |
| **SEC-04** | Chặn `MANAGER` của `CS2` truy cập hoặc gửi `POST` trực tiếp vào phân hệ Nhập kho NCC của Kho tổng `CS1` (trả về HTTP 403) | `apps/accounts/permissions.py` (`assert_can_manage_imports`) | `[x] ĐẠT` |
| **SEC-05** | Chặn `MANAGER` của `CS1` phê duyệt phiếu nhập kho do chính mình lập (`UC-4.9` chỉ cho phép `ADMIN`) | `apps/purchasing/services.py`, `apps/purchasing/views.py` | `[x] ĐẠT` |
| **SEC-06** | Chặn `MANAGER` phê duyệt/từ chối biên bản kiểm kê (`UC-6.10` chỉ cho phép `ADMIN`) | `apps/stocktakes/services.py`, `apps/stocktakes/views.py` | `[x] ĐẠT` |
| **SEC-07** | Chặn `STAFF` truy cập hoặc gửi `POST` trực tiếp tới các trang thêm/sửa/xóa hàng hóa, nhập kho, ghi nhận xuất kho, điều chuyển, kiểm kê, báo cáo | `apps/accounts/permissions.py` (`@role_required`), `tests/test_accounts.py` | `[x] ĐẠT` |
| **SEC-08** | Chặn truy cập chéo cơ sở qua đoán ID trên URL (`outbound_detail`, `outbound_finalize`, `stocktake_detail`, `transfer_detail`) | `apps/sales_outbound/views.py`, `apps/stocktakes/views.py`, `apps/transfers/views.py` | `[x] ĐẠT` |

---

## 3. Checklist Logic Nghiệp vụ theo Phân hệ (53 Use Cases & 3 Quy trình Đề xuất)

### 3.1. Quản lý Danh mục Hàng hóa & Biến thể SKU (`UC-3`, `UC-3.1` → `UC-3.7`)
- `[x]` **UC-3.1 & UC-3.2**: Hiển thị danh sách và chi tiết sản phẩm kèm biến thể SKU (`Màu sắc`, `Kích cỡ`, `Đơn giá`) và tồn kho phân tách theo từng cơ sở (`Còn hàng`, `Sắp hết hàng`, `Hết hàng`).
- `[x]` **UC-3.3**: Tạo sản phẩm mới kèm nhiều biến thể SKU; tự động khởi tạo dòng `TonKho` (`so_luong = 0`, `muc_ton_toi_thieu`) cho tất cả cơ sở.
- `[x]` **UC-3.4**: Kiểm tra phát sinh giao dịch (`has_product_transactions`) trên toàn bộ bảng chứng từ và sổ cái `StockMovement`. Nếu chưa phát sinh giao dịch và tồn bằng 0 → cho phép xóa vật lý; nếu đã phát sinh giao dịch → chặn xóa vật lý với thông báo tiếng Việt rõ ràng và hướng dẫn chuyển sang `Ngừng kinh doanh`.
- `[x]` **UC-3.5**: Cập nhật thông tin sản phẩm, thêm/sửa biến thể SKU và cập nhật ngưỡng tồn tối thiểu (`muc_ton_toi_thieu`).
- `[x]` **UC-3.6 & UC-3.7**: Tìm kiếm theo Mã hàng, Mã SKU, Tên hàng; lọc theo Nhóm hàng, Màu sắc, Kích cỡ, Tình trạng tồn kho và Trạng thái kinh doanh.

### 3.2. Quản lý Nhập kho từ Nhà cung cấp (`UC-4`, `UC-4.1` → `UC-4.11` & Hình 4)
- `[x]` **UC-4.1**: Tải lên file Excel (`.xlsx`), kiểm tra định dạng/cột bắt buộc/mã SKU/số lượng/đơn giá/chiết khấu, hiển thị bảng xem trước (preview) trước khi lưu.
- `[x]` **UC-4.2**: Tạo phiếu nhập kho tại Kho tổng `CS1` (`DRAFT` hoặc `PENDING_APPROVAL`); tính chính xác `thanh_tien = so_luong * don_gia - chiet_khau` và `tong_tien`. **Chưa cộng tồn kho khi chưa duyệt (`DEC-01`)**.
- `[x]` **UC-4.3 & UC-4.4**: Xem danh sách và chi tiết phiếu nhập kho kèm lịch sử người lập, người duyệt và lý do trả lại (nếu có).
- `[x]` **UC-4.5 & UC-4.6**: Tìm kiếm theo mã phiếu/tên NCC; lọc theo Nhà cung cấp, Trạng thái và Khoảng thời gian (`Từ ngày` - `Đến ngày`), cảnh báo rõ ràng nếu `Từ ngày > Đến ngày`.
- `[x]` **UC-4.7 & UC-4.8**: Cho phép sửa/xóa phiếu nhập khi ở trạng thái `DRAFT`, `PENDING_APPROVAL`, `RETURNED`; chặn tuyệt đối sửa/xóa khi đã `APPROVED`.
- `[x]` **UC-4.9**: Chủ cửa hàng (`ADMIN`) phê duyệt phiếu nhập (`APPROVED` $\rightarrow$ cộng tồn kho nguyên tử tại `CS1` + ghi `StockMovement.IMPORT_IN`) hoặc trả lại phiếu kèm lý do (`RETURNED` $\rightarrow$ giữ nguyên tồn kho).
- `[x]` **UC-4.10 & UC-4.11**: Xem thẻ tổng hợp hoạt động nhập kho theo kỳ, xuất Excel từng phiếu nhập (`import_export_excel`) và xuất Excel báo cáo tổng hợp hoạt động nhập kho theo kỳ (`import_report_export`), quản lý danh sách & thêm mới Nhà cung cấp (`supplier_list`).

### 3.3. Quản lý Xuất kho Bán hàng, Điều chuyển Liên Cơ sở & Cảnh báo Tồn kho (`UC-1.5`, `WF-5.0`, `UC-5.1` → `UC-5.13` & Hình 5)
- `[x]` **WF-5.0**: Nhân viên bán hàng (`STAFF`) lập Yêu cầu xuất hàng (`YeuCauXuatHang`) tại quầy; Quản lý cơ sở kiểm tra tồn kho và chuyển thành Phiếu xuất hàng bán (`PhieuXuatHangBan`) hoặc từ chối khi thiếu hàng.
- `[x]` **UC-5.1 & UC-5.2**: Tra cứu nhanh tồn kho theo biến thể SKU tại từng cơ sở; hỗ trợ tải file Excel (`.xlsx`) danh sách hàng xuất kèm kiểm tra tồn kho khả dụng.
- `[x]` **UC-5.3**: Quy trình điều chuyển liên cơ sở 2 bước hạch toán tồn kho độc lập:
  - Bước 1 (`dispatch_transfer` - `DISPATCHED`): Chỉ trừ tồn kho tại cơ sở xuất (`co_so_xuat` - `TRANSFER_OUT`), lượng hàng này được theo dõi ở trạng thái **Đang vận chuyển (`in_transit_qty`)**.
  - Bước 2 (`receive_transfer` - `RECEIVED` / `RECEIVED_WITH_SHORTAGE`): Cộng tồn kho tại cơ sở nhận (`co_so_nhan` - `TRANSFER_IN`) theo đúng số lượng thực nhận (`so_luong_nhan`). Nếu nhận thiếu (`so_luong_nhan < so_luong_xuat`), bắt buộc nhập ghi chú chênh lệch và phát thông báo cảnh báo.
- `[x]` **UC-5.4 & UC-5.5**: Lập và cập nhật phiếu xuất bán ở trạng thái `PENDING` (kiểm tra tồn kho khả dụng nhưng chưa trừ tồn kho).
- `[x]` **UC-5.6**: Ghi nhận hoàn tất phiếu xuất (`finalize_outbound_receipt`): khóa dòng `TonKho` (`select_for_update`), kiểm tra tồn kho lần cuối, trừ tồn kho nguyên tử (`SALE_OUT`), ghi sổ cái và chuyển sang `COMPLETED`.
- `[x]` **UC-5.7**: Xóa phiếu xuất khi còn `PENDING`; chặn xóa khi đã `COMPLETED`.
- `[x]` **UC-5.8, UC-5.9, UC-5.10, UC-5.11**: Xem danh sách, chi tiết, tìm kiếm và lọc phiếu xuất theo cơ sở, trạng thái, khoảng ngày (cảnh báo nếu `Từ ngày > Đến ngày`).
- `[x]` **UC-5.12**: In phiếu xuất kho (`outbound_print`) chỉ khả dụng khi phiếu đã `COMPLETED`.
- `[x]` **UC-5.13**: Tự động sinh cảnh báo tồn kho thấp (`ThongBao.LOW_STOCK`) ngay khi `so_luong <= muc_ton_toi_thieu`, chống trùng lặp thông báo đang mở (`is_resolved=False`) và tự động đóng cảnh báo khi tồn kho được nhập/điều chuyển bổ sung vượt ngưỡng.

### 3.4. Quản lý Kiểm kê Định kỳ & Đột xuất (`UC-1.6`, `UC-6.1` → `UC-6.10` & Hình 6)
- `[x]` **UC-6.1 & UC-6.2**: Xem danh sách và chi tiết biên bản kiểm kê theo phạm vi cơ sở, hiển thị đầy đủ tồn hệ thống snapshot, tồn thực tế, chênh lệch và tổng số SKU `Khớp / Thiếu / Thừa`.
- `[x]` **UC-6.3**: Tải lên file Excel kiểm kê (`.xlsx`), tự động đối chiếu với tồn kho hệ thống tại cơ sở và tính chênh lệch.
- `[x]` **UC-6.4, UC-6.5, UC-6.6**: Tạo mới và cập nhật biên bản kiểm kê khi ở trạng thái `PENDING`.
- `[x]` **UC-6.7**: Xóa biên bản kiểm kê khi chưa được phê duyệt (`PENDING`, `REJECTED`); chặn xóa khi đã `APPROVED`.
- `[x]` **UC-6.8 & UC-6.9**: Tìm kiếm và lọc biên bản kiểm kê theo cơ sở, trạng thái, khoảng thời gian (cảnh báo nếu `Từ ngày > Đến ngày`).
- `[x]` **UC-6.10**: Chủ cửa hàng (`ADMIN`) phê duyệt (`APPROVED`) hoặc từ chối (`REJECTED`) biên bản kiểm kê; giữ nguyên tồn kho hệ thống theo đúng quy tắc kiểm soát nội bộ (`DEC-03`).

### 3.5. Báo cáo Nhập - Xuất - Tồn & Phân tích Chuỗi Cung Ứng (`UC-1.7`, `UC-7.1` → `UC-7.5`)
- `[x]` **UC-7.1 & UC-7.2**: Tính toán chính xác phương trình cân bằng tồn kho theo kỳ:
  $$\text{Tồn cuối kỳ} = \text{Tồn đầu kỳ} + (\text{Nhập NCC} + \text{Nhập ĐC}) - (\text{Xuất bán} + \text{Xuất ĐC})$$
  Hiển thị biểu đồ trực quan Chart.js, phân nhóm `Hàng bán chạy`, `Hàng bán chậm / Tồn cao`, `Sắp hết / Hết hàng`, `Đang điều chuyển`, và drill-down sổ cái từng SKU (`report_variant_detail`).
- `[x]` **UC-7.3**: Xuất báo cáo Nhập - Xuất - Tồn ra file Excel (`.xlsx`) có chống Formula Injection.
- `[x]` **UC-7.4 & UC-7.5**: Tìm kiếm theo Mã SP/SKU/Tên hàng; lọc theo Cơ sở, Khoảng thời gian (`Từ ngày` - `Đến ngày`), Nhóm hàng, Màu sắc, Kích cỡ và Trạng thái tồn kho.

---

## 4. Checklist 10 Kịch bản Nghiệm thu Bắt buộc (`System.md` §20)

| Kịch bản | Mô tả Kiểm chứng | Bài Kiểm thử Tự động (`pytest`) | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Scenario 1** | Tồn kho chỉ tăng khi `ADMIN` phê duyệt phiếu nhập kho (`PENDING_APPROVAL` & `RETURNED` không làm tăng tồn) | `tests/test_purchasing.py::test_scenario_1_import_stock_only_increases_on_admin_approval` | `[x] PASSED` |
| **Scenario 2** | Cô lập dữ liệu giữa Cơ sở 1 và Cơ sở 2 (Quản lý CS2 bị chặn xem/tạo dữ liệu riêng của CS1) | `tests/test_accounts.py::test_scenario_2_branch_isolation_blocks_other_branch_switch` | `[x] PASSED` |
| **Scenario 3** | Chặn xuất vượt tồn & An toàn đồng thời khi 2 giao dịch cùng xuất các sản phẩm cuối cùng | `tests/test_concurrency.py::test_scenario_3_concurrent_outbound_serialization_prevents_negative_stock` | `[x] PASSED` |
| **Scenario 4** | Điều chuyển liên cơ sở 2 bước (`DISPATCHED` trừ kho xuất, `RECEIVED` cộng kho nhận) + xử lý nhận thiếu hàng | `tests/test_transfers.py::test_scenario_4_two_step_interbranch_transfer_accounting` | `[x] PASSED` |
| **Scenario 5** | Tự động phát cảnh báo tồn kho thấp khi `so_luong <= muc_ton_toi_thieu`, chống trùng lặp và tự đóng khi nhập bù | `tests/test_notifications.py::test_scenario_5_low_stock_alert_deduplication_and_auto_resolution` | `[x] PASSED` |
| **Scenario 6** | Bảo vệ xóa sản phẩm đã có lịch sử giao dịch (`UC-3.4`) và cho phép xóa sản phẩm mới chưa giao dịch | `tests/test_catalog.py::test_scenario_6_product_deletion_protection_vs_clean_deletion` | `[x] PASSED` |
| **Scenario 7** | Đối chiếu kiểm kê (`Khớp / Thiếu / Thừa`) và `ADMIN` duyệt không tự động ghi đè mù quáng tồn kho | `tests/test_stocktakes.py::test_scenario_7_stocktake_reconciliation_and_approval_preserves_stock` | `[x] PASSED` |
| **Scenario 8** | Chặn truy cập và chặn gửi `POST` trực tiếp trái phép từ `STAFF` hoặc `MANAGER` sai vai trò/sai cơ sở | `tests/test_accounts.py::test_scenario_8_direct_unauthorized_post_blocked_for_staff_and_wrong_branch_manager` | `[x] PASSED` |
| **Scenario 9** | Kiểm tra tải lên file Excel hợp lệ / lỗi từng dòng cho Nhập kho, Xuất kho, Kiểm kê và Xuất báo cáo `.xlsx` | `tests/test_purchasing.py::test_scenario_9_import_excel_upload_and_export` | `[x] PASSED` |
| **Scenario 10** | Đối chiếu công thức báo cáo $\text{Đầu kỳ} + \text{Nhập} - \text{Xuất} = \text{Cuối kỳ}$ khớp 100% với `TonKho` | `tests/test_reports.py::test_scenario_8_report_separates_sales_from_transfers_and_tracks_in_transit` | `[x] PASSED` |

---

## 5. Checklist Các Trường Hợp Biên Nâng Cao (Deep Edge-Case Hardening — Vòng Rà Soát 2 & 3)

| Mã Edge Case | Tình huống Biên (Boundary / Edge Case) | Cơ chế Bảo vệ đã Triển khai | Tệp Kiểm chứng | Kết quả |
| :--- | :--- | :--- | :--- | :--- |
| **EC-01** | Quản lý bấm "Lập phiếu xuất" 2 lần trên cùng một `YeuCauXuatHang` (nguy cơ lỗi `IntegrityError` trên `OneToOneField`) | Khóa dòng `YeuCauXuatHang` (`select_for_update()`), kiểm tra `trang_thai == PENDING` và chưa có `PhieuXuatHangBan` liên kết trước khi tạo phiếu | `apps/sales_outbound/services.py`, `tests/test_sales_outbound.py` | `[x] ĐẠT` |
| **EC-02** | Quản lý xóa một `PhieuXuatHangBan` đang ở trạng thái `PENDING` được tạo từ `YeuCauXuatHang` (nguy cơ `YeuCauXuatHang` bị kẹt vĩnh viễn ở `PROCESSED`) | Tự động hoàn trả `YeuCauXuatHang` về trạng thái `PENDING` (`nguoi_xu_ly=None`, `thoi_gian_xu_ly=None`) khi phiếu xuất `PENDING` liên kết bị xóa | `apps/sales_outbound/services.py`, `tests/test_sales_outbound.py` | `[x] ĐẠT` |
| **EC-03** | Biến thể SKU con (`BienThe.trang_thai == 'INACTIVE'`) bị ngừng kinh doanh riêng lẻ hoặc sản phẩm cha ngừng kinh doanh được đưa vào phiếu Nhập/Xuất/Điều chuyển/Kiểm kê/Excel | Kiểm tra kép cả `variant.san_pham.trang_thai == 'ACTIVE'` và `variant.trang_thai == 'ACTIVE'` ở mọi Service và bộ đọc Excel; đồng bộ trạng thái biến thể khi đổi trạng thái sản phẩm cha | `apps/*/services.py`, `apps/inventory/excel.py`, `tests/test_catalog.py` | `[x] ĐẠT` |
| **EC-04** | Cơ sở xuất điều chuyển nhập số lượng thực xuất vượt quá số lượng yêu cầu (`so_luong_xuat > so_luong_yeu_cau`) | Chặn ngay trong `dispatch_transfer` với thông báo lỗi tiếng Việt rõ ràng nếu `qty_out > line.so_luong_yeu_cau` + đặt `max="{{ line.so_luong_yeu_cau }}"` trên form HTML | `apps/transfers/services.py`, `templates/transfers/transfer_detail.html`, `tests/test_transfers.py` | `[x] ĐẠT` |
| **EC-05** | Admin bấm "Trả lại" một phiếu nhập đã ở trạng thái `RETURNED` hoặc bấm "Từ chối" một biên bản kiểm kê đã `REJECTED` | Kiểm tra chặn thao tác lặp trên phiếu đã `RETURNED` / `REJECTED` trong `return_import_receipt` và `reject_stocktake` | `apps/purchasing/services.py`, `apps/stocktakes/services.py` | `[x] ĐẠT` |
| **EC-06** | Khi cập nhật sản phẩm (`update_product_and_variants`), người dùng sửa hoặc thêm biến thể bị trùng `ma_sku` hoặc trùng cặp `(mau_sac, kich_co)` | Kiểm tra `exclude(pk=vid)` cho cả `ma_sku` và `(san_pham, mau_sac, kich_co)` trước khi lưu để ném `ValidationError` tiếng Việt thay vì `IntegrityError` | `apps/catalog/services.py` | `[x] ĐẠT` |
| **EC-07** | Tham số điều hướng `next=//evil.com` (Open Redirect) trên form Đăng nhập hoặc Chuyển cơ sở | Xác thực bằng `url_has_allowed_host_and_scheme(..., allowed_hosts={request.get_host()})` | `apps/accounts/views.py` | `[x] ĐẠT` |
| **EC-08** | Đồng bộ số lượng thông báo chưa đọc trên chuông Navbar (`oldschool_global_context`) với trang `/notifications/` cho cả `ADMIN`, `MANAGER`, `STAFF` | Dùng chung hàm `_get_user_notifications_queryset(user, active_branch)` giữa Context Processor và Notification Views | `apps/accounts/context_processors.py`, `apps/notifications/views.py` | `[x] ĐẠT` |
| **EC-09** | Tải file Excel mẫu Nhập kho (`download_excel_template_view('import')`) khi đã có biến thể `ACTIVE` trong DB gây `TypeError: unsupported operand type(s) for *: 'decimal.Decimal' and 'float'` do phép nhân `v.don_gia * 0.65` | Sửa thành `int(v.don_gia * Decimal("0.65"))` và bổ sung bài kiểm thử tự động tải cả 3 mẫu Excel (`import`, `outbound`, `stocktake`) + API `api_variant_stock` | `apps/inventory/views.py`, `tests/test_ui_views.py` | `[x] ĐẠT` |
| **EC-10** | Thanh điều hướng (`templates/base.html`) kiểm tra đường dẫn `/sales-outbound/` thay vì `/outbound/` làm tab "Xuất kho & Điều chuyển" không sáng `active` khi ở phân hệ Xuất bán | Sửa điều kiện thành `{% if '/outbound/' in request.path or '/transfers/' in request.path %}active{% endif %}` | `templates/base.html` | `[x] ĐẠT` |
| **EC-11** | Đường dẫn đích (`target_url`) trong thông báo từ chối yêu cầu xuất hàng (`reject_outbound_request`) dùng chuỗi cứng `/sales-outbound/requests/` thay vì `/outbound/requests/` | Sử dụng `reverse("sales_outbound:request_list")` với fallback `/outbound/requests/` | `apps/sales_outbound/services.py` | `[x] ĐẠT` |
| **EC-12** | Màn hình chỉnh sửa mặt hàng (`product_edit_view` / `product_form.html`) hiển thị cứng `value="5"` cho cột `Tồn tối thiểu` của từng biến thể thay vì giá trị thực tế trong `TonKho` | Gắn `v.min_threshold` từ `TonKho` cho từng biến thể trong `product_edit_view` và hiển thị `value="{{ v.min_threshold|default:5 }}"` trên `product_form.html` | `apps/catalog/views.py`, `templates/catalog/product_form.html` | `[x] ĐẠT` |
| **EC-13** | Màn hình chi tiết phiếu nhập (`import_detail.html`) vẫn hiện nút "Yêu cầu chỉnh sửa lại" đối với phiếu nhập đã ở trạng thái `RETURNED` | Ẩn nút "Yêu cầu chỉnh sửa lại" khi `receipt.trang_thai == 'RETURNED'` (đồng bộ với chốt chặn backend `EC-05`) | `templates/purchasing/import_detail.html` | `[x] ĐẠT` |
