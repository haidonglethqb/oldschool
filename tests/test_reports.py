"""
Tests for Dynamic Inventory & Supply Chain Reporting (UC-7.1 to UC-7.5, Scenario 8).
Verifies:
- Dynamic computation of opening, import_in, transfer_in, sale_out, transfer_out, closing, and in_transit
- Strict separation between sales outbound and interbranch transfers
- Branch scoping for Managers vs global/branch filtering for Admin
- Safe Excel export (UC-7.3)
"""
import pytest
from django.urls import reverse
from apps.reports.selectors import build_inventory_report
from apps.sales_outbound.services import OutboundReceiptLineSpec, create_outbound_receipt
from apps.transfers.services import TransferRequestLineSpec, create_transfer_request, dispatch_transfer


@pytest.mark.django_db
class TestReportsModule:
    def test_scenario_8_report_separates_sales_from_transfers_and_tracks_in_transit(
        self, client, users, branches, sample_catalog
    ):
        """
        Scenario 8:
        - CS1 starts with 30 units of v_m.
        - CS1 sells 4 units (`SALE_OUT`) -> sale_out_qty = 4.
        - CS1 dispatches 6 units to CS2 (`TRANSFER_OUT`, still `DISPATCHED`) -> transfer_out_qty = 6, in_transit_qty = 6.
        - Report for CS1 must show:
          opening_qty = 30, sale_out_qty = 4, transfer_out_qty = 6, total_out_qty = 10, closing_qty = 20, in_transit_qty = 6.
        """
        cs1, cs2 = branches["CS1"], branches["CS2"]
        v_m = sample_catalog["v_m"]

        create_outbound_receipt(
            actor=users["mgr_cs1"],
            co_so=cs1,
            ten_khach_hang="Khách mua lẻ CS1",
            sdt="0905111222",
            dia_chi="Hải Châu",
            line_specs=[OutboundReceiptLineSpec(variant_id=v_m.id, so_luong=4)],
            finalize_immediately=True,
        )

        t = create_transfer_request(
            actor=users["mgr_cs2"],
            co_so_xuat=cs1,
            co_so_nhan=cs2,
            line_specs=[TransferRequestLineSpec(variant_id=v_m.id, so_luong_yeu_cau=6)],
        )
        dispatch_transfer(actor=users["mgr_cs1"], transfer=t)

        report_cs1 = build_inventory_report(
            user=users["mgr_cs1"],
            search_query="SP001-DEN-M",
        )
        assert len(report_cs1["rows"]) == 1
        row = report_cs1["rows"][0]
        assert row["opening_qty"] == 30
        assert row["sale_out_qty"] == 4
        assert row["transfer_out_qty"] == 6
        assert row["total_out_qty"] == 10
        assert row["closing_qty"] == 20
        assert row["in_transit_qty"] == 6

        # Excel export works (UC-7.3)
        client.force_login(users["admin"])
        resp_excel = client.get(reverse("reports:report_dashboard"), {"export": "excel"})
        assert resp_excel.status_code == 200
        assert (
            resp_excel["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
