# Phase 02: Master Data & Inventory Core

## Overview
- **Priority**: P1
- **Status**: Pending
- **Description**: Implement `SanPham` (Product), `BienThe` (Variant SKU), `TonKho` (Branch × Variant stock balance), `StockMovement` (Immutable ledger), centralized `InventoryService` with `select_for_update()` locking, reusable Excel parser/exporter (`excel.py`), and Product Catalogue UI (`UC-3`, `UC-3.1`–`UC-3.7`, `UC-5.1`).

## Related Code Files
- `apps/catalog/models.py`, `apps/catalog/forms.py`, `apps/catalog/services.py`, `apps/catalog/selectors.py`, `apps/catalog/views.py`, `apps/catalog/urls.py`
- `apps/inventory/models.py`, `apps/inventory/services.py`, `apps/inventory/selectors.py`, `apps/inventory/excel.py`
- `templates/catalog/product_list.html`, `templates/catalog/product_detail.html`, `templates/catalog/product_form.html`

## Todo List
- [ ] Implement `SanPham` and `BienThe` models with SKU and `(san_pham, mau_sac, kich_co)` uniqueness
- [ ] Implement `TonKho` and `StockMovement` models with DB constraints
- [ ] Implement `InventoryService` with atomic locking and idempotency keys
- [ ] Implement `excel.py` reusable `.xlsx` preview/import/export utility
- [ ] Implement Catalogue CRUD, variant management, stock status badges, search/filter (`UC-3.1`–`UC-3.7`)
