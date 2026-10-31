# Browser QA — 2026-10-29

- Environment: headless Microsoft Edge through Playwright; Django dev server 127.0.0.1:8765; separate SQLite QA database under state/qa-stocktake-20261029, seeded with demo data.
- Result: **46 checks passed, 0 failed; 0 JavaScript page errors.**
- Accounts: admin_owner (default CS1 for create), manager_cs1, manager_cs2, staff_cs1, staff_cs2.
- Verified Admin/Manager counter menu + shortcut hidden and creation form absent; STAFF menu, shortcut and form remain.
- Verified stocktake single named save button, separate stock column, default selected quantities, SKU changes update stock while preserving manual count, added blank row shows dash, choosing SKU updates dynamic row; CS2 zero-stock SKU displays 0.
- Downloaded templates through real endpoints and selected/uploaded them in browser: import, outbound and stocktake previews succeed. Stocktake preview has 3 rows with correct stock cells.
- Duplicate-SKU submit causes stocktake validation rerender with rows and stock cells preserved. Pending edit displays current selected branch stock.
- STAFF CS1 creates request; Manager CS1 sees it, opens conversion page with customer prefilled, returns and rejects successfully.
- Screenshots: stocktake-desktop.png (1366px) and stocktake-narrow.png (720px).
- Limits: browser did not finalize outbound receipt, check cross-branch rejection or repeat uploads per role; automated suite covers backend matrix. Admin create checked default CS1; Manager CS2 covers other branch.
- Incidental /favicon.ico returns 404. No app script errors. Existing application database never used.
- QA server stopped. Evidence copied to this directory. Automatic approval review rejected recursive cleanup of disposable QA runtime directory with stated reason 'blocked by policy'; runtime directory remains for lead to handle safely.
