# Tài liệu Bàn Giao Kỹ Thuật (Agent Handover Document)

> **Dự án**: Hệ thống Quản lý Tồn kho Thời trang Cổ điển — **Old School Inventory Management System**  
> **Khách hàng / Nghiệp vụ**: Hệ thống cửa hàng bán lẻ thời trang Vintage Old School (2 cơ sở: CS1 Kho tổng kiêm Cửa hàng 1, CS2 Cửa hàng kinh doanh 2).  
> **Ngôn ngữ & Công nghệ**: Python 3.12, Django 5.2.18 LTS, PostgreSQL 16, Bootstrap 5.3, Chart.js, pytest.  
> **Ngày bàn giao**: 26/10/2026.

---

## 1. Mục Đích & Phạm Vi Bàn Giao

Tài liệu này được biên soạn cho **AI Coding Agent kế tiếp** hoặc **Kỹ sư Phần mềm** tiếp nhận dự án. Dự án đã hoàn thiện 100% logic nghiệp vụ cho toàn bộ **53 Use Cases** (UC-1 → UC-7.5), **3 Quy trình Nghiệp vụ Đề xuất (Hình 4, Hình 5, Hình 6)**, và đáp ứng toàn bộ các quyết định kiến trúc (`DEC-01` → `DEC-08`).

Mọi quy định về khóa dòng bi quan (`SELECT FOR UPDATE`), hạch toán tồn kho nguyên tử (`Atomic Stock Engine`), phân quyền 3 cấp (`ADMIN`, `MANAGER`, `STAFF`), cô lập dữ liệu liên cơ sở và kiểm thử tự động đều đã được rà soát và kiểm chứng đạt 100%.

---

## 2. Cách Khởi Động & Kiểm Thử Nhanh

### 2.1. Yêu cầu Môi trường
- Hệ điều hành: Windows, macOS hoặc Linux.
- Python 3.12+ (đã cấu hình virtualenv tại `.venv`).
- PostgreSQL 16 (hoặc SQLite cho môi trường local test).

### 2.2. Các Lệnh Điều Hành Chính (PowerShell / Bash)
```powershell
# Kích hoạt virtualenv (Windows)
.\.venv\Scripts\Activate.ps1

# Kiểm tra tính toàn vẹn hệ thống
.\.venv\Scripts\python.exe manage.py check

# Kiểm tra migration (phải trả về: No changes detected)
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run

# Chạy seed dữ liệu chuẩn (2 cơ sở, 5 tài khoản demo, 5 sản phẩm/18 SKU, tồn kho thực tế)
.\.venv\Scripts\python.exe manage.py seed_oldschool

# Chạy toàn bộ bộ kiểm thử tự động (10 test suites)
.\.venv\Scripts\pytest.exe -v

# Chạy máy chủ phát triển
.\.venv\Scripts\python.exe manage.py runserver
```

---

## 3. Cấu Trúc Mã Nguồn (Repository Layout)

```text
oldschool/
├── manage.py
├── requirements.txt
├── pytest.ini
├── .env / .env.example
├── config/
│   ├── settings.py          # Cấu hình Django 5.2 LTS, PostgreSQL 16, Auth, Static/Media, Vi-VN
│   ├── urls.py              # Định tuyến gốc + handler403 tùy chỉnh
│   ├── wsgi.py / asgi.py
├── apps/
│   ├── branches/            # Cơ sở kinh doanh (CoSo: CS1 Kho tổng & CH, CS2 Cửa hàng)
│   ├── accounts/            # Người dùng (User), Xác thực (UC-1, UC-2), Phân quyền RBAC & Branch Isolation
│   ├── catalog/             # Danh mục hàng hóa (SanPham), Biến thể SKU (BienThe) (UC-3, UC-3.1 → UC-3.7)
│   ├── inventory/           # Động cơ Tồn kho Atomic (TonKho, StockMovement), Excel Parser/Exporter, Seed Command
│   ├── purchasing/          # Nhà cung cấp (NhaCungCap), Nhập kho (PhieuNhapKho, ChiTietPhieuNhapKho) (UC-4, UC-4.1 → UC-4.11)
│   ├── sales_outbound/      # Yêu cầu xuất (YeuCauXuatHang) & Phiếu xuất bán (PhieuXuatHangBan) (UC-1.5, WF-5.0, UC-5.1 → UC-5.12)
│   ├── transfers/           # Điều chuyển liên cơ sở 2 bước (PhieuDieuChuyen, ChiTietPhieuDieuChuyen) (UC-5.3)
│   ├── stocktakes/          # Kiểm kê định kỳ/đột xuất (KiemKe, ChiTietKiemKe) (UC-1.6, UC-6.1 → UC-6.10)
│   ├── reports/             # Báo cáo Nhập-Xuất-Tồn & Phân tích trực quan (BaoCao) (UC-1.7, UC-7.1 → UC-7.5)
│   └── notifications/       # Cảnh báo tồn kho thấp & Thông báo hệ thống (ThongBao) (UC-5.13)
├── templates/               # Giao diện HTML5 + Bootstrap 5.3 + Chart.js (tiếng Việt chuẩn thiết kế Figma)
├── static/                  # CSS (static/css/oldschool.css) & JS (static/js/oldschool.js)
├── tests/                   # 10 tệp kiểm thử pytest chuyên sâu (RBAC, Concurrency, Workflows, UI Views)
├── docs/                    # Toàn bộ tài liệu kiến trúc, đặc tả, thiết kế CSDL, phân quyền, kiểm thử & handover
└── plans/                   # Kế hoạch triển khai chi tiết
```

---

## 4. Chi tiết 9 Phân hệ (Domain Apps) & Tầng Nghiệp vụ

### 4.1. `apps.branches` — Quản lý Cơ sở (`CoSo`)
- **Model**: `CoSo` (`ma_co_so` unique, `ten_co_so`, `dia_chi`, `so_dien_thoai`, `la_kho_tong`, `trang_thai`).
- **Quy tắc**:
  - `CS1` (`la_kho_tong=True`): Kho tổng kiêm Cửa hàng kinh doanh số 1 — **chỉ CS1 mới được nhập hàng từ Nhà cung cấp (`UC-4.2`)**.
  - `CS2` (`la_kho_tong=False`): Cửa hàng kinh doanh số 2 — nhận hàng bổ sung thông qua **Phiếu điều chuyển liên cơ sở (`UC-5.3`)**.

### 4.2. `apps.accounts` — Xác thực, Vai trò & Phân quyền (`User`, `permissions.py`)
- **Model**: `User(AbstractUser)` với `role` (`ADMIN`, `MANAGER`, `STAFF`), `branch` (`FK -> CoSo`, bắt buộc đối với `MANAGER` và `STAFF`), `failed_login_attempts`, `locked_until`.
- **Cơ chế Khóa tạm thời (`UC-1`)**: Nhập sai mật khẩu 5 lần liên tiếp sẽ khóa tài khoản 15 phút (`locked_until`), tự động mở khóa khi hết hạn hoặc đăng nhập đúng sau hạn.
- **Hàm kiểm tra quyền dùng chung (`apps/accounts/permissions.py`)**:
  - `role_required(*allowed_roles)`: Decorator chặn truy cập theo vai trò, trả HTTP 403 (`templates/403.html`).
  - `get_effective_branch(request, allow_all_for_admin=True)`: Trả về cơ sở bắt buộc của `MANAGER`/`STAFF`, hoặc cơ sở đang chọn trên thanh navbar của `ADMIN` (mặc định `None` = Toàn chuỗi).
  - `assert_branch_access(user, branch)`: Ném `PermissionDenied` nếu `MANAGER`/`STAFF` cố truy cập dữ liệu của cơ sở khác.
  - `assert_can_manage_imports(user)`: Đảm bảo chỉ `ADMIN` hoặc `MANAGER` thuộc kho tổng `CS1` mới được lập/sửa/xóa phiếu nhập kho NCC.
  - `filter_by_branch(queryset, user, branch_field="co_so", active_branch=None)`: Tự động giới hạn `QuerySet` theo cơ sở của người dùng.

### 4.3. `apps.catalog` — Danh mục Hàng hóa & Biến thể SKU (`SanPham`, `BienThe`)
- **Models**:
  - `SanPham`: `ma_hang_hoa` (unique), `ten_hang_hoa`, `nhom_hang`, `thuong_hieu`, `don_vi_tinh`, `mo_ta`, `trang_thai` (`ACTIVE` / `INACTIVE`).
  - `BienThe`: `san_pham` (`FK`), `ma_sku` (unique), `mau_sac`, `kich_co`, `don_gia` (`>= 0`), `hinh_anh`, `trang_thai` (`ACTIVE` / `INACTIVE`).
  - Ràng buộc duy nhất `(san_pham, mau_sac, kich_co)`.
- **Services (`apps/catalog/services.py`)**:
  - `create_product_and_variants(...)`: Tạo `SanPham` + các `BienThe` + tự động khởi tạo dòng `TonKho` (`so_luong=0`) tại mọi cơ sở đang hoạt động.
  - `update_product_and_variants(...)`: Cập nhật thông tin sản phẩm, biến thể và ngưỡng tồn tối thiểu (`muc_ton_toi_thieu`), đồng thời đồng bộ cảnh báo tồn kho (`sync_low_stock_alert`).
  - `delete_product_safely(...)`: Kiểm tra phát sinh giao dịch trên bảng nhập, xuất, yêu cầu xuất, điều chuyển, kiểm kê và sổ cái `StockMovement`. Nếu chưa phát sinh giao dịch → xóa vật lý; nếu đã phát sinh giao dịch → chặn xóa vật lý để bảo toàn lịch sử.
  - `toggle_product_business_status(...)`: Chuyển sản phẩm và toàn bộ biến thể sang `INACTIVE` (`Ngừng kinh doanh`) hoặc kích hoạt lại, tự động giải quyết cảnh báo tồn kho mở nếu ngừng kinh doanh.

### 4.4. `apps.inventory` — Động cơ Tồn kho Atomic, Sổ cái & Tiện ích Excel (`TonKho`, `StockMovement`)
- **Models**:
  - `TonKho`: `bien_the`, `co_so`, `so_luong`, `muc_ton_toi_thieu`. Ràng buộc: `ton_kho_nonnegative_quantities` (`so_luong >= 0`), `uniq_branch_variant_stock` (`bien_the, co_so`). Thuộc tính `trang_thai_ton`: `OUT_OF_STOCK` (`0`), `LOW_STOCK` (`0 < so_luong <= muc_ton_toi_thieu`), `IN_STOCK` (`> muc_ton_toi_thieu`).
  - `StockMovement`: Sổ cái bất biến lưu `bien_the`, `co_so`, `loai_thay_doi` (`OPENING_BALANCE`, `PURCHASE_IN`, `SALE_OUT`, `TRANSFER_OUT`, `TRANSFER_IN`), `ma_chung_tu`, `so_luong_thay_doi`, `so_luong_truoc`, `so_luong_sau`, `nguoi_thuc_hien`, `ngay_tao`.
- **Atomic Stock Engine (`apps/inventory/services.py`)**:
  - `apply_stock_movements(*, co_so, items, movement_type, reference_type, reference_code, actor, note="")`:
    1. Gộp các dòng trùng `bien_the_id` và **sắp xếp tăng dần theo `bien_the_id`** để triệt tiêu nguy cơ deadlock khi nhiều giao dịch chạy đồng thời.
    2. Khóa bi quan các dòng `TonKho` bằng `select_for_update()`.
    3. Kiểm tra tồn kho khả dụng (`new_balance < 0` → raise `ValidationError` tiếng Việt rõ ràng và rollback toàn bộ transaction).
    4. Cập nhật `TonKho.so_luong`, tạo bản ghi `StockMovement`, và gọi `sync_low_stock_alert(ton_kho)` để phát/đóng cảnh báo tồn kho thấp tự động.
- **Excel Utilities (`apps/inventory/excel.py`)**:
  - `parse_import_excel(uploaded_file)`: Đọc file `.xlsx` cho nhập kho; kiểm tra SKU hoạt động, số lượng nguyên dương, đơn giá, chiết khấu.
  - `parse_outbound_excel(uploaded_file, branch)`: Đọc file `.xlsx` xuất kho kèm kiểm tra tồn khả dụng tại cơ sở.
  - `parse_stocktake_excel(uploaded_file, branch)`: Đọc file `.xlsx` kiểm kê và đối chiếu với tồn hệ thống.
  - `generate_excel_template(mode)`: Tạo file `.xlsx` mẫu tải về (chỉ lấy SKU của sản phẩm `ACTIVE`).
  - `export_import_receipt_excel(receipt)`: Xuất chi tiết 1 phiếu nhập kho ra `.xlsx`.
  - `export_import_activity_report_excel(receipts, summary, filters)`: Xuất báo cáo hoạt động nhập kho theo kỳ/nhà cung cấp ra `.xlsx` (`UC-4.10`).
  - `export_inventory_report_excel(report_rows, branch_label, date_from, date_to)`: Xuất báo cáo Nhập - Xuất - Tồn ra `.xlsx` (`UC-7.3`).

### 4.5. `apps.purchasing` — Quản lý Nhà cung cấp & Nhập kho (`NhaCungCap`, `PhieuNhapKho`, `ChiTietPhieuNhapKho`)
- **State Machine (`PhieuNhapKho`)**: `DRAFT` / `PENDING_APPROVAL` / `RETURNED` $\rightarrow$ `APPROVED` (hoặc `RETURNED` khi Admin trả lại kèm lý do).
- **Services (`apps/purchasing/services.py`)**:
  - `create_import_receipt(...)` (`UC-4.2`): Chỉ cho phép nhập vào Kho tổng `CS1`; tính `thanh_tien = so_luong * don_gia - chiet_khau` (chiết khấu VNĐ theo `DEC-08`).
  - `update_import_receipt(...)` (`UC-4.7`): Hỗ trợ lưu bản nháp (`DRAFT`) hoặc gửi phê duyệt (`PENDING_APPROVAL`), gửi thông báo Admin khi gửi lại phê duyệt.
  - `delete_import_receipt(...)` (`UC-4.8`): Chặn xóa khi đã `APPROVED`.
  - `approve_import_receipt(...)` (`UC-4.9`): Chỉ `ADMIN` được phê duyệt; khóa phiếu `select_for_update()`, chuyển trạng thái `APPROVED` và gọi `apply_stock_movements(..., movement_type=PURCHASE_IN)` để cộng tồn kho tại `CS1`.
  - `return_import_receipt(...)` (`UC-4.9`): Chỉ `ADMIN` được trả lại phiếu kèm lý do (`ly_do_tra_lai` bắt buộc), không cộng tồn kho.

### 4.6. `apps.sales_outbound` — Yêu cầu Xuất & Phiếu Xuất kho Bán hàng (`YeuCauXuatHang`, `PhieuXuatHangBan`)
- **Luồng Nghiệp vụ Đề xuất Hình 5 (`WF-5.0` + `UC-5.4` → `UC-5.12`)**:
  - `STAFF` (hoặc `MANAGER`) tạo `YeuCauXuatHang` (`PENDING`) tại cơ sở của mình.
  - `MANAGER` kiểm tra tồn kho khả dụng và lập `PhieuXuatHangBan` (`PENDING`) — có thể liên kết từ `YeuCauXuatHang` hoặc tạo trực tiếp/nhập từ Excel (`UC-5.2`). **Lưu ý**: Tạo phiếu `PENDING` chưa trừ tồn kho.
  - `MANAGER` nhấn **Ghi nhận hoàn tất (`finalize_outbound_receipt` - `UC-5.6`)**: Khóa phiếu bằng `select_for_update(of=("self",))` và gọi `apply_stock_movements(..., movement_type=SALE_OUT)` để khóa dòng `TonKho`, kiểm tra tồn kho lần cuối, trừ tồn kho atomic, ghi `StockMovement`, kích hoạt kiểm tra cảnh báo tồn thấp (`UC-5.13`), và chuyển phiếu sang `COMPLETED`.
  - Chỉ phiếu `COMPLETED` mới được phép in (`outbound_print_view` - `UC-5.12`) và bị cấm sửa/xóa (`UC-5.5`, `UC-5.7`).

### 4.7. `apps.transfers` — Điều chuyển Hàng hóa Liên Cơ sở 2 Bước (`PhieuDieuChuyen`, `ChiTietPhieuDieuChuyen`)
- **Luồng Nghiệp vụ Đề xuất Hình 5 (`UC-5.3`)**:
  1. `create_transfer_request(...)`: Quản lý cơ sở cần hàng (thường là `CS2`) tạo yêu cầu điều chuyển từ cơ sở cấp (`CS1`) $\rightarrow$ `REQUESTED`.
  2. `accept_transfer(...)` / `reject_transfer(...)`: Quản lý cơ sở cấp (`CS1`) xác nhận đủ hàng (`ACCEPTED`) hoặc từ chối kèm lý do (`REJECTED`).
  3. `dispatch_transfer(...)`: Quản lý cơ sở cấp (`CS1`) xác nhận xuất điều chuyển $\rightarrow$ trừ tồn kho atomic tại `co_so_xuat` (`TRANSFER_OUT`), chuyển trạng thái sang `DISPATCHED`.
  4. `receive_transfer(...)`: Quản lý cơ sở nhận (`CS2`) kiểm đếm thực tế (`so_luong_thuc_nhan` $\le$ `so_luong_xuat`):
     - Cộng tồn kho atomic tại `co_so_nhan` theo đúng `so_luong_thuc_nhan` (`TRANSFER_IN`).
     - Nếu `so_luong_thuc_nhan == so_luong_xuat` cho mọi dòng $\rightarrow$ `RECEIVED`.
     - Nếu có bất kỳ dòng nào `so_luong_thuc_nhan < so_luong_xuat` $\rightarrow$ bắt buộc nhập ghi chú bất thường, chuyển trạng thái sang `RECEIVED_WITH_SHORTAGE` và gửi thông báo `TRANSFER_ALERT` cho Chủ cửa hàng (`ADMIN`) và hai cơ sở.

### 4.8. `apps.stocktakes` — Kiểm kê Định kỳ & Đột xuất (`KiemKe`, `ChiTietKiemKe`)
- **Luồng Nghiệp vụ Đề xuất Hình 6 (`UC-1.6`, `UC-6.1` → `UC-6.10`)**:
  - `create_stocktake(...)`: Chụp snapshot `so_luong_he_thong` từ `TonKho` tại thời điểm lập biên bản; hỗ trợ nạp số lượng thực tế từ file Excel (`UC-6.3`) hoặc nhập tay; tự động tính `chenh_lech = so_luong_thuc_te - so_luong_he_thong`, phân loại từng dòng (`MATCH`, `SHORTAGE`, `EXCESS`) và cập nhật 3 bộ đếm tổng hợp (`tong_sku_khop`, `tong_sku_thieu`, `tong_sku_thua`).
  - `update_stocktake(...)` (`UC-6.4`): Cho phép sửa khi ở trạng thái `PENDING`, gửi thông báo cho Admin khi gửi lại.
  - `delete_stocktake(...)` (`UC-6.7`): Cho phép xóa khi ở `PENDING` hoặc `REJECTED`.
  - `approve_stocktake(...)` / `reject_stocktake(...)` (`UC-6.10`): Chỉ `ADMIN` được phê duyệt (`APPROVED`) hoặc từ chối (`REJECTED`) kèm ghi chú xử lý. Theo đúng đặc tả `UC-6.10`, việc phê duyệt biên bản kiểm kê ghi nhận kết quả đối soát và phương án xử lý mà **không tự động ghi đè mù quáng lên `TonKho.so_luong`**.

### 4.9. `apps.reports` & `apps.notifications` — Báo cáo Nhập - Xuất - Tồn & Cảnh báo Tồn kho
- **Reports (`apps/reports/selectors.py` & `services.py`)**:
  - `get_inventory_report(...)`: Tổng hợp từ `StockMovement` và `TonKho` theo kỳ (`date_from`, `date_to`), cơ sở, nhóm hàng, màu sắc, kích cỡ, trạng thái tồn kho và từ khóa:
    $$\text{Tồn đầu kỳ} = \text{Tồn hiện tại} - \Delta_{\text{từ đầu kỳ đến nay}}$$
    $$\text{Tồn cuối kỳ} = \text{Tồn đầu kỳ} + \text{Nhập} + \text{Nhận ĐC} - \text{Xuất bán} - \text{Xuất ĐC}$$
  - **Định giá tồn kho theo DEC-07**: Giá vốn `gia_von` tính theo đơn giá nhập bình quân từ các phiếu nhập kho đã được Admin phê duyệt (`PhieuNhapKho.trang_thai = APPROVED`).
  - **Hàng chậm luân chuyển**: Tính theo điều kiện chuẩn `sale_out_qty == 0 and closing_qty > 0`.
  - Cung cấp dữ liệu biểu đồ Chart.js, Top hàng bán chạy (`top_selling`), Hàng chậm luân chuyển (`slow_moving`), Danh sách SKU nguy cơ thiếu hụt (`low_stock_risks`), Lịch sử biến động theo SKU (`get_variant_movement_history`), Lưu bản chụp báo cáo (`BaoCao`, sinh mã kèm microsecond chống trùng) và Xuất Excel (`.xlsx`).
- **Notifications (`apps/notifications/services.py`)**:
  - `sync_low_stock_alert(ton_kho)` (`UC-5.13`): Khi `so_luong <= muc_ton_toi_thieu`, tạo thông báo `LOW_STOCK` cho cả Quản lý cơ sở và Chủ cửa hàng (`ADMIN`), chống trùng lặp thông báo đang mở (`da_giai_quyet=False`). Khi tồn kho được bổ sung `so_luong > muc_ton_toi_thieu` hoặc sản phẩm/biến thể ngừng kinh doanh, tự động đánh dấu `da_giai_quyet=True`.
  - Bản ghi thông báo cho Admin được lưu riêng theo từng người dùng để việc Admin đánh dấu đã đọc không làm mất trạng thái chưa đọc của Quản lý cơ sở.

---

## 5. Danh mục URL Endpoints Toàn Hệ thống

| Phân hệ | URL Pattern | URL Name | View xử lý | Quyền truy cập |
| :--- | :--- | :--- | :--- | :--- |
| **Accounts** | `/accounts/login/` | `accounts:login` | `login_view` | Công khai |
| **Accounts** | `/accounts/logout/` | `accounts:logout` | `logout_view` | Đã đăng nhập (`POST`) |
| **Accounts** | `/accounts/switch-branch/` | `accounts:switch_branch` | `switch_branch_view` | `ADMIN` |
| **Catalog** | `/catalog/` | `catalog:product_list` | `product_list_view` | `ADMIN`, `MANAGER`, `STAFF` |
| **Catalog** | `/catalog/create/` | `catalog:product_create` | `product_create_view` | `ADMIN`, `MANAGER` |
| **Catalog** | `/catalog/<int:pk>/` | `catalog:product_detail` | `product_detail_view` | `ADMIN`, `MANAGER`, `STAFF` |
| **Catalog** | `/catalog/<int:pk>/edit/` | `catalog:product_edit` | `product_edit_view` | `ADMIN`, `MANAGER` |
| **Catalog** | `/catalog/<int:pk>/delete/` | `catalog:product_delete` | `product_delete_view` | `ADMIN`, `MANAGER` (`POST`) |
| **Catalog** | `/catalog/<int:pk>/toggle-status/` | `catalog:product_toggle_status` | `product_toggle_status_view` | `ADMIN`, `MANAGER` (`POST`) |
| **Inventory** | `/inventory/api/variant-stock/` | `inventory:api_variant_stock` | `api_variant_stock_view` | `ADMIN`, `MANAGER`, `STAFF` |
| **Inventory** | `/inventory/templates/<str:template_type>/` | `inventory:download_template` | `download_excel_template_view` | `ADMIN`, `MANAGER`, `STAFF` |
| **Purchasing** | `/purchasing/` | `purchasing:import_list` | `import_list_view` | `ADMIN`, `MANAGER` (CS1) |
| **Purchasing** | `/purchasing/create/` | `purchasing:import_create` | `import_create_view` | `ADMIN`, `MANAGER` (CS1) |
| **Purchasing** | `/purchasing/<int:receipt_id>/` | `purchasing:import_detail` | `import_detail_view` | `ADMIN`, `MANAGER` (CS1) |
| **Purchasing** | `/purchasing/<int:receipt_id>/edit/` | `purchasing:import_update` | `import_update_view` | `ADMIN`, `MANAGER` (CS1) |
| **Purchasing** | `/purchasing/<int:receipt_id>/delete/` | `purchasing:import_delete` | `import_delete_view` | `ADMIN`, `MANAGER` (CS1) (`POST`) |
| **Purchasing** | `/purchasing/<int:receipt_id>/approve/` | `purchasing:import_approve` | `import_approve_view` | `ADMIN` (`POST`) |
| **Purchasing** | `/purchasing/<int:receipt_id>/return/` | `purchasing:import_return` | `import_return_view` | `ADMIN` (`POST`) |
| **Purchasing** | `/purchasing/<int:receipt_id>/export-excel/` | `purchasing:import_export_excel` | `import_export_excel_view` | `ADMIN`, `MANAGER` (CS1) |
| **Purchasing** | `/purchasing/export-report/` | `purchasing:import_report_export` | `import_report_export_view` | `ADMIN`, `MANAGER` (CS1) |
| **Purchasing** | `/purchasing/suppliers/` | `purchasing:supplier_list` | `supplier_list_create_view` | `ADMIN`, `MANAGER` (CS1) |
| **Sales Outbound** | `/outbound/` | `sales_outbound:outbound_list` | `outbound_list_view` | `ADMIN`, `MANAGER`, `STAFF` |
| **Sales Outbound** | `/outbound/create/` | `sales_outbound:outbound_create` | `outbound_create_view` | `ADMIN`, `MANAGER` |
| **Sales Outbound** | `/outbound/<int:receipt_id>/` | `sales_outbound:outbound_detail` | `outbound_detail_view` | `ADMIN`, `MANAGER`, `STAFF` |
| **Sales Outbound** | `/outbound/<int:receipt_id>/edit/` | `sales_outbound:outbound_update` | `outbound_update_view` | `ADMIN`, `MANAGER` |
| **Sales Outbound** | `/outbound/<int:receipt_id>/finalize/` | `sales_outbound:outbound_finalize` | `outbound_finalize_view` | `ADMIN`, `MANAGER` (`POST`) |
| **Sales Outbound** | `/outbound/<int:receipt_id>/delete/` | `sales_outbound:outbound_delete` | `outbound_delete_view` | `ADMIN`, `MANAGER` (`POST`) |
| **Sales Outbound** | `/outbound/<int:receipt_id>/print/` | `sales_outbound:outbound_print` | `outbound_print_view` | `ADMIN`, `MANAGER`, `STAFF` |
| **Sales Outbound** | `/outbound/requests/` | `sales_outbound:request_list` | `request_list_create_view` | `ADMIN`, `MANAGER`, `STAFF` |
| **Sales Outbound** | `/outbound/requests/<int:request_id>/reject/` | `sales_outbound:request_reject` | `request_reject_view` | `ADMIN`, `MANAGER` (`POST`) |
| **Transfers** | `/transfers/` | `transfers:transfer_list` | `transfer_list_view` | `ADMIN`, `MANAGER` |
| **Transfers** | `/transfers/create/` | `transfers:transfer_create` | `transfer_create_view` | `ADMIN`, `MANAGER` |
| **Transfers** | `/transfers/<int:transfer_id>/` | `transfers:transfer_detail` | `transfer_detail_view` | `ADMIN`, `MANAGER` |
| **Transfers** | `/transfers/<int:transfer_id>/accept/` | `transfers:transfer_accept` | `transfer_accept_view` | `ADMIN`, `MANAGER` (Cơ sở xuất) |
| **Transfers** | `/transfers/<int:transfer_id>/reject/` | `transfers:transfer_reject` | `transfer_reject_view` | `ADMIN`, `MANAGER` (Cơ sở xuất) |
| **Transfers** | `/transfers/<int:transfer_id>/dispatch/` | `transfers:transfer_dispatch` | `transfer_dispatch_view` | `ADMIN`, `MANAGER` (Cơ sở xuất) |
| **Transfers** | `/transfers/<int:transfer_id>/receive/` | `transfers:transfer_receive` | `transfer_receive_view` | `ADMIN`, `MANAGER` (Cơ sở nhận) |
| **Stocktakes** | `/stocktakes/` | `stocktakes:stocktake_list` | `stocktake_list_view` | `ADMIN`, `MANAGER` |
| **Stocktakes** | `/stocktakes/create/` | `stocktakes:stocktake_create` | `stocktake_create_view` | `ADMIN`, `MANAGER` |
| **Stocktakes** | `/stocktakes/<int:stocktake_id>/` | `stocktakes:stocktake_detail` | `stocktake_detail_view` | `ADMIN`, `MANAGER` |
| **Stocktakes** | `/stocktakes/<int:stocktake_id>/edit/` | `stocktakes:stocktake_update` | `stocktake_update_view` | `ADMIN`, `MANAGER` |
| **Stocktakes** | `/stocktakes/<int:stocktake_id>/delete/` | `stocktakes:stocktake_delete` | `stocktake_delete_view` | `ADMIN`, `MANAGER` (`POST`) |
| **Stocktakes** | `/stocktakes/<int:stocktake_id>/approve/` | `stocktakes:stocktake_approve` | `stocktake_approve_view` | `ADMIN` (`POST`) |
| **Stocktakes** | `/stocktakes/<int:stocktake_id>/reject/` | `stocktakes:stocktake_reject` | `stocktake_reject_view` | `ADMIN` (`POST`) |
| **Reports** | `/reports/` | `reports:report_dashboard` | `report_dashboard_view` | `ADMIN`, `MANAGER` |
| **Reports** | `/reports/variant/<int:variant_id>/` | `reports:report_variant_detail` | `report_variant_detail_view` | `ADMIN`, `MANAGER` |
| **Reports** | `/reports/save-snapshot/` | `reports:report_save_snapshot` | `report_save_snapshot_view` | `ADMIN`, `MANAGER` (`POST`) |
| **Notifications** | `/notifications/` | `notifications:list` | `notification_list_view` | `ADMIN`, `MANAGER`, `STAFF` |
| **Notifications** | `/notifications/<int:pk>/read/` | `notifications:mark_read` | `mark_notification_read_view` | `ADMIN`, `MANAGER`, `STAFF` (`POST`) |
| **Notifications** | `/notifications/mark-all-read/` | `notifications:mark_all_read` | `mark_all_read_view` | `ADMIN`, `MANAGER`, `STAFF` (`POST`) |

---

## 6. Tài khoản Demo Chuẩn (`seed_oldschool`)

| Vai trò | Tên đăng nhập | Mật khẩu | Cơ sở phụ trách |
| :--- | :--- | :--- | :--- |
| **Chủ cửa hàng (`ADMIN`)** | `admin_owner` | `OldSchool@123` | Toàn hệ thống (`CS1` & `CS2`) |
| **Quản lý Cơ sở 1 (`MANAGER`)** | `manager_cs1` | `OldSchool@123` | `CS1` — Kho tổng & Cửa hàng 1 (Đà Nẵng) |
| **Quản lý Cơ sở 2 (`MANAGER`)** | `manager_cs2` | `OldSchool@123` | `CS2` — Cửa hàng 2 (Đà Nẵng) |
| **Nhân viên Bán hàng CS1 (`STAFF`)** | `staff_cs1` | `OldSchool@123` | `CS1` — Kho tổng & Cửa hàng 1 |
| **Nhân viên Bán hàng CS2 (`STAFF`)** | `staff_cs2` | `OldSchool@123` | `CS2` — Cửa hàng 2 |

---

## 7. Lưu ý Quan trọng cho Agent Tiếp nhận (Critical Implementation Notes)
1. **Không bao giờ cập nhật trực tiếp `TonKho.so_luong` bên ngoài `apps/inventory/services.py`**: Mọi biến động tồn kho bắt buộc phải đi qua `apply_stock_movements()` hoặc `set_opening_stock()` để đảm bảo khóa dòng `select_for_update()`, ghi sổ cái `StockMovement`, và đồng bộ cảnh báo `ThongBao`.
2. **PostgreSQL `SELECT ... FOR UPDATE` với `nullable FK`**: Trong PostgreSQL 16, khi gọi `.select_for_update()` kèm `.select_related(...)` trên một khóa ngoại cho phép `NULL` (ví dụ `PhieuXuatHangBan.yeu_cau_xuat`), PostgreSQL tạo `LEFT OUTER JOIN` và từ chối khóa phía nullable. Luôn dùng `.select_for_update(of=("self",))` khi dùng chung với `select_related` có khóa ngoại nullable.
3. **Bảo toàn dữ liệu form khi ném `ValidationError`**: Toàn bộ các view xử lý form nhiều dòng (`product_create/edit`, `import_create/edit`, `outbound_create/edit`, `transfer_create`, `stocktake_create/edit`) đều trích xuất `initial_lines` / `submitted_variants` để giữ nguyên các dòng dữ liệu người dùng đã nhập khi gặp lỗi validation.
4. **Danh mục Tài liệu liên quan trong `docs/`**:
   - `docs/System.md`: Tài liệu yêu cầu tổng thể ban đầu.
   - `docs/REQUIREMENTS_MATRIX.md`: Ma trận truy vết 53 Use Cases sang Models, Services, Views, Tests.
   - `docs/LOGIC_AUDIT_CHECKLIST.md`: Bảng kiểm tra rà soát logic toàn diện từng phân hệ và 10 kịch bản nghiệm thu + danh mục Edge Cases EC-01 đến EC-28.
   - `docs/DATABASE_DESIGN.md` & `docs/ERD_AUDIT.md`: Thiết kế 19 bảng CSDL PostgreSQL và đối chiếu với báo cáo DOCX.
   - `docs/PERMISSIONS.md`: Ma trận phân quyền RBAC và cô lập dữ liệu cơ sở.
   - `docs/STOCK_WORKFLOWS.md`: Máy trạng thái và quy trình khóa dòng chống xung đột.
   - `docs/TEST_RESULTS.md` & `docs/DEMO_GUIDE.md`: Kết quả kiểm thử tự động và kịch bản chạy demo.
