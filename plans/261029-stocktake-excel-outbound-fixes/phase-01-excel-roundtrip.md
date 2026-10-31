# Phase 1 — Đọc được file Excel tải từ web

Trạng thái: Completed. Ưu tiên: P1. Ước lượng: 2h. Bối cảnh: [plan.md](./plan.md).

## Bằng chứng và nguyên nhân

- `apps/inventory/excel.py`: `parse_import_excel`, `parse_outbound_excel`, `parse_stocktake_excel` chuẩn hóa `raw_rows[0]` làm tên cột, lần lượt khoảng dòng 120, 226, 327.
- `build_excel_response` ghi banner tại dòng 1, hướng dẫn tại dòng 2, tên cột tại dòng 4, dữ liệu từ dòng 5.
- `download_excel_template_view` dùng builder này cho cả mẫu nhập, xuất và kiểm kê.
- Đã tái hiện: tạo workbook bằng builder rồi đưa vào parser tương ứng, cả 3 trả `valid=False` và `file_error` thiếu cột. Lỗi xảy ra trước bước truy vấn SKU.
- File trong `sample_data/excel/` có tên cột dòng 1. Không chỉ sửa các file mẫu tĩnh vì endpoint tải xuống tự tạo workbook khác.

## Yêu cầu

- Một cách tìm dòng tiêu đề dùng chung cho cả 3 parser; nhận file cũ dòng 1 và mẫu web dòng 4.
- Giữ nguyên hợp đồng kết quả `{valid, file_error, rows, errors}` và các kiểm tra nghiệp vụ từng parser.
- Báo đúng số dòng Excel thực tế; dữ liệu bắt đầu ở dòng 5 phải được báo dòng 5.
- Lỗi thiếu tên cột phải phân biệt với lỗi SKU, số lượng hoặc thiếu tồn. Bước đọc/preview không tạo phiếu và không đổi tồn.

## Tệp triển khai

| Hành động | Đường dẫn tuyệt đối | Nội dung |
|---|---|---|
| Modify | `C:/Users/HaiChu/Documents/GitHub/oldschool/apps/inventory/excel.py` | Helper nhận diện tên cột và dùng ở cả 3 parser |
| Create | `C:/Users/HaiChu/Documents/GitHub/oldschool/tests/test_stocktake_excel_request_regressions.py` | Test hồi quy tập trung cho round trip, parser, UI và phân quyền |

Không dự kiến sửa `apps/inventory/views.py` hoặc các file mẫu tĩnh: đọc để đối chiếu, chỉ sửa nếu test round trip chứng minh cần thiết.

## Các bước

1. Thêm test tái hiện tải mẫu qua `inventory:download_template`, lấy bytes response, điền SKU fixture và số lượng hợp lệ; POST file tới view tạo phiếu tương ứng với `form_action=upload_excel`. Không dùng workbook tự tạo làm bằng chứng duy nhất.
2. Tạo helper lấy tên cột và offset dữ liệu. Dò tối đa 20 dòng đầu của sheet active; chọn dòng đầu có đủ bộ tên cột bắt buộc của parser. Kiểm kê tiếp tục nhận `ma_sku` + `so_luong_thuc_te` hoặc fallback hiện hữu `ma_sku` + `so_luong`; nếu có cả hai cột số lượng, ưu tiên `so_luong_thuc_te`. Không coi banner hay dòng hướng dẫn là header.
3. Chuẩn hóa Unicode NFC, chữ thường, khoảng trắng đầu/cuối, khoảng trắng liên tiếp và NBSP trước khi ánh xạ alias hiện hữu. Giữ alias `Mã SKU`/`Mã hàng`, tên có dấu và tên kỹ thuật hiện có; không suy đoán cột chỉ theo vị trí.
4. Sau chuẩn hóa, từ chối tên cột bắt buộc trùng canonical (ví dụ cùng có `SKU` và `Mã hàng`); báo rõ cột nhập nhằng. Thiếu bộ bắt buộc trong vùng dò thì trả lỗi cấu trúc hiện có hoặc thông báo cụ thể hơn.
5. Dùng offset tìm được cho vòng lặp dữ liệu: bỏ preamble, giữ số dòng vật lý. Ví dụ header index 3 (dòng 4) thì dữ liệu index 4 được báo dòng 5.
6. Giữ validation SKU đang hoạt động, SKU trùng, đơn giá/chiết khấu, số lượng và tồn kho theo từng phân hệ. Không nhân dịp này đổi công thức giá hay quy tắc tồn.
7. Test file dòng 1, dòng 4, một số dòng trống/preamble, đổi thứ tự cột, Unicode/khoảng trắng, cột bắt buộc thiếu hoặc trùng, file trống/hỏng và dòng dữ liệu sai.

## Ma trận nghiệm thu

| Tình huống | Kỳ vọng |
|---|---|
| Mẫu nhập từ endpoint, SKU fixture và giá hợp lệ | Preview có đúng số lượng/đơn giá, không báo thiếu cột |
| Mẫu xuất, số lượng trong tồn fixture | Preview hợp lệ, không trừ tồn |
| Mẫu xuất, số lượng vượt tồn fixture | Lỗi thiếu tồn của dòng hàng, không phải thiếu cột |
| Mẫu kiểm kê, số thực tế 0 | Đọc hợp lệ; tồn hệ thống và chênh lệch đúng cơ sở |
| File mẫu cũ tên cột dòng 1 | Tiếp tục đọc được |
| Kiểm kê dùng alias `Số lượng`, hoặc có cả hai cột số lượng | Giữ fallback; ưu tiên `Số lượng thực tế` khi có cả hai |
| Dữ liệu sai tại dòng 5 | Thông báo chỉ đúng dòng 5 |
| Không có đủ cột hoặc canonical trùng | Từ chối rõ ràng, không ánh xạ nhầm |

## Rủi ro và bảo vệ

- Dò quá xa dễ nhầm dữ liệu thành header: giới hạn 20 dòng, đòi đủ bộ tên cột. Chưa hỗ trợ nhiều bảng hoặc tự chọn sheet khác.
- File mẫu xuất mặc định có số lượng 2 nhưng dữ liệu thật có thể hết tồn: test chủ động điền tồn fixture; thiếu tồn là lỗi nghiệp vụ hợp lệ.
- Giữ kiểm tra extension, kích thước, workbook hỏng và xuất chống formula injection đang có. Không nới quyền truy cập phân hệ nhập cho Quản lý CS2.

## Checklist

- [x] Tái hiện thủ công bằng builder → cả 3 parser trước sửa; không tuyên bố toàn bộ test mới đã chạy đỏ trên baseline.
- [x] Helper dùng chung và offset đúng ở cả 3 parser.
- [x] Round trip HTTP thực tế và các case cấu trúc/dữ liệu đạt.
- [x] Preview không tạo phiếu, dòng phiếu hoặc stock movement.

Tiếp theo: tích hợp cùng phase 2, chạy hồi quy và QA ở [phase 3](./phase-03-regression-and-acceptance.md).

## Kết quả xác minh

19 test mới được gom trong một tệp thay vì sửa rải rác các tệp test cũ. Suite mục tiêu 37 passed (84.29s); QA Edge tải mẫu → upload cả 3 phân hệ đạt. Xem [kết quả test](../../docs/TEST_RESULTS.md) và [QA trình duyệt](./reports/browser-qa.md).
