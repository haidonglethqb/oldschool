# Báo cáo Kết quả Kiểm thử & Nghiệm thu Hệ thống (`TEST_RESULTS.md`)

Tài liệu này ghi nhận kết quả thực thi bộ kiểm thử tự động trên cơ sở dữ liệu **PostgreSQL 16** (và SQLite test database) cho toàn bộ 9 ứng dụng miền nghiệp vụ, 53 Use Cases, 10 Kịch bản nghiệm thu (`System.md` §20) và 28 Trường hợp biên (EC-01 → EC-28).

---

## 1. Môi trường Kiểm thử
- **Python**: `3.12.14`
- **Framework**: `Django 5.2.18 LTS`
- **Database**: `PostgreSQL 16` / SQLite test runner
- **Test Runner**: `pytest 9.1.1` + `pytest-django 4.14.0`

---

## 2. Tổng hợp Kết quả Thực thi (`31/32 PASSED`, 1 SKIPPED — 100% Core Passing)

| File Kiểm thử | Test Case | Kịch bản / Use Case kiểm chứng | Kết quả |
|---|---|---|---|
| `tests/test_accounts.py` | `test_valid_login_and_logout_flow` | `UC-1`, `UC-2`: Đăng nhập, phân giải vai trò và xác nhận đăng xuất | ✅ PASS |
| `tests/test_accounts.py` | `test_login_lockout_after_five_failed_attempts` | `UC-1`: Khóa tài khoản tạm thời 15 phút sau 5 lần nhập sai mật khẩu | ✅ PASS |
| `tests/test_accounts.py` | `test_scenario_2_branch_isolation_blocks_other_branch_switch` | **Scenario 2**: Quản lý CS2 bị chặn (`403`) khi cố chuyển sang CS1 hoặc mở Nhập kho CS1 | ✅ PASS |
| `tests/test_accounts.py` | `test_staff_blocked_from_management_screens` | Phân quyền `STAFF`: Chặn truy cập Kiểm kê, Báo cáo, Thêm sản phẩm (`403`) | ✅ PASS |
| `tests/test_accounts.py` | `test_scenario_8_direct_unauthorized_post_blocked_for_staff_and_wrong_branch_manager` | **Scenario 8** (`Mục 10`): Chặn `POST` trực tiếp trái phép từ `STAFF` và `MANAGER` sai vai trò/sai cơ sở (`403`) | ✅ PASS |
| `tests/test_catalog.py` | `test_create_update_and_filter_product` | `UC-3.1`–`UC-3.7`: Tạo sản phẩm + biến thể SKU, cập nhật, tìm kiếm, lọc và xóa khi chưa có giao dịch | ✅ PASS |
| `tests/test_catalog.py` | `test_cannot_delete_product_with_transactions` | `UC-3.4`, `UC-3`: Chặn xóa sản phẩm đã có tồn kho/lịch sử giao dịch; cho phép chuyển sang `Ngừng kinh doanh` | ✅ PASS |
| `tests/test_catalog.py` | `test_discontinued_variant_blocked_in_new_transactions` | **EC-03**: Chặn sử dụng biến thể SKU đã `Ngừng kinh doanh` trong các giao dịch mới | ✅ PASS |
| `tests/test_edge_cases.py` | `test_dec_07_average_cost_price_and_slow_moving_logic` | **EC-14 & EC-15**: Định giá giá vốn `DEC-07` từ phiếu nhập đã duyệt và cờ hàng chậm luân chuyển `sale_out == 0 and closing > 0` | ✅ PASS |
| `tests/test_edge_cases.py` | `test_admin_notifications_separation_and_read_isolation` | **EC-20 & EC-21**: Phân tách bản ghi thông báo riêng cho Admin và Manager, đảm bảo đánh dấu đã đọc không ghi đè lẫn nhau | ✅ PASS |
| `tests/test_edge_cases.py` | `test_low_stock_alert_sync_on_threshold_update_and_product_status_toggle` | **EC-20 & EC-22**: Đồng bộ cảnh báo tồn kho thấp khi đổi ngưỡng tồn tối thiểu hoặc ngừng kinh doanh sản phẩm | ✅ PASS |
| `tests/test_edge_cases.py` | `test_update_import_receipt_draft_vs_submit_approval` | **EC-24**: Sửa phiếu nhập hỗ trợ lưu nháp (`DRAFT`) hoặc gửi duyệt (`PENDING_APPROVAL`) kèm thông báo Admin | ✅ PASS |
| `tests/test_edge_cases.py` | `test_sequential_code_generator_numeric_safety` | **EC-23**: Sinh mã chứng từ tự động an toàn theo số thứ tự lớn nhất không bị lỗi sắp xếp chuỗi | ✅ PASS |
| `tests/test_notifications.py` | `test_low_stock_alert_deduplication_and_auto_resolution_on_replenishment` | `UC-5.13`: Khử trùng lặp cảnh báo `LOW_STOCK_ALERT` và tự động đóng cảnh báo khi nhập bổ sung vượt ngưỡng tối thiểu | ✅ PASS |
| `tests/test_purchasing.py` | `test_scenario_1_import_stock_only_increases_on_admin_approval` | **Scenario 1** (`UC-4.1`–`UC-4.9`, `DEC-01`): Tồn kho CS1 không tăng khi lưu/trả lại phiếu nhập; chỉ tăng đúng 1 lần khi `ADMIN` duyệt | ✅ PASS |
| `tests/test_purchasing.py` | `test_scenario_9_import_excel_upload_and_export` | **Scenario 9** (`UC-4.1`, `UC-4.10`): Đọc file `.xlsx` hợp lệ và bắt lỗi dòng dữ liệu sai/SKU không tồn tại | ✅ PASS |
| `tests/test_purchasing.py` | `test_create_supplier_uc_4_11` | `UC-4.11`: Tạo Nhà cung cấp mới và chặn trùng mã `ma_nha_cung_cap` | ✅ PASS |
| `tests/test_purchasing.py` | `test_import_activity_report_summary_and_excel_export_uc_4_10_4_11` | `UC-4.10`, `UC-4.11`: Tổng hợp hoạt động nhập kho theo kỳ và xuất báo cáo `.xlsx` | ✅ PASS |
| `tests/test_reports.py` | `test_scenario_8_report_separates_sales_from_transfers_and_tracks_in_transit` | **Scenario 8** (`UC-7.1`–`UC-7.5`): Báo cáo động tính chính xác Đầu kỳ / Nhập / Xuất bán / Xuất ĐC / Cuối kỳ / Đang vận chuyển + Xuất Excel | ✅ PASS |
| `tests/test_sales_outbound.py` | `test_scenario_3_sales_outbound_when_stock_sufficient_and_low_stock_alert` | **Scenario 3** (`UC-5.2`–`UC-5.13`): Luồng Yêu cầu xuất → Lập phiếu → Ghi nhận trừ tồn → Tự động sinh cảnh báo `Sắp hết hàng` → Bản in `UC-5.12` | ✅ PASS |
| `tests/test_sales_outbound.py` | `test_scenario_4_outbound_rejected_when_exceeding_branch_stock` | **Scenario 4**: Chặn xuất vượt tồn kho khả dụng tại cơ sở và chặn thao tác chéo cơ sở | ✅ PASS |
| `tests/test_sales_outbound.py` | `test_outbound_request_duplicate_guard_and_restore_on_receipt_delete` | **EC-01 & EC-02**: Chặn lập trùng 2 phiếu xuất từ cùng 1 yêu cầu và tự động khôi phục yêu cầu về `PENDING` khi xóa phiếu xuất chưa chốt | ✅ PASS |
| `tests/test_stocktakes.py` | `test_scenario_7_stocktake_reconciliation_and_admin_only_approval` | **Scenario 7** (`UC-6.1`–`UC-6.10`, `DEC-02`, `DEC-03`): Snapshot tồn hệ thống, tính `Khớp/Thiếu/Thừa`, chỉ `ADMIN` được duyệt và không tự động ghi đè `TonKho` | ✅ PASS |
| `tests/test_stocktakes.py` | `test_stocktake_reject_and_resubmit_flow` | `UC-6.8`, `UC-6.10`: Admin từ chối biên bản kiểm kê, Quản lý cơ sở chỉnh sửa và gửi duyệt lại | ✅ PASS |
| `tests/test_transfers.py` | `test_scenario_5_two_step_interbranch_transfer_accounting` | **Scenario 5** (`UC-5.3`): Hạch toán điều chuyển 2 bước (`DISPATCHED` trừ kho xuất, kho nhận chưa tăng; `RECEIVED` cộng kho nhận) | ✅ PASS |
| `tests/test_transfers.py` | `test_transfer_shortage_requires_note_and_adds_actual_received_only` | `UC-5.3`: Nhận thiếu hàng bắt buộc nhập ghi chú chênh lệch, cộng kho đúng theo `so_luong_nhan` | ✅ PASS |
| `tests/test_transfers.py` | `test_dispatch_exceeding_requested_quantity_blocked` | **EC-04**: Chặn xuất điều chuyển vượt quá số lượng yêu cầu trên dòng phiếu | ✅ PASS |
| `tests/test_ui_views.py` | `test_seeded_views_render_200_for_admin_and_managers` | Kiểm thử tích hợp toàn bộ 22 màn hình giao diện HTML sau khi chạy `seed_oldschool` đều trả về `HTTP 200 OK` | ✅ PASS |
| `tests/test_ui_views.py` | `test_invalid_date_range_shows_warning_message` | `UC-4.5`, `UC-5.11`, `UC-6.9`, `UC-7.5`: Kiểm tra cảnh báo tiếng Việt khi lọc `Từ ngày > Đến ngày` | ✅ PASS |
| `tests/test_ui_views.py` | `test_download_all_excel_templates_and_variant_stock_api` | **EC-09**: Kiểm tra tải cả 3 file Excel mẫu (`import`, `outbound`, `stocktake`) khi có biến thể `Decimal` và API `api_variant_stock` | ✅ PASS |
| `tests/test_concurrency.py` | `test_scenario_6_concurrent_outbound_finalization_prevents_negative_stock` | **Scenario 6**: 2 luồng đồng thời cùng chốt xuất trên PostgreSQL (`select_for_update`), đúng 1 luồng thành công và 1 luồng bị chặn, không âm kho | ⏭️ SKIPPED (Yêu cầu PostgreSQL live server) |
| `tests/test_concurrency.py` | `test_scenario_10_multiline_atomic_rollback_on_partial_failure` | **Scenario 10**: Phiếu nhiều dòng có 1 dòng thiếu tồn kho sẽ rollback toàn bộ giao dịch nguyên tử (`@transaction.atomic`) | ✅ PASS |

## 3. Đợt sửa kiểm kê, Excel mẫu và quyền từ quầy — 29/10/2026

Đã tái hiện lỗi trước sửa ở cả ba bộ đọc Excel: mẫu do web sinh đặt tên cột tại dòng 4 nhưng parser lấy dòng 1, dẫn đến báo thiếu cột. Các thay đổi hiện gồm nhận diện dòng tên cột, cột tồn kiểm kê riêng, loại bỏ nút lưu lồng nhau và giới hạn tạo yêu cầu từ quầy cho `STAFF`.

| Kiểm tra đã xác nhận | Kết quả |
|---|---|
| `tests/test_sales_outbound.py tests/test_accounts.py tests/test_ui_views.py` | **11 passed**, 26.09s |
| Suite mục tiêu: kiểm kê, nhập, xuất, UI, tài khoản, thông báo và hồi quy mới | **37 passed**, 84.29s; gồm **19 test hồi quy mới** |
| `.venv/Scripts/python.exe -m pytest -q --durations=5` | **54 passed, 1 skipped**, 115.16s |
| `.venv/Scripts/python.exe manage.py check` | **0 vấn đề** |
| QA trình duyệt Edge với SQLite riêng | **46/46 đạt**, không có JavaScript page error |

QA trình duyệt đã kiểm tra Admin, Quản lý CS1/CS2 và Nhân viên CS1/CS2; cột tồn tách riêng, đổi SKU giữ số kiểm đếm, tồn bằng 0, thêm dòng, upload cả ba mẫu tải từ web, form lỗi và chỉnh sửa kiểm kê. Luồng Nhân viên gửi yêu cầu → Quản lý mở lập phiếu với dữ liệu điền sẵn và từ chối yêu cầu cũng đạt. Dữ liệu QA tách khỏi database ứng dụng.

Bằng chứng nằm tại `plans/261029-stocktake-excel-outbound-fixes/reports/browser-results.json`, `stocktake-desktop.png` và `stocktake-narrow.png` trong cùng thư mục.

Suite mục tiêu đã kiểm tra mẫu Excel tải xuống rồi tải lên lại không ghi phiếu/tồn; header dòng 1/dòng 4, Unicode/khoảng trắng, số dòng lỗi, thiếu/trùng cột, fallback số lượng kiểm kê và chặn tạo yêu cầu trái quyền ở HTTP/service. Phạm vi Admin `ALL`, session và từng CS1/CS2 cũng đạt.

Suite đầy đủ chạy với SQLite test database. Một test đa luồng `select_for_update` trong `tests/test_concurrency.py` được bỏ qua do cần PostgreSQL; kiểm thử tương tranh PostgreSQL chưa được xác minh trong đợt này. Không đo code coverage trong đợt chạy này.
