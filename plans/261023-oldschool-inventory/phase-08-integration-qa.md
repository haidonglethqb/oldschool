# Phase 08: System Integration & Concurrency QA

## Overview
- **Priority**: P1
- **Status**: Pending
- **Description**: Execute comprehensive automated tests covering all 10 User Acceptance Scenarios in `docs/System.md` §20, PostgreSQL concurrent row-locking tests (`select_for_update`), failure rollback tests, RBAC bypass tests, and Playwright E2E browser tests.

## Related Code Files
- `pytest.ini`
- `tests/test_accounts.py`, `tests/test_catalog.py`, `tests/test_purchasing.py`, `tests/test_sales_outbound.py`, `tests/test_transfers.py`, `tests/test_stocktakes.py`, `tests/test_reports.py`, `tests/test_notifications.py`, `tests/test_concurrency.py`, `tests/e2e/test_browser_flows.py`

## Todo List
- [ ] Run unit and integration test suites across all 9 Django apps
- [ ] Run PostgreSQL concurrent outbound test (Scenario 9) and failure rollback test (Scenario 10)
- [ ] Run Playwright browser tests and capture representative UI screenshots
