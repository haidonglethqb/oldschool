"""Tests for Deep Edge Cases and Business Logic Hardening (EC-14 to EC-28)."""
import pytest
from decimal import Decimal
from django.utils import timezone
from apps.accounts.models import User
from apps.branches.models import CoSo
from apps.catalog.models import BienThe, SanPham
from apps.catalog.services import (
    create_product_with_variants,
    toggle_product_business_status,
    update_product_and_variants,
)
from apps.inventory.models import StockMovement, TonKho
from apps.inventory.services import set_opening_stock
from apps.notifications.models import ThongBao
from apps.notifications.services import notify_branch_managers, sync_low_stock_alert
from apps.purchasing.models import ChiTietPhieuNhapKho, NhaCungCap, PhieuNhapKho
from apps.purchasing.services import (
    ImportLineSpec,
    approve_import_receipt,
    create_import_receipt,
    generate_next_import_code,
    update_import_receipt,
)
from apps.reports.selectors import build_inventory_report


@pytest.mark.django_db
class TestAuditedEdgeCases:
    def test_dec_07_average_cost_price_and_slow_moving_logic(self, branches, users, supplier):
        """DEC-07: Report calculates cost price from approved imports, and flags slow moving items."""
        branch_cs1 = branches["CS1"]
        admin_user = users["admin"]
        manager_cs1 = users["mgr_cs1"]

        # 1. Create product and variant
        product = create_product_with_variants(
            actor=admin_user,
            ma_san_pham="SP-DEC07",
            ten_hang_hoa="Sơ mi Vintage DEC07",
            nhom_hang="Áo sơ mi",
            don_vi_tinh="Cái",
            variants_data=[{"mau_sac": "Trắng", "kich_co": "L", "don_gia": Decimal("250000")}],
        )
        variant = product.variants.first()

        # 2. Before any approved import, cost price should fallback to 0 per DEC-07
        today = timezone.localdate()
        report_initial = build_inventory_report(
            user=admin_user,
            selected_branch=branch_cs1,
            date_from_str=str(today),
            date_to_str=str(today),
        )
        row_initial = next(r for r in report_initial["rows"] if r["variant"].id == variant.id)
        assert row_initial["cost_price"] == Decimal("0")
        assert row_initial["inventory_value"] == Decimal("0")

        # 3. Create and approve an import receipt with import price 120,000 VND
        receipt = create_import_receipt(
            actor=manager_cs1,
            nha_cung_cap=supplier,
            co_so_nhan=branch_cs1,
            ma_phieu_nhap_kho="PNK-20261026-901",
            line_specs=[
                ImportLineSpec(
                    variant_id=variant.id,
                    so_luong=10,
                    don_gia=Decimal("120000"),
                    chiet_khau=Decimal("0"),
                )
            ],
            submit_for_approval=True,
        )
        approve_import_receipt(actor=admin_user, receipt=receipt)

        # 4. Check report again: cost price should be 120,000 and closing stock value = 10 * 120,000 = 1,200,000
        report_after = build_inventory_report(
            user=admin_user,
            selected_branch=branch_cs1,
            date_from_str=str(today),
            date_to_str=str(today),
        )
        row_after = next(r for r in report_after["rows"] if r["variant"].id == variant.id)
        assert row_after["cost_price"] == Decimal("120000")
        assert row_after["inventory_value"] == Decimal("1200000")
        # No sale occurred and closing_qty is 10 > 0 -> should be slow_moving
        assert row_after["is_slow_moving"] is True

    def test_admin_notifications_separation_and_read_isolation(self, branches, users):
        """EC-20 & EC-21: Admin and manager receive isolated notification records."""
        branch_cs1 = branches["CS1"]
        admin_user = users["admin"]
        manager_cs1 = users["mgr_cs1"]

        notify_branch_managers(
            branch=branch_cs1,
            notification_type=ThongBao.NotificationType.TRANSFER_DISPATCHED,
            title="Kiểm tra cách ly thông báo",
            content="Nội dung kiểm tra phân tách thông báo",
        )
        # Should create notification for manager and notification for admin
        mgr_notif = ThongBao.objects.filter(nguoi_nhan=manager_cs1).first()
        admin_notif = ThongBao.objects.filter(nguoi_nhan=admin_user).first()
        assert mgr_notif is not None
        assert admin_notif is not None

        # Admin marks their notification as read
        admin_notif.da_doc = True
        admin_notif.save()

        # Manager's notification must remain unread
        mgr_notif.refresh_from_db()
        assert mgr_notif.da_doc is False

    def test_low_stock_alert_sync_on_threshold_update_and_product_status_toggle(self, branches, users):
        """EC-20 & EC-22: Updating min_threshold or toggling product status syncs low stock alert."""
        branch_cs1 = branches["CS1"]
        admin_user = users["admin"]

        product = create_product_with_variants(
            actor=admin_user,
            ma_san_pham="SP-SYNC-ALERT",
            ten_hang_hoa="Quần Jeans Alert",
            nhom_hang="Quần jeans",
            don_vi_tinh="Chiếc",
            don_gia_niem_yet=Decimal("350000"),
            variants_data=[{"mau_sac": "Xanh", "kich_co": "30", "don_gia": Decimal("350000")}],
        )
        variant = product.variants.first()
        # Set 3 items in stock with min_threshold 5
        set_opening_stock(
            branch=branch_cs1,
            variant=variant,
            quantity=3,
            actor=admin_user,
            min_threshold=5,
        )

        tk = TonKho.objects.get(co_so=branch_cs1, bien_the=variant)
        assert tk.so_luong == 3
        assert tk.muc_ton_toi_thieu == 5  # so_luong (3) <= 5 -> alert exists
        alert = ThongBao.objects.filter(
            bien_the=variant,
            co_so=branch_cs1,
            loai_thong_bao=ThongBao.NotificationType.LOW_STOCK_ALERT,
            da_xu_ly=False,
        ).first()
        assert alert is not None

        # Lower threshold to 2 -> so_luong (3) > 2 -> alert should resolve
        update_product_and_variants(
            actor=admin_user,
            product=product,
            ten_hang_hoa=product.ten_hang_hoa,
            nhom_hang=product.nhom_hang,
            don_vi_tinh=product.don_vi_tinh,
            don_gia_niem_yet=Decimal("350000"),
            variants_data=[
                {
                    "id": variant.id,
                    "mau_sac": "Xanh",
                    "kich_co": "30",
                    "don_gia": Decimal("350000"),
                    "min_threshold": 2,
                }
            ],
        )
        alert.refresh_from_db()
        assert alert.da_xu_ly is True

        # Raise threshold back to 5 -> alert should open again
        update_product_and_variants(
            actor=admin_user,
            product=product,
            ten_hang_hoa=product.ten_hang_hoa,
            nhom_hang=product.nhom_hang,
            don_vi_tinh=product.don_vi_tinh,
            don_gia_niem_yet=Decimal("350000"),
            variants_data=[
                {
                    "id": variant.id,
                    "mau_sac": "Xanh",
                    "kich_co": "30",
                    "don_gia": Decimal("350000"),
                    "min_threshold": 5,
                }
            ],
        )
        new_alert = ThongBao.objects.filter(
            bien_the=variant,
            co_so=branch_cs1,
            loai_thong_bao=ThongBao.NotificationType.LOW_STOCK_ALERT,
            da_xu_ly=False,
        ).first()
        assert new_alert is not None

        # Deactivate product -> alert should resolve automatically
        toggle_product_business_status(actor=admin_user, product=product)
        new_alert.refresh_from_db()
        assert new_alert.da_xu_ly is True

    def test_update_import_receipt_draft_vs_submit_approval(self, branches, users, supplier):
        """EC-24: update_import_receipt allows saving as DRAFT or PENDING_APPROVAL with admin alert."""
        branch_cs1 = branches["CS1"]
        admin_user = users["admin"]
        manager_cs1 = users["mgr_cs1"]

        product = create_product_with_variants(
            actor=admin_user,
            ma_san_pham="SP-IMPORT-DRAFT",
            ten_hang_hoa="Khoác Kaki",
            nhom_hang="Áo khoác",
            don_vi_tinh="Chiếc",
            don_gia_niem_yet=Decimal("450000"),
            variants_data=[{"mau_sac": "Rêu", "kich_co": "XL", "don_gia": Decimal("450000")}],
        )
        variant = product.variants.first()

        receipt = create_import_receipt(
            actor=manager_cs1,
            nha_cung_cap=supplier,
            co_so_nhan=branch_cs1,
            ma_phieu_nhap_kho="PNK-20261026-902",
            line_specs=[
                ImportLineSpec(
                    variant_id=variant.id,
                    so_luong=5,
                    don_gia=Decimal("200000"),
                    chiet_khau=Decimal("0"),
                )
            ],
            submit_for_approval=True,
        )
        assert receipt.trang_thai == PhieuNhapKho.Status.PENDING_APPROVAL

        # Update and save as draft
        updated_draft = update_import_receipt(
            actor=manager_cs1,
            receipt=receipt,
            nha_cung_cap=supplier,
            line_specs=[
                ImportLineSpec(
                    variant_id=variant.id,
                    so_luong=6,
                    don_gia=Decimal("200000"),
                    chiet_khau=Decimal("0"),
                )
            ],
            submit_for_approval=False,
        )
        assert updated_draft.trang_thai == PhieuNhapKho.Status.DRAFT

        # Update and resubmit for approval
        updated_pending = update_import_receipt(
            actor=manager_cs1,
            receipt=updated_draft,
            nha_cung_cap=supplier,
            line_specs=[
                ImportLineSpec(
                    variant_id=variant.id,
                    so_luong=8,
                    don_gia=Decimal("200000"),
                    chiet_khau=Decimal("0"),
                )
            ],
            submit_for_approval=True,
        )
        assert updated_pending.trang_thai == PhieuNhapKho.Status.PENDING_APPROVAL
        # Admin should receive notification of resubmission
        notif = ThongBao.objects.filter(
            related_entity_id=receipt.id,
            related_entity_type="PhieuNhapKho",
            loai_thong_bao=ThongBao.NotificationType.IMPORT_SUBMITTED,
        ).last()
        assert notif is not None

    def test_sequential_code_generator_numeric_safety(self, branches, users, supplier):
        """EC-23: generate_next_import_code scans maximum numeric suffix correctly."""
        branch_cs1 = branches["CS1"]
        manager_cs1 = users["mgr_cs1"]
        today_str = timezone.localdate().strftime("%Y%m%d")

        # Pre-create code with 009
        PhieuNhapKho.objects.create(
            ma_phieu_nhap_kho=f"PNK-{today_str}-009",
            nha_cung_cap=supplier,
            co_so_nhan=branch_cs1,
            nguoi_tao=manager_cs1,
            trang_thai=PhieuNhapKho.Status.DRAFT,
        )
        next_code = generate_next_import_code()
        assert next_code == f"PNK-{today_str}-010"
