# Quy trình Nghiệp vụ & Cơ chế Hạch toán Sổ cái Tồn kho (`STOCK_WORKFLOWS.md`)

Mọi biến động số lượng tồn kho (`TonKho.so_luong`) trong hệ thống **Old School** đều bắt buộc đi qua dịch vụ trung tâm [`apply_stock_movements`](../apps/inventory/services.py) trong một giao dịch nguyên tử (`@transaction.atomic`) sử dụng khóa dòng bi quan (`select_for_update()`) theo thứ tự tăng dần của `bien_the_id`.

---

## 1. Quy trình Nhập kho tại Kho tổng CS1 (`UC-4.1` – `UC-4.11`)

```mermaid
stateDiagram-v2
    [*] --> DRAFT: Lưu nháp (Không đổi tồn)
    [*] --> PENDING_APPROVAL: Gửi chờ duyệt (Không đổi tồn)
    DRAFT --> PENDING_APPROVAL: Gửi duyệt
    PENDING_APPROVAL --> RETURNED: Admin trả lại chỉnh sửa (Không đổi tồn)
    RETURNED --> PENDING_APPROVAL: Quản lý CS1 cập nhật & gửi lại
    PENDING_APPROVAL --> APPROVED: Admin phê duyệt (UC-4.9 -> Cộng tồn CS1 + Ghi sổ cái IMPORT_IN)
```
- **Điểm kiểm soát quan trọng (`DEC-01`)**: Khi Quản lý CS1 tạo hoặc sửa phiếu nhập, tồn kho hoàn toàn chưa thay đổi. Chỉ khi `ADMIN` bấm **Duyệt phiếu nhập**, hệ thống mới khóa dòng `TonKho` của CS1, cộng số lượng nhập, tạo bút toán `StockMovement(movement_type="IMPORT_IN")` và tự động đóng các cảnh báo sắp hết hàng nếu tồn mới vượt định mức tối thiểu.

---

## 2. Quy trình Xuất kho bán hàng (`UC-5.1`, `UC-5.2`, `UC-5.4` – `UC-5.13`)

```mermaid
stateDiagram-v2
    [*] --> YeuCau_PENDING: Nhân viên bán hàng gửi yêu cầu xuất
    YeuCau_PENDING --> PhieuXuat_PENDING: Quản lý lập Phiếu xuất hàng bán (Chưa trừ tồn)
    YeuCau_PENDING --> YeuCau_REJECTED: Quản lý từ chối (Thiếu tồn kho)
    PhieuXuat_PENDING --> PhieuXuat_COMPLETED: Quản lý Ghi nhận xuất kho (UC-5.11 -> Khóa dòng, kiểm tra tồn, trừ kho + Ghi sổ cái SALE_OUT)
```
- **Kiểm soát tương tranh & Chống âm kho**: Khi bấm **Ghi nhận xuất kho** (`finalize_outbound_receipt`), hệ thống khóa `TonKho` bằng `select_for_update()`. Nếu `so_luong_hien_tai < so_luong_xuat`, toàn bộ giao dịch bị hủy (`InsufficientStockError`), tuyệt đối không cho phép tồn kho âm.
- **Cảnh báo tồn kho tự động (`UC-5.13`)**: Ngay sau khi trừ tồn, `sync_low_stock_alert` kiểm tra nếu `so_luong <= muc_ton_toi_thieu` sẽ sinh (hoặc cập nhật tại chỗ không trùng lặp) thông báo `LOW_STOCK_ALERT`.

---

## 3. Quy trình Điều chuyển Nội bộ 2 bước (`UC-5.3`)

```mermaid
stateDiagram-v2
    [*] --> REQUESTED: Cơ sở nhận tạo yêu cầu điều chuyển (Không đổi tồn)
    REQUESTED --> ACCEPTED: Cơ sở xuất chấp nhận (Không đổi tồn)
    REQUESTED --> REJECTED: Cơ sở xuất từ chối (Không đổi tồn)
    REQUESTED --> DISPATCHED: Cơ sở xuất xác nhận Xuất điều chuyển (Bước 1: Trừ tồn Cơ sở xuất - TRANSFER_OUT)
    ACCEPTED --> DISPATCHED: Cơ sở xuất xác nhận Xuất điều chuyển (Bước 1: Trừ tồn Cơ sở xuất - TRANSFER_OUT)
    DISPATCHED --> RECEIVED: Cơ sở nhận xác nhận Đã nhận đủ (Bước 2: Cộng tồn Cơ sở nhận - TRANSFER_IN)
    DISPATCHED --> RECEIVED_WITH_SHORTAGE: Thực nhận < Thực xuất (Bước 2: Cộng theo SL thực nhận + Ghi chú chênh lệch)
```
- **Hạch toán 2 bước chuẩn xác**:
  1. Khi cơ sở xuất bấm **Xuất điều chuyển** (`DISPATCHED`), hàng rời kho xuất nên tồn kho cơ sở xuất giảm ngay (`TRANSFER_OUT`), nhưng tồn kho cơ sở nhận **chưa tăng** (lượng hàng này được Báo cáo ghi nhận vào cột **Đang vận chuyển / In-Transit**).
  2. Chỉ khi cơ sở nhận bấm **Xác nhận Đã nhận hàng** (`RECEIVED` / `RECEIVED_WITH_SHORTAGE`), tồn kho cơ sở nhận mới tăng theo `so_luong_nhan` (`TRANSFER_IN`).

---

## 4. Quy trình Kiểm kê kho (`UC-6.1` – `UC-6.10`)

```mermaid
stateDiagram-v2
    [*] --> PENDING: Quản lý cơ sở lập biên bản kiểm kê (Chụp snapshot so_luong_he_thong)
    PENDING --> REJECTED: Admin từ chối & yêu cầu kiểm đếm lại
    REJECTED --> PENDING: Quản lý cập nhật & gửi duyệt lại
    PENDING --> APPROVED: Admin phê duyệt (UC-6.10 -> Xác nhận biên bản, giữ nguyên TonKho vật lý theo DEC-03)
```
