# Nhật ký Quyết định Thiết kế & Nghiệp vụ (`DECISIONS.md`)

Tài liệu này ghi nhận các điểm mâu thuẫn hoặc chưa được định nghĩa đầy đủ trong `50K22.3-Nhom09-ChuDe6-BCTD2.docx`, quy tắc xử lý bảo thủ được chọn theo thứ tự ưu tiên tại Mục 1 của `docs/System.md`, lý do và phạm vi ảnh hưởng.

---

### DEC-01: Thời điểm cập nhật tăng tồn kho khi Nhập kho (`UC-4` vs `UC-4.9`)
- **Mâu thuẫn trong tài liệu gốc**:
  - `UC-4` (Bảng 5 - Đặc tả tổng quát Nhập kho) ghi tại Bước 8–9: Quản lý cơ sở nhấn Lưu phiếu nhập → hệ thống cập nhật tăng tồn kho ngay.
  - Tuy nhiên, Quy trình nhập kho đề xuất (Hình 4, Bước 4–5) và `UC-4.9` (Bảng 24 - Phê duyệt phiếu nhập kho) quy định rõ: Quản lý CS1 tạo phiếu nhập ở trạng thái **Chờ phê duyệt**, Chủ (`ADMIN`) kiểm tra và chọn **Phê duyệt** thì hệ thống mới cập nhật số lượng hàng hóa vào tồn kho; nếu Chủ trả lại phiếu thì tồn kho không thay đổi.
- **Quyết định**: Áp dụng theo `UC-4.9` (Đặc tả chi tiết ưu tiên hơn mô tả tổng quát). Tồn kho chỉ tăng đúng 1 lần trong giao dịch atomic khi `ADMIN` phê duyệt phiếu nhập (`PENDING_APPROVAL → APPROVED`).
- **Trạng thái**: Đã chốt (Pending Business Confirmation nếu muốn cho phép tự động duyệt ở một số loại phiếu).

---

### DEC-02: Thẩm quyền phê duyệt Biên bản Kiểm kê (`Mục VI.4` vs `UC-1.6` & `UC-6.10`)
- **Mâu thuẫn trong tài liệu gốc**:
  - Mục VI.4 (trang 18) ghi Quản lý cơ sở có quyền duyệt, từ chối biên bản của cơ sở mình phụ trách.
  - Ngược lại, `UC-1.6` (Bảng 7, Bước 10) và `UC-6.10` (Bảng 49 - Phê duyệt kết quả kiểm kê) quy định Actor duy nhất thực hiện phê duyệt/từ chối biên bản kiểm kê là **Chủ (Admin)**.
- **Quyết định**: Áp dụng theo `UC-6.10` — chỉ vai trò `ADMIN` (Chủ) mới có quyền Phê duyệt (`APPROVED`) hoặc Từ chối (`REJECTED`) biên bản kiểm kê. Quản lý cơ sở (`MANAGER`) có quyền tạo, nhập Excel, cập nhật và xóa biên bản khi còn ở trạng thái `PENDING`.
- **Trạng thái**: Đã chốt theo `System.md` §7.5.

---

### DEC-03: Hành vi đối với Tồn kho vật lý khi Phê duyệt Biên bản Kiểm kê
- **Vấn đề trong tài liệu gốc**:
  - `UC-6.10` mô tả việc Chủ phê duyệt biên bản kiểm kê sẽ chuyển trạng thái biên bản từ `Chờ duyệt` sang `Đã duyệt` và lưu người duyệt/thời gian duyệt, nhưng **không** quy định việc tự động ghi đè số lượng tồn kho hiện tại (`TonKho`) bằng `so_luong_thuc_te`. Nếu tự động ghi đè trực tiếp bằng `so_luong_thuc_te` đã chụp từ trước khi có các giao dịch nhập/xuất mới sẽ làm sai lệch tồn kho hiện hành.
- **Quyết định**: Phê duyệt biên bản kiểm kê (`UC-6.10`) chỉ cập nhật trạng thái biên bản (`APPROVED`) và metadata phê duyệt, **không tự động ghi đè tồn kho vật lý**. Snapshot `so_luong_he_thong` và `chenh_lech` được bảo toàn phục vụ đối chiếu kiểm toán.
- **Trạng thái**: Đã chốt theo `System.md` §7.5.

---

### DEC-04: Tách biệt Nghiệp vụ Xuất kho Bán hàng và Xuất kho Điều chuyển Liên cơ sở
- **Mâu thuẫn trong tài liệu gốc**:
  - `UC-5.4` đến `UC-5.9` gộp mô tả "xuất bán hàng hoặc xuất điều chuyển" trong cùng một phiếu xuất, và Bảng 59 (`PhieuXuatHangBan`) ghi nhầm diễn giải cột `id_co_so` là "chi nhánh tiếp nhận". Trong khi đó, tài liệu lại thiết kế riêng Bảng 61 (`PhieuDieuChuyen`) và Bảng 62 (`ChiTietPhieuDieuChuyen`) cùng quy trình BPMN riêng (Hình 6) cho điều chuyển liên cơ sở.
- **Quyết định**:
  - Tách riêng 2 module và 2 nhóm bảng:
    1. `sales_outbound` (`PhieuXuatHangBan` + `YeuCauXuatHang`): Phục vụ xuất bán hàng cho khách tại một cơ sở (`co_so`).
    2. `transfers` (`PhieuDieuChuyen`): Phục vụ điều chuyển nội bộ giữa `co_so_xuat` và `co_so_nhan` với vòng đời `REQUESTED → ACCEPTED → DISPATCHED → RECEIVED / RECEIVED_WITH_SHORTAGE`.
  - Trên giao diện mục **XUẤT KHO**, cung cấp thanh điều hướng con (sub-navigation) rõ ràng giữa **Xuất bán hàng**, **Yêu cầu xuất bán (Nhân viên)** và **Điều chuyển liên cơ sở** để người dùng thao tác thuận tiện như một phân hệ thống nhất.
- **Trạng thái**: Đã chốt theo `System.md` §7.2–7.4 & §13.

---

### DEC-05: Quy tắc Chiết khấu trên Dòng Phiếu Nhập Kho (`ChiTietPhieuNhapKho.chiet_khau`)
- **Vấn đề trong tài liệu gốc**:
  - Bảng 58 ghi `chiet_khau` là *"theo % hoặc theo số tiền"*, nhưng công thức cột `thanh_tien` ngay bên dưới ghi cứng: `thanh_tien = so_luong × don_gia − chiet_khau`.
- **Quyết định**: Chuẩn hóa `chiet_khau` là **số tiền chiết khấu cố định (VNĐ)** trên dòng chi tiết (`0 <= chiet_khau <= so_luong * don_gia`), khớp tuyệt đối với công thức `thanh_tien = so_luong * don_gia - chiet_khau` trong Bảng 58.
- **Trạng thái**: Đã chốt theo `System.md` §7.1.

---

### DEC-06: Định nghĩa Ngưỡng Tồn kho Thấp (`UC-5.13`) & Trạng thái Tồn kho (`Mục 14`)
- **Vấn đề trong tài liệu gốc**:
  - Tài liệu yêu cầu 3 trạng thái: `Còn hàng` (xanh), `Sắp hết hàng` (vàng), `Hết hàng` (đỏ) và cảnh báo khi số lượng tồn thấp hơn/chạm ngưỡng tối thiểu.
- **Quyết định**:
  - Đánh giá trên từng cặp `(co_so, bien_the)` tại bảng `TonKho`:
    - `so_luong == 0` → **Hết hàng** (`OUT_OF_STOCK`)
    - `0 < so_luong <= muc_ton_toi_thieu` → **Sắp hết hàng** (`LOW_STOCK`)
    - `so_luong > muc_ton_toi_thieu` → **Còn hàng** (`IN_STOCK`)
  - Cảnh báo tồn kho thấp (`LOW_STOCK_ALERT`) được sinh khi `so_luong <= muc_ton_toi_thieu` (bao gồm cả sắp hết và hết hàng), chỉ giữ tối đa 1 cảnh báo chưa xử lý cho mỗi `(co_so, bien_the)` và tự động đánh dấu đã xử lý khi tồn kho tăng lên `> muc_ton_toi_thieu`.
- **Trạng thái**: Đã chốt theo `System.md` §6.6 & §14.

---

### DEC-07: Phương pháp Tính Giá vốn / Giá trị Tồn kho & Hàng tồn đọng trong Báo cáo (`UC-7.2`, `UC-7.3`)
- **Vấn đề trong tài liệu gốc**:
  - Bảng 66 (`BaoCao`) có cột `gia_von` và `gia_tri_ton_kho` nhưng tài liệu không quy định phương pháp kế toán giá vốn (FIFO, Bình quân gia quyền hay Giá nhập gần nhất).
  - `UC-7.2` nhắc tới "mặt hàng tồn đọng lâu ngày" nhưng không nêu công thức số ngày.
- **Quyết định**:
  - Không tự bịa thuật toán kế toán phức tạp: `gia_von` tham chiếu theo **đơn giá nhập bình quân từ các phiếu nhập đã duyệt** của biến thể đó (hoặc `0` nếu chưa có phiếu nhập), và ghi chú rõ trên giao diện báo cáo.
  - **Hàng chậm luân chuyển / tồn đọng (Slow-moving stock)**: Được xác định là các biến thể có tồn kho cuối kỳ `> 0` nhưng tổng số lượng xuất bán khách hàng (`SALES_OUTBOUND`) trong kỳ báo cáo bằng `0`.
  - **Quyền xuất Excel báo cáo (`UC-7.3`)**: Cho phép `MANAGER` xuất báo cáo Excel của cơ sở mình phụ trách (theo đúng `UC-7.3`) và cho phép `ADMIN` xuất báo cáo Excel toàn hệ thống hoặc từng cơ sở.
- **Trạng thái**: Đã chốt theo `System.md` §7.6 & §11.G.
