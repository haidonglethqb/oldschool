"""Tests for Product Catalogue & Variant Stock Management (UC-3, UC-3.1 to UC-3.7)."""
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from apps.catalog.models import SanPham
from apps.catalog.services import (
    create_product_with_variants,
    delete_product,
    toggle_product_business_status,
    update_product_and_variants,
)


@pytest.mark.django_db
class TestCatalogModule:
    def test_create_update_and_filter_product(self, client, users, branches, sample_catalog):
        """UC-3.1, UC-3.3, UC-3.5, UC-3.6, UC-3.7: Create product, update variants, search and filter."""
        client.force_login(users["admin"])
        new_prod = create_product_with_variants(
            actor=users["admin"],
            ma_san_pham="SP999",
            ten_hang_hoa="Váy Midi Cổ Điển",
            nhom_hang="Váy nữ",
            don_vi_tinh="Cái",
            don_gia_niem_yet=Decimal("320000"),
            variants_data=[
                {"ma_sku": "SP999-KEM-S", "mau_sac": "Kem", "kich_co": "S", "don_gia": Decimal("320000")},
            ],
        )
        assert new_prod.variants.count() == 1

        update_product_and_variants(
            actor=users["admin"],
            product=new_prod,
            ten_hang_hoa="Váy Midi Cổ Điển Cao Cấp",
            nhom_hang="Váy nữ",
            don_vi_tinh="Cái",
            don_gia_niem_yet=Decimal("350000"),
        )
        new_prod.refresh_from_db()
        assert new_prod.ten_hang_hoa == "Váy Midi Cổ Điển Cao Cấp"

        # Search via view
        resp = client.get(reverse("catalog:product_list"), {"q": "SP999"})
        assert resp.status_code == 200
        assert "Váy Midi Cổ Điển Cao Cấp" in resp.content.decode("utf-8")

        # Delete product without transactions (UC-3.4)
        delete_product(actor=users["admin"], product=new_prod)
        assert not SanPham.objects.filter(ma_san_pham="SP999").exists()

    def test_cannot_delete_product_with_transactions(self, users, sample_catalog):
        """UC-3.4: Product with existing stock balance or movement history cannot be deleted."""
        with pytest.raises(ValidationError):
            delete_product(actor=users["admin"], product=sample_catalog["product"])

        # Can discontinue instead (UC-3)
        toggle_product_business_status(actor=users["admin"], product=sample_catalog["product"])
        sample_catalog["product"].refresh_from_db()
        assert sample_catalog["product"].trang_thai == SanPham.Status.DISCONTINUED
        assert all(v.trang_thai == "INACTIVE" for v in sample_catalog["product"].variants.all())

    def test_discontinued_variant_blocked_in_new_transactions(
        self, users, branches, supplier, sample_catalog
    ):
        """Edge Case: A discontinued SKU variant cannot be used in new import/outbound/transfer documents."""
        from apps.purchasing.services import ImportLineSpec, create_import_receipt

        v_l = sample_catalog["v_l"]
        v_l.trang_thai = "INACTIVE"
        v_l.save(update_fields=["trang_thai"])

        with pytest.raises(ValidationError):
            create_import_receipt(
                actor=users["mgr_cs1"],
                nha_cung_cap=supplier,
                line_specs=[ImportLineSpec(variant_id=v_l.id, so_luong=5, don_gia=Decimal("200000"))],
            )

    def test_product_image_display_and_clear(self, client, users, sample_catalog):
        """Verify product image shows up in detail and list views, and can be updated or cleared."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(users["admin"])
        prod = sample_catalog["product"]

        # Detail view without image has placeholder
        resp_no_img = client.get(reverse("catalog:product_detail", args=[prod.id]))
        assert resp_no_img.status_code == 200
        assert "Chưa có hình ảnh minh họa" in resp_no_img.content.decode("utf-8")

        # Upload image
        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
        )
        img_file = SimpleUploadedFile("test_prod.gif", small_gif, content_type="image/gif")

        update_product_and_variants(
            actor=users["admin"],
            product=prod,
            ten_hang_hoa=prod.ten_hang_hoa,
            nhom_hang=prod.nhom_hang,
            don_vi_tinh=prod.don_vi_tinh,
            don_gia_niem_yet=prod.don_gia_niem_yet,
            hinh_anh=img_file,
        )
        prod.refresh_from_db()
        assert prod.hinh_anh

        # Detail view now has image and modal
        resp_with_img = client.get(reverse("catalog:product_detail", args=[prod.id]))
        assert resp_with_img.status_code == 200
        content_str = resp_with_img.content.decode("utf-8")
        assert prod.hinh_anh.url in content_str
        assert "productImageModal" in content_str

        # List view now has image thumbnail and delete button
        resp_list = client.get(reverse("catalog:product_list"))
        assert resp_list.status_code == 200
        list_html = resp_list.content.decode("utf-8")
        assert prod.hinh_anh.url in list_html
        assert "openDeleteProductModal" in list_html
        assert "deleteProductModal" in list_html

        # Clear image
        update_product_and_variants(
            actor=users["admin"],
            product=prod,
            ten_hang_hoa=prod.ten_hang_hoa,
            nhom_hang=prod.nhom_hang,
            don_vi_tinh=prod.don_vi_tinh,
            don_gia_niem_yet=prod.don_gia_niem_yet,
            hinh_anh=False,
        )
        prod.refresh_from_db()
        assert not prod.hinh_anh

    def test_product_edit_view_image_upload_unlocalized_prices_and_clear(
        self, client, users, sample_catalog, settings, tmp_path
    ):
        """Regression: product_edit_view renders unlocalized numeric values and persists uploaded/replaced/cleared images."""
        import re
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.catalog.models import BienThe

        settings.MEDIA_ROOT = str(tmp_path)
        client.force_login(users["admin"])
        prod = sample_catalog["product"]

        # Add a >= 1,000,000 variant to verify multi-dot localization does not break HTML/POST
        BienThe.objects.create(
            san_pham=prod,
            ma_sku="SP001-BE-XL",
            mau_sac="Be",
            kich_co="XL",
            don_gia=Decimal("1250000"),
            trang_thai=BienThe.Status.ACTIVE,
        )

        edit_url = reverse("catalog:product_edit", args=[prod.id])
        resp_get = client.get(edit_url)
        assert resp_get.status_code == 200
        html = resp_get.content.decode("utf-8")

        rendered_prices = re.findall(r'name="variant_price\[\]" value="([^"]*)"', html)
        assert "450000" in rendered_prices
        assert "1250000" in rendered_prices
        assert "450.000" not in rendered_prices
        assert "1.250.000" not in rendered_prices

        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
        )
        variants = list(prod.variants.all())
        post_base = {
            "ma_san_pham": prod.ma_san_pham,
            "ten_hang_hoa": prod.ten_hang_hoa,
            "nhom_hang": prod.nhom_hang,
            "don_vi_tinh": prod.don_vi_tinh,
            "don_gia_niem_yet": "450000",
            "muc_ton_toi_thieu": "5",
            "trang_thai": prod.trang_thai,
            "ghi_chu": prod.ghi_chu,
            "variant_id[]": [str(v.id) for v in variants],
            "variant_sku[]": [v.ma_sku for v in variants],
            "variant_color[]": [v.mau_sac for v in variants],
            "variant_size[]": [v.kich_co for v in variants],
            "variant_price[]": [str(v.don_gia) for v in variants],
            "variant_threshold[]": ["5" for _ in variants],
        }

        # 1. Upload image via HTTP POST
        img_1 = SimpleUploadedFile("bomber_oldschool.gif", small_gif, content_type="image/gif")
        resp_post = client.post(edit_url, {**post_base, "hinh_anh": img_1})
        assert resp_post.status_code == 302
        assert resp_post.url == reverse("catalog:product_detail", args=[prod.id])

        prod.refresh_from_db()
        assert prod.hinh_anh
        assert "bomber_oldschool" in prod.hinh_anh.name
        assert (tmp_path / prod.hinh_anh.name).exists()
        assert BienThe.objects.get(ma_sku="SP001-DEN-M").don_gia == Decimal("450000")
        assert BienThe.objects.get(ma_sku="SP001-BE-XL").don_gia == Decimal("1250000")

        # Detail and list views render the uploaded image URL
        assert prod.hinh_anh.url in client.get(reverse("catalog:product_detail", args=[prod.id])).content.decode("utf-8")
        assert prod.hinh_anh.url in client.get(reverse("catalog:product_list")).content.decode("utf-8")

        # 2. Replace with a very long filename (> 130 chars)
        long_name = ("anh_san_pham_ao_khoac_bomber_oldschool_" * 4) + ".gif"
        img_long = SimpleUploadedFile(long_name, small_gif, content_type="image/gif")
        resp_replace = client.post(edit_url, {**post_base, "hinh_anh": img_long})
        assert resp_replace.status_code == 302
        prod.refresh_from_db()
        assert prod.hinh_anh
        assert (tmp_path / prod.hinh_anh.name).exists()

        # 3. Clear image via ClearableFileInput checkbox
        resp_clear = client.post(edit_url, {**post_base, "hinh_anh-clear": "on"})
        assert resp_clear.status_code == 302
        prod.refresh_from_db()
        assert not prod.hinh_anh

    def test_product_edit_view_error_states_and_rollback_badge(self, client, users, sample_catalog, settings, tmp_path):
        """Failed upload or atomic rollback shows field error and does not render fake saved-image badge."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        settings.MEDIA_ROOT = str(tmp_path)
        client.force_login(users["admin"])
        prod = sample_catalog["product"]
        edit_url = reverse("catalog:product_edit", args=[prod.id])
        variants = list(prod.variants.all())

        # Invalid image file should re-render with field error on hinh_anh
        bad_file = SimpleUploadedFile("not_an_image.txt", b"hello", content_type="text/plain")
        resp_bad = client.post(
            edit_url,
            {
                "ma_san_pham": prod.ma_san_pham,
                "ten_hang_hoa": prod.ten_hang_hoa,
                "nhom_hang": prod.nhom_hang,
                "don_vi_tinh": prod.don_vi_tinh,
                "don_gia_niem_yet": "450000",
                "muc_ton_toi_thieu": "5",
                "trang_thai": prod.trang_thai,
                "ghi_chu": prod.ghi_chu,
                "hinh_anh": bad_file,
                "variant_id[]": [str(v.id) for v in variants],
                "variant_sku[]": [v.ma_sku for v in variants],
                "variant_color[]": [v.mau_sac for v in variants],
                "variant_size[]": [v.kich_co for v in variants],
                "variant_price[]": [str(v.don_gia) for v in variants],
                "variant_threshold[]": ["5" for _ in variants],
            },
        )
        assert resp_bad.status_code == 200
        bad_html = resp_bad.content.decode("utf-8")
        assert "Đã có ảnh hiện tại" not in bad_html
        assert "text-danger" in bad_html

        # Valid image + variant ValidationError triggers rollback and must NOT show fake saved badge
        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
        )
        good_img = SimpleUploadedFile("rollback_test.gif", small_gif, content_type="image/gif")
        resp_rollback = client.post(
            edit_url,
            {
                "ma_san_pham": prod.ma_san_pham,
                "ten_hang_hoa": prod.ten_hang_hoa,
                "nhom_hang": prod.nhom_hang,
                "don_vi_tinh": prod.don_vi_tinh,
                "don_gia_niem_yet": "450000",
                "muc_ton_toi_thieu": "5",
                "trang_thai": prod.trang_thai,
                "ghi_chu": prod.ghi_chu,
                "hinh_anh": good_img,
                "variant_id[]": [str(v.id) for v in variants],
                "variant_sku[]": [v.ma_sku for v in variants],
                "variant_color[]": [v.mau_sac for v in variants],
                "variant_size[]": [v.kich_co for v in variants],
                "variant_price[]": ["-100" for _ in variants],
                "variant_threshold[]": ["5" for _ in variants],
            },
        )
        assert resp_rollback.status_code == 200
        prod.refresh_from_db()
        assert not prod.hinh_anh
        assert "Đã có ảnh hiện tại" not in resp_rollback.content.decode("utf-8")
