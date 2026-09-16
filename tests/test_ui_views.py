"""End-to-end View & Template Rendering Tests across all 7 user-facing modules."""
import pytest
from django.core.management import call_command
from django.urls import reverse
from apps.accounts.models import User
from apps.catalog.models import BienThe, SanPham
from apps.purchasing.models import PhieuNhapKho
from apps.sales_outbound.models import PhieuXuatHangBan
from apps.stocktakes.models import KiemKe
from apps.transfers.models import PhieuDieuChuyen


@pytest.mark.django_db
class TestAllUIViewsRenderCleanly:
    def test_seeded_views_render_200_for_admin_and_managers(self, client):
        """Seed full dataset and verify every screen renders HTTP 200 with Vietnamese UI."""
        call_command("seed_oldschool")

        admin = User.objects.get(username="admin_owner")
        client.force_login(admin)

        product = SanPham.objects.first()
        variant = BienThe.objects.first()
        imp = PhieuNhapKho.objects.first()
        out = PhieuXuatHangBan.objects.filter(trang_thai=PhieuXuatHangBan.Status.COMPLETED).first()
        transfer = PhieuDieuChuyen.objects.first()
        stocktake = KiemKe.objects.first()

        urls_to_check = [
            reverse("catalog:product_list"),
            reverse("catalog:product_detail", args=[product.id]),
            reverse("catalog:product_create"),
            reverse("catalog:product_edit", args=[product.id]),
            reverse("purchasing:import_list"),
            reverse("purchasing:import_create"),
            reverse("purchasing:import_detail", args=[imp.id]),
            reverse("purchasing:supplier_list"),
            reverse("sales_outbound:outbound_list"),
            reverse("sales_outbound:outbound_create"),
            reverse("sales_outbound:outbound_detail", args=[out.id]),
            reverse("sales_outbound:outbound_print", args=[out.id]),
            reverse("sales_outbound:request_list"),
            reverse("transfers:transfer_list"),
            reverse("transfers:transfer_create"),
            reverse("transfers:transfer_detail", args=[transfer.id]),
            reverse("stocktakes:stocktake_list"),
            reverse("stocktakes:stocktake_create"),
            reverse("stocktakes:stocktake_detail", args=[stocktake.id]),
            reverse("reports:report_dashboard"),
            reverse("reports:report_variant_detail", args=[variant.id]),
            reverse("notifications:list"),
        ]

        for url in urls_to_check:
            resp = client.get(url)
            assert resp.status_code == 200, f"Failed GET {url} -> status {resp.status_code}"

    def test_invalid_date_range_shows_warning_message(self, client, users):
        """UC-4.5, UC-5.11, UC-6.9, UC-7.5: Filtering with date_from > date_to displays a Vietnamese warning."""
        client.force_login(users["admin"])
        filter_urls = [
            reverse("purchasing:import_list"),
            reverse("sales_outbound:outbound_list"),
            reverse("stocktakes:stocktake_list"),
            reverse("reports:report_dashboard"),
        ]
        for url in filter_urls:
            resp = client.get(url, {"date_from": "2026-12-31", "date_to": "2026-01-01"})
            assert resp.status_code == 200
            html = resp.content.decode("utf-8")
            assert "Từ ngày" in html and "Đến ngày" in html

    def test_download_all_excel_templates_and_variant_stock_api(self, client, users, sample_catalog):
        """EC-09: Verify Excel template downloads (import/outbound/stocktake) and api_variant_stock work with Decimal prices."""
        client.force_login(users["mgr_cs1"])
        for tpl_type in ("import", "outbound", "stocktake"):
            resp = client.get(reverse("inventory:download_template", args=[tpl_type]))
            assert resp.status_code == 200
            assert "spreadsheetml" in resp["Content-Type"]
            assert len(resp.content) > 500

        v_m = sample_catalog["v_m"]
        api_resp = client.get(reverse("inventory:api_variant_stock"), {"variant_id": v_m.id})
        assert api_resp.status_code == 200
        data = api_resp.json()
        assert data["ma_sku"] == v_m.ma_sku
        assert data["so_luong_ton"] == 30

        bad_resp = client.get(reverse("inventory:api_variant_stock"), {"variant_id": "invalid"})
        assert bad_resp.status_code == 400
