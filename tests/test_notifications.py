"""
Tests for Deduplicated Low-Stock Warnings & Auto-Resolution (UC-5.13).
"""
from decimal import Decimal
import pytest
from apps.inventory.models import TonKho
from apps.notifications.models import ThongBao
from apps.purchasing.services import ImportLineSpec, approve_import_receipt, create_import_receipt
from apps.sales_outbound.services import OutboundReceiptLineSpec, create_outbound_receipt


@pytest.mark.django_db
class TestNotificationsAndLowStockAlerts:
    def test_low_stock_alert_deduplication_and_auto_resolution_on_replenishment(
        self, users, branches, supplier, sample_catalog
    ):
        """
        1. CS1 has 30 units of v_m (min_threshold=5). No unresolved low-stock alert exists for (CS1, v_m).
        2. CS1 sells 26 units -> remaining = 4 -> 1 unresolved LOW_STOCK_ALERT is created.
        3. CS1 sells 1 more unit -> remaining = 3 -> existing alert is updated in-place (still 1 unresolved alert, no duplicates).
        4. CS1 receives +20 units via approved import -> remaining = 23 (> 5) -> alert is automatically marked resolved (`da_xu_ly=True`).
        """
        cs1 = branches["CS1"]
        v_m = sample_catalog["v_m"]

        assert (
            ThongBao.objects.filter(
                loai_thong_bao=ThongBao.NotificationType.LOW_STOCK_ALERT,
                co_so=cs1,
                bien_the=v_m,
                da_xu_ly=False,
            ).count()
            == 0
        )

        # Deduct 26 -> stock = 4
        create_outbound_receipt(
            actor=users["mgr_cs1"],
            co_so=cs1,
            ten_khach_hang="Khách 1",
            sdt="0905000111",
            dia_chi="Đà Nẵng",
            line_specs=[OutboundReceiptLineSpec(variant_id=v_m.id, so_luong=26)],
            finalize_immediately=True,
        )
        open_alerts = ThongBao.objects.filter(
            loai_thong_bao=ThongBao.NotificationType.LOW_STOCK_ALERT,
            co_so=cs1,
            bien_the=v_m,
            da_xu_ly=False,
        )
        assert open_alerts.count() >= 1
        initial_alert_count = open_alerts.count()

        # Deduct 1 more -> stock = 3 -> must update existing open alert(s) without duplicating
        create_outbound_receipt(
            actor=users["mgr_cs1"],
            co_so=cs1,
            ten_khach_hang="Khách 2",
            sdt="0905000222",
            dia_chi="Đà Nẵng",
            line_specs=[OutboundReceiptLineSpec(variant_id=v_m.id, so_luong=1)],
            finalize_immediately=True,
        )
        assert (
            ThongBao.objects.filter(
                loai_thong_bao=ThongBao.NotificationType.LOW_STOCK_ALERT,
                co_so=cs1,
                bien_the=v_m,
                da_xu_ly=False,
            ).count()
            == initial_alert_count
        )

        # Replenish +20 via approved import -> stock = 23 -> alert auto-resolves
        imp = create_import_receipt(
            actor=users["mgr_cs1"],
            nha_cung_cap=supplier,
            line_specs=[ImportLineSpec(variant_id=v_m.id, so_luong=20, don_gia=Decimal("250000"))],
        )
        approve_import_receipt(actor=users["admin"], receipt=imp)
        assert TonKho.objects.get(co_so=cs1, bien_the=v_m).so_luong == 23
        assert (
            ThongBao.objects.filter(
                loai_thong_bao=ThongBao.NotificationType.LOW_STOCK_ALERT,
                co_so=cs1,
                bien_the=v_m,
                da_xu_ly=False,
            ).count()
            == 0
        )
