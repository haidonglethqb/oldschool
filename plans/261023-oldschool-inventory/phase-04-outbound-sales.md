# Phase 04: Outbound Sales (`Xuất kho bán hàng`)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Description**: Implement Staff `YeuCauXuatHang` (Proposed workflow Fig. 5), `PhieuXuatHangBan`, `ChiTietPhieuXuatHangBan`, stock lookup (`UC-5.1`), Excel import (`UC-5.2`), create/edit/delete pending receipt (`UC-5.4`, `UC-5.5`, `UC-5.7`), atomic finalization with row-level locking (`UC-5.6`), search/filter (`UC-5.8`–`UC-5.11`), and print view (`UC-5.12`).

## Related Code Files
- `apps/sales_outbound/models.py`, `apps/sales_outbound/forms.py`, `apps/sales_outbound/services.py`, `apps/sales_outbound/selectors.py`, `apps/sales_outbound/views.py`, `apps/sales_outbound/urls.py`
- `templates/sales_outbound/receipt_list.html`, `templates/sales_outbound/receipt_detail.html`, `templates/sales_outbound/receipt_form.html`, `templates/sales_outbound/receipt_print.html`, `templates/sales_outbound/request_list.html`, `templates/sales_outbound/request_form.html`

## Todo List
- [ ] Implement `YeuCauXuatHang`, `PhieuXuatHangBan`, `ChiTietPhieuXuatHangBan` models
- [ ] Implement Staff outbound request creation & Manager conversion to receipt
- [ ] Implement Outbound receipt CRUD & Excel preview (`UC-5.2`, `UC-5.4`, `UC-5.5`, `UC-5.7`)
- [ ] Implement atomic `finalize_outbound_receipt` with `select_for_update()` (`UC-5.6`)
- [ ] Implement print-friendly HTML receipt view (`UC-5.12`)
