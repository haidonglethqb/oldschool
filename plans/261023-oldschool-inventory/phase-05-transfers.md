# Phase 05: Interbranch Transfers (`Điều chuyển liên cơ sở`)

## Overview
- **Priority**: P1
- **Status**: Pending
- **Description**: Implement `PhieuDieuChuyen` and `ChiTietPhieuDieuChuyen` (`UC-5.3`), state lifecycle (`REQUESTED → ACCEPTED → DISPATCHED → RECEIVED / RECEIVED_WITH_SHORTAGE / REJECTED / CANCELLED`), sender stock deduction on dispatch (in-transit tracking), receiver confirmation, and explicit discrepancy recording.

## Related Code Files
- `apps/transfers/models.py`, `apps/transfers/forms.py`, `apps/transfers/services.py`, `apps/transfers/selectors.py`, `apps/transfers/views.py`, `apps/transfers/urls.py`
- `templates/transfers/transfer_list.html`, `templates/transfers/transfer_detail.html`, `templates/transfers/transfer_form.html`, `templates/transfers/transfer_receive.html`

## Todo List
- [ ] Implement `PhieuDieuChuyen` and `ChiTietPhieuDieuChuyen` with `co_so_xuat != co_so_nhan` constraint
- [ ] Implement `create_transfer_request`, `accept_transfer`, `reject_transfer`
- [ ] Implement `dispatch_transfer` (deduct sender stock atomically & mark in-transit)
- [ ] Implement `receive_transfer` (credit receiver stock by actual received qty & record `RECEIVED_WITH_SHORTAGE` on shortage)
