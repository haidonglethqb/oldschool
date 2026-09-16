"""
Concurrency, Row-Level Locking (`select_for_update`), and Atomic Rollback Tests
on PostgreSQL 16 (Scenario 6 & Scenario 10 of System.md §20).
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.db import connections
from apps.accounts.models import User
from apps.branches.models import CoSo
from apps.catalog.models import BienThe
from apps.catalog.services import create_product_with_variants
from apps.inventory.models import StockMovement, TonKho
from apps.inventory.services import StockDeltaSpec, apply_stock_movements, set_opening_stock
from apps.sales_outbound.models import PhieuXuatHangBan
from apps.sales_outbound.services import (
    OutboundReceiptLineSpec,
    create_outbound_receipt,
    finalize_outbound_receipt,
)


@pytest.mark.django_db(transaction=True)
class TestPostgreSQLConcurrencyAndAtomicity:
    def test_scenario_6_concurrent_outbound_finalization_prevents_negative_stock(self):
        """
        Scenario 6 (Real PostgreSQL Concurrency):
        - Branch CS1 has 5 units of SKU `SP-CONC-M`.
        - Two pending outbound receipts (`PXB-CONC-1` for 4 units, `PXB-CONC-2` for 4 units)
          were created while stock was 5.
        - Two concurrent threads attempt to call `finalize_outbound_receipt` simultaneously.
        - Because `apply_stock_movements` locks `TonKho` with `select_for_update()`,
          EXACTLY ONE thread succeeds (stock becomes 5 - 4 = 1) and the second thread
          fails with `InsufficientStockError` (subclass of `ValidationError`).
        - Final stock is 1 (never -3).
        """
        cs1 = CoSo.objects.create(
            ma_co_so="CS1",
            ten_co_so="Kho tổng CS1",
            dia_chi="Đà Nẵng",
            sdt="02363888101",
            is_central_warehouse=True,
        )
        mgr = User.objects.create_user(
            username="mgr_conc",
            password="OldSchool@123",
            role=User.Role.MANAGER,
            branch=cs1,
        )
        create_product_with_variants(
            actor=mgr,
            ma_san_pham="SP-CONC",
            ten_hang_hoa="Áo Concurrency Test",
            nhom_hang="Áo thun",
            don_vi_tinh="Cái",
            don_gia_niem_yet=Decimal("200000"),
            variants_data=[{"ma_sku": "SP-CONC-M", "mau_sac": "Đen", "kich_co": "M", "don_gia": Decimal("200000")}],
        )
        variant = BienThe.objects.get(ma_sku="SP-CONC-M")
        set_opening_stock(branch=cs1, variant=variant, quantity=5, actor=mgr)

        r1 = create_outbound_receipt(
            actor=mgr,
            co_so=cs1,
            ma_phieu_xuat_hang_ban="PXB-CONC-1",
            ten_khach_hang="Khách A",
            sdt="0905111111",
            dia_chi="Đà Nẵng",
            line_specs=[OutboundReceiptLineSpec(variant_id=variant.id, so_luong=4)],
            finalize_immediately=False,
        )
        r2 = create_outbound_receipt(
            actor=mgr,
            co_so=cs1,
            ma_phieu_xuat_hang_ban="PXB-CONC-2",
            ten_khach_hang="Khách B",
            sdt="0905222222",
            dia_chi="Đà Nẵng",
            line_specs=[OutboundReceiptLineSpec(variant_id=variant.id, so_luong=4)],
            finalize_immediately=False,
        )

        def _worker(receipt_id: int) -> str:
            try:
                rec = PhieuXuatHangBan.objects.get(pk=receipt_id)
                actor_obj = User.objects.get(pk=mgr.id)
                finalize_outbound_receipt(actor=actor_obj, receipt=rec)
                return "SUCCESS"
            except ValidationError:
                return "INSUFFICIENT_STOCK"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_worker, r1.id), pool.submit(_worker, r2.id)]
            outcomes = sorted(f.result() for f in futures)

        assert outcomes == ["INSUFFICIENT_STOCK", "SUCCESS"]
        final_bal = TonKho.objects.get(co_so=cs1, bien_the=variant)
        assert final_bal.so_luong == 1

    def test_scenario_10_multiline_atomic_rollback_on_partial_failure(self):
        """
        Scenario 10:
        A multi-line stock mutation where Line 1 (SKU A) has sufficient stock (10 >= 3)
        and Line 2 (SKU B) has insufficient stock (2 < 5) must roll back the ENTIRE transaction:
        SKU A remains 10, SKU B remains 2, and zero `StockMovement` rows are created for that batch.
        """
        cs1 = CoSo.objects.create(
            ma_co_so="CS1-RB",
            ten_co_so="Kho Rollback",
            dia_chi="Đà Nẵng",
            sdt="02363000000",
            is_central_warehouse=True,
        )
        mgr = User.objects.create_user(
            username="mgr_rb",
            password="OldSchool@123",
            role=User.Role.MANAGER,
            branch=cs1,
        )
        create_product_with_variants(
            actor=mgr,
            ma_san_pham="SP-RB",
            ten_hang_hoa="Áo Rollback Test",
            nhom_hang="Áo khoác",
            don_vi_tinh="Cái",
            don_gia_niem_yet=Decimal("300000"),
            variants_data=[
                {"ma_sku": "SP-RB-A", "mau_sac": "Đen", "kich_co": "S", "don_gia": Decimal("300000")},
                {"ma_sku": "SP-RB-B", "mau_sac": "Trắng", "kich_co": "L", "don_gia": Decimal("300000")},
            ],
        )
        sku_a = BienThe.objects.get(ma_sku="SP-RB-A")
        sku_b = BienThe.objects.get(ma_sku="SP-RB-B")
        set_opening_stock(branch=cs1, variant=sku_a, quantity=10, actor=mgr)
        set_opening_stock(branch=cs1, variant=sku_b, quantity=2, actor=mgr)

        movements_before = StockMovement.objects.filter(co_so=cs1).count()

        with pytest.raises(ValidationError):
            apply_stock_movements(
                branch=cs1,
                deltas=[
                    StockDeltaSpec(variant=sku_a, quantity_delta=-3, idempotency_key="RB-TEST-LINE-1"),
                    StockDeltaSpec(variant=sku_b, quantity_delta=-5, idempotency_key="RB-TEST-LINE-2"),
                ],
                movement_type=StockMovement.MovementType.SALE_OUT,
                source_doc_type="RollbackTest",
                source_doc_id=999,
                source_doc_code="RB-999",
                actor=mgr,
            )

        assert TonKho.objects.get(co_so=cs1, bien_the=sku_a).so_luong == 10
        assert TonKho.objects.get(co_so=cs1, bien_the=sku_b).so_luong == 2
        assert StockMovement.objects.filter(co_so=cs1).count() == movements_before
