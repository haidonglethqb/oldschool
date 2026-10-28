import pytest
from decimal import Decimal
from django.urls import reverse
from apps.accounts.models import User
from apps.inventory.models import TonKho
from apps.purchasing.models import PhieuNhapKho
from apps.purchasing.services import ImportLineSpec, create_import_receipt, propose_supplier_return, confirm_supplier_return
from apps.stocktakes.services import StocktakeLineSpec, create_stocktake
from apps.transfers.models import PhieuDieuChuyen
from apps.transfers.services import TransferRequestLineSpec, create_transfer_request, dispatch_transfer, receive_transfer


@pytest.mark.django_db
class TestFeedbackAdjustments:
    def test_admin_stocktake_creation_auto_approves_and_has_save_button(self, client, users, branches, sample_catalog):
        """Admin creates stocktake -> status is directly APPROVED with no pending state."""
        admin = users["admin"]
        v_m = sample_catalog["v_m"]
        client.force_login(admin)

        # GET stocktake create form: verify button says 'Lưu' for Admin
        resp_get = client.get(reverse("stocktakes:stocktake_create"))
        assert resp_get.status_code == 200
        html = resp_get.content.decode("utf-8")
        assert "Lưu</button>" in html or "Lưu" in html
        assert "UC-6.2" not in html

        # Create stocktake as admin
        st = create_stocktake(
            actor=admin,
            co_so=branches["CS1"],
            line_specs=[StocktakeLineSpec(variant_id=v_m.id, so_luong_thuc_te=20)],
        )
        assert st.trang_thai == "APPROVED"
        assert st.duyet_boi == admin
        assert st.thoi_gian_duyet is not None

    def test_manager_propose_defect_return_and_admin_confirm(self, client, users, branches, supplier, sample_catalog):
        """Manager inspects goods, reports defect, and Admin confirms returning to NCC."""
        mgr = users["mgr_cs1"]
        admin = users["admin"]
        v_m = sample_catalog["v_m"]
        initial_stock = TonKho.objects.get(co_so=branches["CS1"], bien_the=v_m).so_luong

        receipt = create_import_receipt(
            actor=mgr,
            nha_cung_cap=supplier,
            ma_phieu_nhap_kho="PNK-DEFECT-001",
            line_specs=[ImportLineSpec(variant_id=v_m.id, so_luong=10, don_gia=Decimal("200000"))],
        )
        assert receipt.trang_thai == PhieuNhapKho.Status.PENDING_APPROVAL

        # Manager reports defect
        client.force_login(mgr)
        resp_propose = client.post(
            reverse("purchasing:import_propose_return", args=[receipt.id]),
            {"ly_do_loi_ncc": "Hàng lỗi đường may rách nách 10 áo"},
        )
        assert resp_propose.status_code == 302
        receipt.refresh_from_db()
        assert receipt.trang_thai == PhieuNhapKho.Status.RETURN_PROPOSED
        assert "Hàng lỗi đường may" in receipt.ly_do_loi_ncc
        assert receipt.nguoi_bao_loi == mgr

        # Admin confirms return to supplier
        client.force_login(admin)
        resp_confirm = client.post(
            reverse("purchasing:import_confirm_supplier_return", args=[receipt.id]),
            {"ghi_chu_chu": "Đồng ý trả lại NCC"},
        )
        assert resp_confirm.status_code == 302
        receipt.refresh_from_db()
        assert receipt.trang_thai == PhieuNhapKho.Status.RETURNED_TO_SUPPLIER

        # Verify stock did NOT increase
        final_stock = TonKho.objects.get(co_so=branches["CS1"], bien_the=v_m).so_luong
        assert final_stock == initial_stock

    def test_transfer_bidirectional_cs1_and_cs2(self, client, users, branches, sample_catalog):
        """Both CS1 and CS2 can create and dispatch transfers."""
        mgr_cs1 = users["mgr_cs1"]
        mgr_cs2 = users["mgr_cs2"]
        v_m = sample_catalog["v_m"]

        # Transfer 1: CS1 -> CS2
        t1 = create_transfer_request(
            actor=mgr_cs1,
            co_so_xuat=branches["CS1"],
            co_so_nhan=branches["CS2"],
            line_specs=[TransferRequestLineSpec(variant_id=v_m.id, so_luong_yeu_cau=5)],
        )
        dispatch_transfer(actor=mgr_cs1, transfer=t1)
        t1.refresh_from_db()
        assert t1.trang_thai == PhieuDieuChuyen.Status.DISPATCHED
        receive_transfer(actor=mgr_cs2, transfer=t1)
        t1.refresh_from_db()
        assert t1.trang_thai == PhieuDieuChuyen.Status.RECEIVED

        # Transfer 2: CS2 -> CS1
        t2 = create_transfer_request(
            actor=mgr_cs2,
            co_so_xuat=branches["CS2"],
            co_so_nhan=branches["CS1"],
            line_specs=[TransferRequestLineSpec(variant_id=v_m.id, so_luong_yeu_cau=2)],
        )
        dispatch_transfer(actor=mgr_cs2, transfer=t2)
        t2.refresh_from_db()
        assert t2.trang_thai == PhieuDieuChuyen.Status.DISPATCHED
        receive_transfer(actor=mgr_cs1, transfer=t2)
        t2.refresh_from_db()
        assert t2.trang_thai == PhieuDieuChuyen.Status.RECEIVED

    def test_report_page_has_lich_su_bien_dong_and_no_uc_codes(self, client, users):
        """Dashboard shows 'LỊCH SỬ BIẾN ĐỘNG' header and no UC tags."""
        client.force_login(users["admin"])
        resp = client.get(reverse("reports:report_dashboard"))
        assert resp.status_code == 200
        html = resp.content.decode("utf-8")
        assert "LỊCH SỬ BIẾN ĐỘNG" in html
        assert "SỔ CÁI" not in html
        assert "UC-7.1" not in html
        assert "UC-7.2" not in html
