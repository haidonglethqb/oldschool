# Kiểm toán Sơ đồ Thực thể Liên kết & Thiết kế CSDL (`ERD_AUDIT.md`)

Tài liệu này đối chiếu ba tầng: **Yêu cầu Nghiệp vụ (Use Cases & BPMN) ↔ 12 Bảng dữ liệu trong `50K22.3-Nhom09-ChuDe6-BCTD2.docx` + Sơ đồ ERD (`BienThe`) ↔ Mô hình Django ORM thực thi**.

---

## 1. Tổng quan các Thực thể trong Tài liệu Gốc

Trong báo cáo `50K22.3-Nhom09-ChuDe6-BCTD2.docx` (Mục D.III, Bảng 55 → Bảng 66), có **12 bảng dữ liệu** được liệt kê:
1. `SanPham` (Bảng 55)
2. `NhaCungCap` (Bảng 56)
3. `PhieuNhapKho` (Bảng 57)
4. `ChiTietPhieuNhapKho` (Bảng 58)
5. `PhieuXuatHangBan` (Bảng 59)
6. `ChiTietPhieuXuatHangBan` (Bảng 60)
7. `PhieuDieuChuyen` (Bảng 61)
8. `ChiTietPhieuDieuChuyen` (Bảng 62)
9. `CoSo` (Bảng 63)
10. `KiemKe` (Bảng 64)
11. `ChiTietKiemKe` (Bảng 65)
12. `BaoCao` (Bảng 66)

Trên sơ đồ ERD mở rộng, thực thể thứ 13 là `BienThe` (Product Variant) được bổ sung để đáp ứng yêu cầu quản lý biến thể tại Mục VI.1.

---

## 2. Phân tích Bất cập & Sai lệch giữa DOCX Tables, ERD và Nghiệp vụ

### 2.1 Thực thể bị thiếu (Missing Entities)

| Thực thể bị thiếu | Lý do bắt buộc phải bổ sung | Mô hình Django tương ứng |
| :--- | :--- | :--- |
| **Tài khoản Người dùng (`User`)** | `UC-1`, `UC-2` và phân quyền 3 vai trò (`ADMIN`, `MANAGER`, `STAFF`) gắn với `CoSo` cần bảng người dùng chuẩn. Bảng `KiemKe` (Bảng 64) có các cột `tao_boi_id`, `duyet_boi_id`, `tu_choi_boi_id` nhưng không có bảng đích để tham chiếu FK. | `accounts.User` (kế thừa `AbstractUser`) |
| **Biến thể Sản phẩm (`BienThe`)** | Mục VI.1 quy định: *"Một sản phẩm có thể có nhiều biến thể khác nhau dựa trên màu sắc và kích thước. Mỗi biến thể có mã SKU riêng, số lượng tồn kho riêng và có thể có giá bán riêng"*. Bảng 55 (`SanPham`) trong DOCX lại gộp `mau_sac`, `kich_co` vào bảng cha. | `catalog.BienThe` |
| **Tồn kho theo Cơ sở × Biến thể (`TonKho`)** | Old School có 2 cơ sở (`CS1 - Kho tổng`, `CS2`), mỗi biến thể có số lượng tồn hiện tại và định mức tồn tối thiểu (`muc_ton_toi_thieu`) riêng tại từng cơ sở để kiểm soát xuất kho và cảnh báo `UC-5.13`. Trong 12 bảng gốc hoàn toàn chưa có bảng lưu tồn kho hiện hành. | `inventory.TonKho` (`UNIQUE(co_so, bien_the)`) |
| **Sổ cái Biến động Tồn kho (`StockMovement`)** | Để truy vết kiểm toán bất biến (immutable audit log) cho mọi giao dịch tăng/giảm tồn kho và tính toán chính xác Báo cáo Nhập - Xuất - Tồn theo kỳ (`UC-7.1`, `UC-7.2`), tách biệt giữa Xuất bán (`SALES_OUTBOUND`) và Điều chuyển (`TRANSFER_OUT`/`TRANSFER_IN`). | `inventory.StockMovement` |
| **Yêu cầu Xuất kho Bán hàng (`YeuCauXuatHang`)** | Quy trình xuất kho bán hàng đề xuất (Hình 5, Bước 1) mô tả Nhân viên bán hàng (`STAFF`) lập yêu cầu xuất kho gửi Quản lý cơ sở kiểm tra và lập Phiếu xuất kho. | `sales_outbound.YeuCauXuatHang`, `ChiTietYeuCauXuatHang` |
| **Thông báo & Cảnh báo (`ThongBao`)** | Mục C.II của DOCX và `UC-5.13` yêu cầu chuông thông báo trên thanh công cụ lưu lịch sử thông báo nghiệp vụ (duyệt/trả phiếu nhập, hoàn tất xuất kho, điều chuyển, kiểm kê, cảnh báo sắp hết hàng). | `notifications.ThongBao` |

---

### 2.2 Phân tích Chi tiết Từng Bảng trong DOCX và Cải tiến Schema

#### 1. Bảng `SanPham` (Bảng 55) & `BienThe`
- **Vấn đề trong DOCX**:
  - Chứa cột `stt` (IntegerField, Not Null): Chỉ là số thứ tự hiển thị trên giao diện, lưu cứng trong DB sẽ gây lỗi khi thêm/xóa/lọc.
  - Chứa `mau_sac` và `kich_co` trực tiếp trong `SanPham`: Khiến mỗi màu/size phải tạo lại thông tin sản phẩm cha.
  - Thiếu cột `trang_thai` kinh doanh (`Đang kinh doanh` / `Ngừng kinh doanh`) được mô tả trong `UC-3` và Mục VI.1.
- **Chuẩn hóa trong Django**:
  - Bảng `SanPham`: Giữ `id`, `ma_san_pham` (Unique), `ten_hang_hoa`, `nhom_hang`, `don_vi_tinh`, `don_gia_niem_yet`, `hinh_anh`, `ghi_chu`, `trang_thai` (`ACTIVE`/`DISCONTINUED`). Loại bỏ cột `stt` lưu cứng (sử dụng `forloop.counter` hoặc đánh số phân trang trên giao diện).
  - Bảng `BienThe`: `id`, `san_pham` (FK → `SanPham`), `ma_sku` (Unique), `mau_sac`, `kich_co`, `don_gia` (Decimal), `trang_thai`, kèm ràng buộc `UNIQUE(san_pham, mau_sac, kich_co)`.

#### 2. Bảng `PhieuNhapKho` (Bảng 57) & `ChiTietPhieuNhapKho` (Bảng 58)
- **Vấn đề trong DOCX**:
  - `PhieuNhapKho` thiếu khóa ngoại `co_so_nhan` (nhập vào kho nào — mặc định CS1 Kho tổng).
  - Thiếu `trang_thai` (`DRAFT`, `PENDING_APPROVAL`, `RETURNED`, `APPROVED`), `nguoi_tao`, `nguoi_duyet`, `thoi_gian_duyet`, `ly_do_tra_lai` dù `UC-4.7`, `UC-4.8`, `UC-4.9` bắt buộc kiểm tra trạng thái duyệt và lý do trả phiếu.
  - `ChiTietPhieuNhapKho.id_san_pham` trỏ vào `SanPham` thay vì `BienThe` (SKU).
  - `chiet_khau` ghi *"theo % hoặc theo số tiền"* gây nhập nhằng công thức `thanh_tien = so_luong * don_gia - chiet_khau`.
- **Chuẩn hóa trong Django**:
  - Bổ sung `co_so_nhan` (FK → `CoSo`), `trang_thai`, `nguoi_tao`, `nguoi_duyet`, `thoi_gian_duyet`, `ly_do_tra_lai`, `ghi_chu` vào `PhieuNhapKho`.
  - Liên kết `ChiTietPhieuNhapKho` với `BienThe` (FK `PROTECT`). Chuẩn hóa `chiet_khau` là số tiền VNĐ cố định trên dòng (`0 <= chiet_khau <= so_luong * don_gia`).

#### 3. Bảng `PhieuXuatHangBan` (Bảng 59) & `ChiTietPhieuXuatHangBan` (Bảng 60)
- **Vấn đề trong DOCX**:
  - Phần diễn giải của Bảng 59 ghi nhầm `id_co_so` là *"chi nhánh tiếp nhận hàng hóa xuất kho"* và `sdt`/`dia_chi` là *"chi nhánh nhận hàng"* (nhầm với phiếu điều chuyển).
  - Thiếu `trang_thai` (`PENDING`, `COMPLETED`, `CANCELLED`), `nguoi_tao`, `nguoi_ghi_nhan`, `thoi_gian_ghi_nhan` để phục vụ `UC-5.5`, `UC-5.6`, `UC-5.7`, `UC-5.12`.
  - `ChiTietPhieuXuatHangBan` trỏ tới `SanPham` thay vì `BienThe`.
- **Chuẩn hóa trong Django**:
  - `PhieuXuatHangBan.co_so` là **Cơ sở xuất bán** (FK → `CoSo`). `ten_khach_hang`, `sdt`, `dia_chi`, `phuong_thuc_giao` (`COUNTER`/`DELIVERY`) lưu thông tin giao nhận đơn hàng bán.
  - Bổ sung `trang_thai`, `nguoi_tao`, `nguoi_ghi_nhan`, `thoi_gian_ghi_nhan`, `yeu_cau_xuat` (FK nullable → `YeuCauXuatHang`).
  - `ChiTietPhieuXuatHangBan` tham chiếu `BienThe` (FK `PROTECT`).

#### 4. Bảng `PhieuDieuChuyen` (Bảng 61) & `ChiTietPhieuDieuChuyen` (Bảng 62)
- **Vấn đề trong DOCX**:
  - Trên Hình 14 (Sơ đồ quan hệ), `PhieuDieuChuyen` có thêm `ngay_nhan` và `dia_chi` nhưng Bảng 61 lại thiếu; cả hai đều thiếu `trang_thai`, `ly_do`, `nguoi_yeu_cau`, `nguoi_xuat`, `nguoi_nhan`.
  - `ChiTietPhieuDieuChuyen` chỉ có một cột `so_luong`, không thể lưu đồng thời số lượng yêu cầu, số lượng thực xuất từ cơ sở gửi và số lượng thực nhận tại cơ sở nhận khi xảy ra thiếu hàng (Scenario 5).
- **Chuẩn hóa trong Django**:
  - `PhieuDieuChuyen`: Có `co_so_xuat`, `co_so_nhan` (`CheckConstraint: co_so_xuat != co_so_nhan`), `trang_thai` (`REQUESTED`, `ACCEPTED`, `REJECTED`, `DISPATCHED`, `RECEIVED`, `RECEIVED_WITH_SHORTAGE`, `CANCELLED`), `ly_do`, `ghi_chu_chenh_lech`, timestamps và user FKs cho từng bước.
  - `ChiTietPhieuDieuChuyen`: Lưu `bien_the`, `so_luong_yeu_cau`, `so_luong_xuat`, `so_luong_nhan`, `ghi_chu`.

#### 5. Bảng `KiemKe` (Bảng 64) & `ChiTietKiemKe` (Bảng 65)
- **Vấn đề trong DOCX**:
  - `KiemKe` có `tao_boi_id`, `duyet_boi_id`, `tu_choi_boi_id` kiểu `IntegerField` rời rạc, thiếu `nguoi_kiem_ke` (nhân viên thực đếm tại kho theo `UC-1.6`).
  - `ChiTietKiemKe` có lỗi chính tả tên cột `don_vi_tinh_` và kiểu `Demical`, thiếu cột `trang_thai_doi_chieu` (`MATCH`/`SHORTAGE`/`EXCESS`), và diễn giải cột `ghi_chu` bị copy nhầm từ phiếu điều chuyển.
- **Chuẩn hóa trong Django**:
  - Chuyển `tao_boi`, `duyet_boi`, `tu_choi_boi` thành `ForeignKey(User, on_delete=PROTECT)`. Thêm `nguoi_kiem_ke` và `ghi_chu`.
  - `ChiTietKiemKe` tham chiếu `BienThe`, lưu `so_luong_he_thong`, `so_luong_thuc_te` (`>= 0`), `chenh_lech = so_luong_thuc_te - so_luong_he_thong`, `trang_thai_doi_chieu` (`MATCH`, `SHORTAGE`, `EXCESS`), `don_vi_tinh`, `don_gia` (`DecimalField`), `xu_ly`, `ghi_chu`.

#### 6. Bảng `BaoCao` (Bảng 66)
- **Vấn đề trong DOCX**:
  - Bảng `BaoCao` chỉ gắn với 1 `id_san_pham` mà thiếu `co_so` (báo cáo của cơ sở nào hay toàn hệ thống) và thiếu khoảng thời gian (`tu_ngay`, `den_ngay`).
- **Chuẩn hóa trong Django**:
  - Tính toán báo cáo động trực tiếp từ `StockMovement` để luôn chính xác theo thời gian thực; đồng thời hỗ trợ lưu bản chụp (`BaoCao`) có đầy đủ `co_so`, `tu_ngay`, `den_ngay`, `bien_the`, `ton_dau_ky`, `nhap_kho`, `xuat_kho`, `ton_cuoi_ky`, `gia_von`, `gia_tri_ton_kho`.
