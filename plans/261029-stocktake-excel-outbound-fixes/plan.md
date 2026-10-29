---
title: "Sửa kiểm kê, đọc Excel mẫu và quyền yêu cầu xuất từ quầy"
description: "Khắc phục nút trống, tách tồn hệ thống, đồng bộ Excel mẫu với bộ đọc và giới hạn tạo yêu cầu từ quầy cho Nhân viên."
status: completed
priority: P1
effort: 6h
branch: main
tags: [bugfix, frontend, backend, auth]
created: 2026-10-29
---

# Kế hoạch sửa kiểm kê và xuất bán

## Phạm vi và trạng thái

Đã triển khai Excel, UI kiểm kê và phân quyền; suite mục tiêu 37 passed (19 test mới), QA Edge 46/46 đạt, `manage.py check` 0 vấn đề. Toàn suite: 54 passed, 1 skipped (115.16s); bỏ qua kiểm thử khóa đồng thời cần PostgreSQL khi chạy SQLite.

| Mục | Kết luận kiểm tra | Kết quả cần đạt |
|---|---|---|
| Nút nâu trống ở kiểm kê | Template lồng một nút submit ngoài các nút theo vai trò | Đã sửa: một nút lưu có nhãn và biểu tượng đúng vai trò |
| Excel mẫu bị báo thiếu cột | Cả 3 parser lấy dòng 1; file tải từ web có tên cột tại dòng 4 | Đọc được file mẫu nhập, xuất, kiểm kê và file cũ có tên cột tại dòng 1 |
| Tồn hệ thống lẫn trong SKU | Cả ba nhánh render dòng đều ghép `[Hệ thống: ...]` vào option | Cột tồn hệ thống riêng, cập nhật theo SKU và cơ sở |
| Yêu cầu từ quầy ở Admin/Quản lý | Menu, shortcut, form và service hiện cho mọi vai trò tạo | Bỏ menu/shortcut và quyền tạo của Admin/Quản lý; Nhân viên vẫn tạo |

## Cách hiểu nghiệp vụ dùng để triển khai

- Admin và Quản lý CS1/CS2 tạo phiếu xuất bán trực tiếp; không tạo yêu cầu từ quầy.
- Giữ Nhân viên CS1/CS2 gửi yêu cầu. Admin/Quản lý vẫn đọc và xử lý yêu cầu đã nhận qua danh sách xử lý, thẻ chờ xử lý hoặc thông báo; trang xử lý không có form tạo của họ.
- Quy tắc dựa vào vai trò, không hard-code CS1/CS2; tiếp tục cô lập dữ liệu từng cơ sở.
- Tồn hiển thị khi tạo/sửa là tồn hiện tại của cơ sở. Server tiếp tục chụp số tồn khi lưu theo service hiện hữu; cột giao diện chỉ đọc.
- Không đổi quy trình phê duyệt kiểm kê, thời điểm trừ tồn, mô hình dữ liệu hay xóa lịch sử yêu cầu.

## Các giai đoạn

| # | Giai đoạn | Trạng thái | Ước lượng | Chi tiết |
|---|---|---|---|---|
| 1 | Đồng bộ đọc Excel với file tải xuống | Completed | 2h | [phase-01](./phase-01-excel-roundtrip.md) |
| 2 | Sửa kiểm kê và giới hạn tạo yêu cầu từ quầy | Completed | 2.5h | [phase-02](./phase-02-stocktake-ui-and-request-roles.md) |
| 3 | Hồi quy, duyệt code và nghiệm thu theo vai trò | Completed | 1.5h | [phase-03](./phase-03-regression-and-acceptance.md) |

Phase 1 và 2 hoàn thành trước phase 3. Thêm test hồi quy cùng từng thay đổi; phase 3 chạy tích hợp và kiểm tra trình duyệt.

## Điều kiện thực hiện

- Workspace đang có nhiều thay đổi chưa commit; giữ nguyên thay đổi có sẵn, rà diff trước khi sửa từng tệp.
- Không có `docs/development-rules.md` và `docs/code-standards.md` tại thời điểm khảo sát. Theo cấu trúc Django service/selector và pytest đang dùng.
- Tests hiện kiểm tra tải file bằng HTTP status/type/size; test nhập Excel tự dựng tên cột tại dòng 1 nên chưa bắt lỗi tải xuống rồi tải lên.
- Không cần migration; bổ sung kiểm tra quyền cả HTTP và service, cập nhật ma trận quyền.

## Tiêu chí hoàn tất

- [x] Mẫu tải thật từ web được tải lại và hiển thị preview đúng ở cả 3 phân hệ.
- [x] Kiểm kê không còn nút trống; cột tồn riêng đúng ở dòng mặc định, dòng thêm, Excel và form trả về khi lỗi.
- [x] Admin/Quản lý không thấy menu/shortcut/form tạo yêu cầu và không thể POST hoặc gọi service tạo yêu cầu.
- [x] Nhân viên gửi yêu cầu; Quản lý xử lý đúng cơ sở; Admin xử lý theo phạm vi được chọn.
- [x] Kiểm thử mục tiêu, toàn bộ suite và QA trình duyệt được ghi bằng kết quả thực tế.

## Lệnh triển khai đã thực hiện

`/cook C:/Users/HaiChu/Documents/GitHub/oldschool/plans/261029-stocktake-excel-outbound-fixes/plan.md --auto`

## Điểm cần theo dõi

Luồng xử lý yêu cầu của Admin/Quản lý đã được giữ. Test mới tập trung tại `tests/test_stocktake_excel_request_regressions.py`. [Kết quả test](../../docs/TEST_RESULTS.md), [QA trình duyệt](./reports/browser-qa.md). Server QA đã dừng; runtime tạm còn do automatic approval review chặn dọn tệp (`blocked by policy`).
