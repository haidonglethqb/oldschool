# Phase 06: Inventory Counting (`Kiểm kê kho`)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Description**: Implement `KiemKe` and `ChiTietKiemKe` (`UC-1.6`, `UC-6.1`–`UC-6.10`), system stock snapshot on count creation, manual & Excel count import (`UC-6.3`), automatic difference (`so_luong_thuc_te - so_luong_he_thong`) and status (`MATCH`, `SHORTAGE`, `EXCESS`), summary counters, and `ADMIN` approval/rejection without silently overwriting physical stock.

## Related Code Files
- `apps/stocktakes/models.py`, `apps/stocktakes/forms.py`, `apps/stocktakes/services.py`, `apps/stocktakes/selectors.py`, `apps/stocktakes/views.py`, `apps/stocktakes/urls.py`
- `templates/stocktakes/stocktake_list.html`, `templates/stocktakes/stocktake_detail.html`, `templates/stocktakes/stocktake_form.html`, `templates/stocktakes/excel_preview.html`

## Todo List
- [ ] Implement `KiemKe` and `ChiTietKiemKe` models
- [ ] Implement manual & Excel stocktake creation/update (`UC-6.3`–`UC-6.6`)
- [ ] Implement search, filter, and deletion for eligible pending/rejected records (`UC-6.1`, `UC-6.2`, `UC-6.7`–`UC-6.9`)
- [ ] Implement `ADMIN` approval and rejection (`UC-6.10`) preserving stock snapshot integrity
