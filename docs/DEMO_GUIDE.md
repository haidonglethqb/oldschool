# Hướng dẫn Trình diễn Hệ thống (Demo Walkthrough Guide — `DEMO_GUIDE.md`)

Tài liệu này hướng dẫn kịch bản trình diễn trực tiếp trên trình duyệt (5–10 phút) đi qua trọn vẹn các phân hệ nghiệp vụ và 10 kịch bản nghiệm thu của hệ thống **Old School**.

---

## 1. Khởi chạy hệ thống trước buổi Demo
```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_oldschool
.\.venv\Scripts\python.exe manage.py runserver 8000
```
Mở trình duyệt tại: `http://127.0.0.1:8000/accounts/login/`

---

## 2. Kịch bản Demo 6 Bước (Theo luồng chuỗi cung ứng thực tế)

### Bước 1: Đăng nhập Quản lý Cơ sở 2 (`manager_cs2` / `OldSchool@123`) — Kiểm tra cô lập cơ sở & Cảnh báo tồn kho
1. Đăng nhập bằng `manager_cs2`. Quan sát thanh ngữ cảnh hiển thị cố định: **CS2 — Cơ sở 2 - Thanh Khê**.
2. Trên menu **Danh mục hàng hóa**, lọc theo tình trạng **Sắp hết hàng** hoặc **Hết hàng** để thấy ngay `SP002-TRANG-M` (Tồn = 0, `Hết hàng`) và `SP001-DEN-L` (Tồn = 3, `Sắp hết hàng`).
3. Thử truy cập đường dẫn `/purchasing/` (Nhập kho của Kho tổng CS1) -> Hệ thống lập tức chặn với màn hình **403 — Từ chối quyền truy cập**.

### Bước 2: Quy trình Xuất bán tại Cơ sở 2 (`staff_cs2` & `manager_cs2`)
1. Vào menu **Xuất kho & Điều chuyển -> Phiếu xuất hàng bán**: Quan sát yêu cầu xuất từ nhân viên bán hàng `staff_cs2` đang chờ xử lý.
2. Bấm **Lập phiếu xuất** từ yêu cầu đó (hoặc tải file Excel mẫu `sample_data/excel/mau_xuat_kho.xlsx`), sau đó bấm **Lưu & Ghi nhận xuất kho ngay**.
3. Sau khi ghi nhận hoàn tất, bấm nút **In phiếu xuất kho (UC-5.12)** để mở mẫu phiếu in chuẩn của cửa hàng Old School.
4. Thử tạo một phiếu xuất với số lượng `999` (vượt tồn kho CS2) -> Hệ thống từ chối và báo lỗi rõ ràng bằng tiếng Việt, tồn kho được bảo toàn.

### Bước 3: Quy trình Điều chuyển Nội bộ 2 bước từ Kho tổng CS1 sang CS2 (`UC-5.3`)
1. Đang ở tài khoản `manager_cs2`, vào **Xuất kho & Điều chuyển -> Phiếu điều chuyển cơ sở**:
   - Xem phiếu `PDC-CS1-CS2-DEMO-001` đang ở trạng thái **Đang vận chuyển (Đã xuất)** (hàng đã trừ ở CS1 nhưng chưa cộng vào CS2).
   - Bấm vào chi tiết phiếu, nhập số lượng thực nhận tại Bước 2 và bấm **Xác nhận Đã nhận hàng** -> Tồn kho của `SP002-TRANG-M` tại CS2 lập tức tăng từ `0` lên `5`.

### Bước 4: Quy trình Nhập kho tại Kho tổng CS1 (`manager_cs1` / `OldSchool@123`)
1. Đăng xuất và đăng nhập bằng `manager_cs1`.
2. Vào **Nhập kho -> Tạo phiếu nhập mới**:
   - Có thể tải lên file `sample_data/excel/mau_nhap_kho.xlsx` để hệ thống đọc tự động, hoặc chọn Nhà cung cấp và nhập dòng hàng.
   - Bấm **Lưu & Gửi chờ phê duyệt**. Quan sát phiếu ở trạng thái **Chờ duyệt** và tồn kho CS1 **chưa tăng**.

### Bước 5: Quy trình Kiểm kê kho & Phê duyệt của Chủ cửa hàng (`admin_owner` / `OldSchool@123`)
1. Đăng xuất và đăng nhập bằng tài khoản Chủ cửa hàng `admin_owner`.
2. Trên thanh Header, chuyển đổi bộ chọn **Cơ sở** giữa `Tất cả cơ sở (Toàn chuỗi)` và từng cơ sở `CS1`, `CS2`, `CS3`.
3. Vào **Nhập kho -> Phiếu nhập kho**, mở phiếu `PNK-DEMO-002` (hoặc phiếu vừa tạo ở Bước 4), bấm **Duyệt phiếu nhập & Cộng tồn kho** -> Tồn kho Kho tổng CS1 tăng ngay lập tức.
4. Vào **Kiểm kê kho**, mở biên bản `KK-CS1-DEMO-001` (có dòng Khớp và dòng Thiếu), bấm **Phê duyệt biên bản** (`UC-6.10`) hoặc **Từ chối biên bản**.

### Bước 6: Báo cáo Xuất — Nhập — Tồn động & Xuất Excel (`UC-7.1` – `UC-7.5`)
1. Vào menu **Báo cáo**:
   - Quan sát 4 thẻ KPI tổng hợp, biểu đồ Chart.js và bảng chi tiết phân tách rõ **Nhập NCC**, **Nhập ĐC**, **Xuất bán**, **Xuất ĐC**, **Tồn cuối kỳ** và **Đang VC (In-Transit)**.
   - Chuyển đổi qua lại giữa các tab: `Tất cả mặt hàng`, `Hàng bán chạy`, `Hàng bán chậm / Tồn cao`, `Sắp hết / Hết hàng`, `Đang điều chuyển`.
   - Bấm biểu tượng đồng hồ ở cột **Sổ cái** của bất kỳ SKU nào để xem lịch sử bút toán bất biến (`StockMovement`).
   - Bấm **Xuất file Excel (UC-7.3)** để tải về bảng tính `.xlsx` đã định dạng.
