"""
Tests for Stocktake / Inventory Count Records (UC-6.1 to UC-6.10, Scenario 7, DEC-02 & DEC-03).
"""
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from apps.inventory.models import TonKho
from apps.stocktakes.models import ChiTietKiemKe, KiemKe
from apps.stocktakes.services import (
    StocktakeLineSpec,
    approve_stocktake,
    create_stocktake,
    delete_stocktake,
    reject_stocktake,
    update_stocktake,
)


@pytest.mark.django_db
class TestStocktakesModule:
    def test_scenario_7_stocktake_reconciliation_and_admin_only_approval(
        self, users, branches, sample_catalog
    ):
        """
        Scenario 7:
        1. CS2 Manager creates a stocktake where system stock for v_m is 10 (actual counted = 9 -> SHORTAGE -1)
           and for v_l is 4 (actual counted = 4 -> MATCH 0).
        2. CS2 Manager cannot approve their own stocktake (DEC-02 -> PermissionDenied).
        3. Admin approves stocktake (UC-6.10) -> status becomes APPROVED, while physical TonKho
           remains unchanged at 10 and 4 per DEC-03 / UC-6.10.
        """
        cs2 = branches["CS2"]
        v_m = sample_catalog["v_m"]  # System stock = 10
        v_l = sample_catalog["v_l"]  # System stock = 4

        st = create_stocktake(
            actor=users["mgr_cs2"],
            co_so=cs2,
            ma_kiem_ke="KK-TEST-CS2-001",
            nguoi_kiem_ke="Lê Văn Quản Lý CS2",
            line_specs=[
                StocktakeLineSpec(variant_id=v_m.id, so_luong_thuc_te=9, xu_ly="Đang tìm kiếm 1 cái thất lạc"),
                StocktakeLineSpec(variant_id=v_l.id, so_luong_thuc_te=4, xu_ly="Khớp"),
            ],
        )
        assert st.trang_thai == KiemKe.Status.PENDING
        line_m = st.lines.get(bien_the=v_m)
        line_l = st.lines.get(bien_the=v_l)
        assert line_m.so_luong_he_thong == 10
        assert line_m.chenh_lech == -1
        assert line_m.trang_thai_doi_chieu == ChiTietKiemKe.ReconciliationStatus.SHORTAGE
        assert line_l.chenh_lech == 0
        assert line_l.trang_thai_doi_chieu == ChiTietKiemKe.ReconciliationStatus.MATCH

        # Manager cannot approve stocktake (DEC-02)
        with pytest.raises(PermissionDenied):
            approve_stocktake(actor=users["mgr_cs2"], stocktake=st)

        # Admin approves stocktake (DEC-03)
        approve_stocktake(actor=users["admin"], stocktake=st)
        st.refresh_from_db()
        assert st.trang_thai == KiemKe.Status.APPROVED
        # Physical stock is NOT silently overwritten
        assert TonKho.objects.get(co_so=cs2, bien_the=v_m).so_luong == 10

        # Approved stocktake cannot be deleted or edited
        with pytest.raises(ValidationError):
            delete_stocktake(actor=users["admin"], stocktake=st)

    def test_stocktake_reject_and_resubmit_flow(self, users, branches, sample_catalog):
        cs2 = branches["CS2"]
        v_m = sample_catalog["v_m"]

        st = create_stocktake(
            actor=users["mgr_cs2"],
            co_so=cs2,
            line_specs=[StocktakeLineSpec(variant_id=v_m.id, so_luong_thuc_te=8)],
        )
        reject_stocktake(actor=users["admin"], stocktake=st, reason="Đề nghị kiểm lại kho phụ")
        st.refresh_from_db()
        assert st.trang_thai == KiemKe.Status.REJECTED

        # Rejected stocktake can be updated by branch manager
        update_stocktake(
            actor=users["mgr_cs2"],
            stocktake=st,
            line_specs=[StocktakeLineSpec(variant_id=v_m.id, so_luong_thuc_te=10, xu_ly="Đã tìm thấy 2 cái ở kệ phụ")],
        )
        st.refresh_from_db()
        assert st.trang_thai == KiemKe.Status.PENDING
        assert st.lines.first().chenh_lech == 0
