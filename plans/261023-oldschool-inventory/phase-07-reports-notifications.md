# Phase 07: Reports & Notifications (`Báo cáo & Cảnh báo`)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Description**: Implement `BaoCao` and dynamic reporting from `StockMovement` (`UC-1.7`, `UC-7.1`–`UC-7.5`), Chart.js visual analytics, Excel export (`UC-7.3`), `ThongBao` notifications, and automatic low-stock alert lifecycle (`UC-5.13`).

## Related Code Files
- `apps/reports/models.py`, `apps/reports/selectors.py`, `apps/reports/services.py`, `apps/reports/views.py`, `apps/reports/urls.py`
- `apps/notifications/models.py`, `apps/notifications/services.py`, `apps/notifications/views.py`, `apps/notifications/urls.py`
- `templates/reports/dashboard.html`, `templates/notifications/notification_list.html`

## Todo List
- [ ] Implement `ThongBao` model, notification dropdown, and deduplicated low-stock warning engine (`UC-5.13`)
- [ ] Implement `BaoCao` and `ReportSelector` reconciling `ton_dau_ky + nhap_kho - xuat_kho = ton_cuoi_ky`
- [ ] Separate customer sales (`SALES_OUTBOUND`) from transfers (`TRANSFER_OUT`/`TRANSFER_IN`) and track in-transit stock
- [ ] Implement Chart.js dashboards (best-selling, slow-moving, low-stock) and `.xlsx` export (`UC-7.1`–`UC-7.5`)
