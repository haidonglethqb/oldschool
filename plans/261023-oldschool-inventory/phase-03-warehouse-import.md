# Phase 03: Warehouse Import (`Nhập kho`)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Description**: Implement `NhaCungCap`, `PhieuNhapKho`, `ChiTietPhieuNhapKho`, manual & Excel import preview (`UC-4.1`, `UC-4.2`), list/detail/search/filter/edit/delete (`UC-4.3`–`UC-4.8`), Admin approval/return (`UC-4.9`) with atomic stock posting, and import reports (`UC-4.10`, `UC-4.11`).

## Related Code Files
- `apps/purchasing/models.py`, `apps/purchasing/forms.py`, `apps/purchasing/services.py`, `apps/purchasing/selectors.py`, `apps/purchasing/views.py`, `apps/purchasing/urls.py`
- `templates/purchasing/receipt_list.html`, `templates/purchasing/receipt_detail.html`, `templates/purchasing/receipt_form.html`, `templates/purchasing/excel_preview.html`, `templates/purchasing/import_report.html`

## Todo List
- [ ] Implement `NhaCungCap`, `PhieuNhapKho`, `ChiTietPhieuNhapKho` models
- [ ] Implement manual receipt creation/update/deletion for CS1 Manager
- [ ] Implement Excel `.xlsx` upload & preview with row-level error validation (`UC-4.1`)
- [ ] Implement Admin approval (atomic stock increase) and return with reason (`UC-4.9`)
- [ ] Implement Import Activity Report & Excel export (`UC-4.10`, `UC-4.11`)
