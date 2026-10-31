# Ma trận Phân quyền RBAC & Cơ chế Cô lập Dữ liệu theo Cơ sở (`PERMISSIONS.md`)

Hệ thống **Old School** thực thi kiểm soát truy cập dựa trên vai trò (**RBAC**) kết hợp với cô lập phạm vi dữ liệu theo cơ sở (**Branch Isolation**) tại cả tầng View (`@role_required`, `get_effective_branch`) và tầng Service (`assert_roles`, `assert_branch_access`, `assert_can_manage_imports`).

---

## 1. Ba vai trò nghiệp vụ chuẩn

1. **`ADMIN` — Chủ cửa hàng (Owner / Administrator)**:
   - Không bị khóa cứng vào một cơ sở đơn lẻ (`branch = NULL`).
   - Có thể chuyển đổi linh hoạt giữa chế độ xem **Tất cả cơ sở (Toàn chuỗi)** hoặc từng cơ sở (`CS1`, `CS2`, `CS3`) ngay trên thanh điều hướng.
   - Tạo Phiếu xuất bán trực tiếp và xem/xử lý yêu cầu từ Nhân viên theo phạm vi đã chọn; không tạo Yêu cầu xuất từ quầy.
   - Là vai trò **duy nhất** có quyền:
     - Phê duyệt hoặc trả lại Phiếu nhập kho (`UC-4.9` — `DEC-01`).
     - Phê duyệt hoặc từ chối Biên bản kiểm kê (`UC-6.10` — `DEC-02`).

2. **`MANAGER` — Quản lý cơ sở (`CS1`, `CS2`, `CS3`)**:
   - Bắt buộc gắn chặt với 1 cơ sở (`user.branch`).
   - Mọi thao tác truy vấn và cập nhật đều bị khóa trong phạm vi `user.branch` (mọi nỗ lực truyền `?branch=` hoặc `POST` sang cơ sở khác đều bị từ chối với mã `403 PermissionDenied`).
   - **Quản lý CS1 (Kho tổng)**: Được quyền lập/sửa/xóa Phiếu nhập kho chưa duyệt và thêm Nhà cung cấp (`UC-4.1`–`UC-4.8`, `UC-4.11`).
   - **Quản lý CS2 / CS3**: Không được truy cập phân hệ Nhập kho từ NCC; thực hiện nhận hàng thông qua quy trình Điều chuyển nội bộ từ Kho tổng (`UC-5.3`).
   - Tạo Phiếu xuất bán trực tiếp và xem/xử lý yêu cầu từ Nhân viên tại cơ sở của mình; không tạo Yêu cầu xuất từ quầy.

3. **`STAFF` — Nhân viên bán hàng (`CS1`, `CS2`, `CS3`)**:
   - Bắt buộc gắn chặt với 1 cơ sở (`user.branch`).
   - Được phép tra cứu Danh mục hàng hóa & tồn kho cơ sở (`UC-3`, `UC-5.1`).
   - **Tạo & Ghi nhận Phiếu xuất bán trực tiếp tại quầy**: Nhân viên được phép lập phiếu xuất bán và chốt xuất kho trừ tồn ngay tại cơ sở để phục vụ khách mua lẻ mà không cần quản lý phê duyệt (`UC-5.2`–`UC-5.11`).
   - **Tạo Yêu cầu xuất hàng bán nội bộ**: Khi ngoài kệ/quầy hết hàng, nhân viên lập yêu cầu xuất bổ sung từ kho ra quầy (chỉ gồm Lý do xuất và mặt hàng, không có thông tin khách hàng) gửi Quản lý phê duyệt.
   - Được xem danh sách/chi tiết và in phiếu xuất đã hoàn tất (`UC-5.12`).
   - Bị chặn hoàn toàn khỏi các màn hình: Nhập kho, Điều chuyển nội bộ, Kiểm kê kho, Báo cáo tổng hợp, Xóa phiếu xuất và Thêm/Sửa/Xóa sản phẩm.

---

## 2. Bảng Ma trận Phân quyền Chi tiết

| Phân hệ / Chức năng | Chủ (`ADMIN`) | Quản lý CS1 (`Kho tổng`) | Quản lý CS2 / CS3 | Nhân viên bán hàng (`STAFF`) |
|---|:---:|:---:|:---:|:---:|
| Đăng nhập / Đăng xuất (`UC-1`, `UC-2`) | ✅ | ✅ | ✅ | ✅ |
| Chuyển đổi phạm vi xem cơ sở trên Header | ✅ (Toàn chuỗi) | ❌ (Khóa CS1) | ❌ (Khóa CS2/CS3) | ❌ (Khóa cơ sở) |
| Tra cứu Danh mục & Tồn kho (`UC-3.1`, `UC-3.6`, `UC-3.7`, `UC-5.1`) | ✅ | ✅ | ✅ | ✅ |
| Thêm / Sửa / Xóa / Ngừng KD Sản phẩm (`UC-3.3`–`UC-3.5`) | ✅ | ✅ | ✅ | ❌ (`403`) |
| Lập / Sửa / Xóa Phiếu nhập kho chưa duyệt (`UC-4.1`–`UC-4.8`) | ✅ | ✅ | ❌ (`403`) | ❌ (`403`) |
| Thêm Nhà cung cấp mới (`UC-4.11`) | ✅ | ✅ | ❌ (`403`) | ❌ (`403`) |
| **Phê duyệt / Trả lại Phiếu nhập kho (`UC-4.9`)** | ✅ (**Duy nhất**) | ❌ (`403`) | ❌ (`403`) | ❌ (`403`) |
| Tạo Yêu cầu xuất hàng bán nội bộ | ❌ (`403`) | ❌ (`403`) | ❌ (`403`) | ✅ (Tại cơ sở) |
| Xem Yêu cầu xuất hàng bán | ✅ (Toàn chuỗi / Cơ sở) | ✅ (Chỉ CS1) | ✅ (Chỉ CS2/CS3) | ✅ (Tại cơ sở) |
| Lập Phiếu xuất từ yêu cầu / Từ chối yêu cầu | ✅ | ✅ (Chỉ CS1) | ✅ (Chỉ CS2/CS3) | ❌ (`403`) |
| Lập / Sửa / Ghi nhận Phiếu xuất bán (`UC-5.2`–`UC-5.11`) | ✅ | ✅ (Tại CS1) | ✅ (Tại CS2/CS3) | ✅ (Tại cơ sở) |
| Xóa Phiếu xuất hàng bán chưa chốt (`UC-5.7`) | ✅ | ✅ (Tại CS1) | ✅ (Tại CS2/CS3) | ❌ (`403`) |
| Xem & In Phiếu xuất hàng bán đã hoàn tất (`UC-5.12`) | ✅ | ✅ (Tại CS1) | ✅ (Tại CS2/CS3) | ✅ (Tại cơ sở) |
| Tạo / Xuất / Nhận Phiếu điều chuyển nội bộ (`UC-5.3`) | ✅ | ✅ (Liên quan CS1) | ✅ (Liên quan CS2/CS3) | ❌ (`403`) |
| Lập / Sửa / Xóa Biên bản kiểm kê chưa duyệt (`UC-6.1`–`UC-6.9`) | ✅ | ✅ (Tại CS1) | ✅ (Tại CS2/CS3) | ❌ (`403`) |
| **Phê duyệt / Từ chối Biên bản kiểm kê (`UC-6.10`)** | ✅ (**Duy nhất**) | ❌ (`403`) | ❌ (`403`) | ❌ (`403`) |
| Xem Báo cáo & Xuất Excel (`UC-7.1`–`UC-7.5`) | ✅ (Toàn chuỗi / Cơ sở) | ✅ (Chỉ CS1) | ✅ (Chỉ CS2/CS3) | ❌ (`403`) |

## 3. Quy trình Xuất bán & Yêu cầu xuất kho — cập nhật 31/10/2026

- **Xuất bán trực tiếp**: Nhân viên (`STAFF`) được quyền lập phiếu xuất bán và chốt xuất kho ngay tại quầy (`save_and_finalize`) để bán hàng cho khách mà không cần chờ duyệt, chỉ trong phạm vi cơ sở mình làm việc. Thao tác xóa phiếu xuất vẫn dành riêng cho Quản lý / Admin.
- **Yêu cầu xuất hàng bán nội bộ**: Dùng khi quầy/kệ hết hàng cần vào kho lấy bổ sung. Form yêu cầu của Nhân viên chỉ gồm **Lý do xuất kho** và **Mặt hàng cần xuất**, không yêu cầu thông tin khách hàng. Quản lý nhận thông báo và phê duyệt lập phiếu xuất kho. Tài khoản `ADMIN`/`MANAGER` bị chặn tạo tại cả HTTP POST và service; mở danh sách để duyệt hoặc từ chối.
