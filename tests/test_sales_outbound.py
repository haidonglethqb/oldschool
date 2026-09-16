"""
Tests for Sales Outbound Requests, Receipts, Print Slip & Low-Stock Alerts
(UC-5.1, UC-5.2, UC-5.4 to UC-5.13, Scenario 3 & Scenario 4).
"""
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from apps.inventory.models import TonKho
from apps.notifications.models import ThongBao
from apps.sales_outbound.models import PhieuXuatHangBan, YeuCauXuatHang
from apps.sales_outbound.services import (
    OutboundReceiptLineSpec,
    OutboundRequestLineSpec,
    create_outbound_receipt,
    create_outbound_request,
    delete_outbound_receipt,
    finalize_outbound_receipt,
    update_outbound_receipt,
)


@pytest.mark.django_db
class TestSalesOutboundModule:
    def test_scenario_3_sales_outbound_when_stock_sufficient_and_low_stock_alert(
        self, client, users, branches, sample_catalog
    ):
        """
        Scenario 3:
        1. Staff at CS2 creates a sales outbound request.
        2. Manager at CS2 prepares an outbound receipt from the request (PENDING -> stock not deducted yet).
        3. Manager at CS2 finalizes the receipt (COMPLETED -> stock deducted atomically).
        4. When remaining stock <= min_threshold (5), a LOW_STOCK_ALERT notification is generated (UC-5.13).
        5. Completed receipt can be printed (UC-5.12) and cannot be deleted or finalized twice.
        """
        cs2 = branches["CS2"]
        v_m = sample_catalog["v_m"]  # Initial stock at CS2 = 10, min_threshold = 5

        req = create_outbound_request(
            actor=users["staff_cs2"],
            co_so=cs2,
            ten_khach_hang="Khách lẻ CS2",
            line_specs=[OutboundRequestLineSpec(variant_id=v_m.id, so_luong=6)],
        )
        assert req.trang_thai == YeuCauXuatHang.Status.PENDING

        receipt = create_outbound_receipt(
            actor=users["mgr_cs2"],
            co_so=cs2,
            yeu_cau_xuat=req,
            ten_khach_hang="Khách lẻ CS2",
            sdt="0905123456",
            dia_chi="Thanh Khê, Đà Nẵng",
            line_specs=[OutboundReceiptLineSpec(variant_id=v_m.id, so_luong=6)],
            finalize_immediately=False,
        )
        assert receipt.trang_thai == PhieuXuatHangBan.Status.PENDING
        # Stock still 10 before finalization
        assert TonKho.objects.get(co_so=cs2, bien_the=v_m).so_luong == 10

        finalize_outbound_receipt(actor=users["mgr_cs2"], receipt=receipt)
        receipt.refresh_from_db()
        assert receipt.trang_thai == PhieuXuatHangBan.Status.COMPLETED
        # Stock is now 10 - 6 = 4 (<= min_threshold 5)
        assert TonKho.objects.get(co_so=cs2, bien_the=v_m).so_luong == 4

        # Low-stock alert must exist for (CS2, v_m)
        assert ThongBao.objects.filter(
            loai_thong_bao=ThongBao.NotificationType.LOW_STOCK_ALERT,
            co_so=cs2,
            bien_the=v_m,
            da_xu_ly=False,
        ).exists()

        # Printable view works for COMPLETED receipt (UC-5.12)
        client.force_login(users["mgr_cs2"])
        resp_print = client.get(reverse("sales_outbound:outbound_print", args=[receipt.id]))
        assert resp_print.status_code == 200
        assert receipt.ma_phieu_xuat_hang_ban in resp_print.content.decode("utf-8")

        # Cannot finalize again or delete completed receipt
        with pytest.raises(ValidationError):
            finalize_outbound_receipt(actor=users["mgr_cs2"], receipt=receipt)
        with pytest.raises(ValidationError):
            delete_outbound_receipt(actor=users["mgr_cs2"], receipt=receipt)

    def test_scenario_4_outbound_rejected_when_exceeding_branch_stock(
        self, users, branches, sample_catalog
    ):
        """
        Scenario 4:
        Attempting to create or finalize an outbound receipt for a quantity exceeding
        the branch's current stock raises ValidationError and leaves stock unchanged.
        """
        cs2 = branches["CS2"]
        v_m = sample_catalog["v_m"]  # Stock at CS2 = 10

        with pytest.raises(ValidationError):
            create_outbound_receipt(
                actor=users["mgr_cs2"],
                co_so=cs2,
                ten_khach_hang="Khách mua sỉ vượt tồn",
                sdt="0905999999",
                dia_chi="Đà Nẵng",
                line_specs=[OutboundReceiptLineSpec(variant_id=v_m.id, so_luong=15)],
                finalize_immediately=True,
            )

        assert TonKho.objects.get(co_so=cs2, bien_the=v_m).so_luong == 10

        # Cross-branch manipulation blocked
        with pytest.raises(PermissionDenied):
            create_outbound_receipt(
                actor=users["mgr_cs2"],
                co_so=branches["CS1"],
                ten_khach_hang="Hack CS1",
                sdt="0905999999",
                dia_chi="Đà Nẵng",
                line_specs=[OutboundReceiptLineSpec(variant_id=v_m.id, so_luong=1)],
            )

    def test_outbound_request_duplicate_guard_and_restore_on_receipt_delete(
        self, users, branches, sample_catalog
    ):
        """
        Edge Case:
        1. Creating a second outbound receipt from an already-processed YeuCauXuatHang raises ValidationError.
        2. Deleting a PENDING PhieuXuatHangBan restores its linked YeuCauXuatHang back to PENDING.
        """
        cs2 = branches["CS2"]
        v_m = sample_catalog["v_m"]

        req = create_outbound_request(
            actor=users["staff_cs2"],
            co_so=cs2,
            ten_khach_hang="Khách test yêu cầu kép",
            line_specs=[OutboundRequestLineSpec(variant_id=v_m.id, so_luong=2)],
        )
        receipt = create_outbound_receipt(
            actor=users["mgr_cs2"],
            co_so=cs2,
            yeu_cau_xuat=req,
            ten_khach_hang="Khách test yêu cầu kép",
            sdt="0905111333",
            dia_chi="Đà Nẵng",
            line_specs=[OutboundReceiptLineSpec(variant_id=v_m.id, so_luong=2)],
            finalize_immediately=False,
        )
        req.refresh_from_db()
        assert req.trang_thai == YeuCauXuatHang.Status.PROCESSED

        # Attempting to create a second receipt from the same request must fail with ValidationError
        with pytest.raises(ValidationError):
            create_outbound_receipt(
                actor=users["mgr_cs2"],
                co_so=cs2,
                yeu_cau_xuat=req,
                ten_khach_hang="Khách test yêu cầu kép lần 2",
                sdt="0905111333",
                dia_chi="Đà Nẵng",
                line_specs=[OutboundReceiptLineSpec(variant_id=v_m.id, so_luong=2)],
            )

        # Deleting the unfinalized receipt restores the request back to PENDING
        delete_outbound_receipt(actor=users["mgr_cs2"], receipt=receipt)
        req.refresh_from_db()
        assert req.trang_thai == YeuCauXuatHang.Status.PENDING
        assert req.nguoi_xu_ly is None
