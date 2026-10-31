"""Business services for Product Catalogue and Variants (UC-3, UC-3.1 to UC-3.7)."""
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from apps.accounts.models import User
from apps.accounts.permissions import assert_roles
from apps.catalog.models import BienThe, SanPham
from apps.inventory.models import StockMovement, TonKho
from apps.inventory.services import ensure_variant_balances_across_branches
from apps.notifications.services import sync_low_stock_alert
from apps.purchasing.models import ChiTietPhieuNhapKho
from apps.sales_outbound.models import ChiTietPhieuXuatHangBan, ChiTietYeuCauXuatHang
from apps.stocktakes.models import ChiTietKiemKe
from apps.transfers.models import ChiTietPhieuDieuChuyen


def generate_sku(ma_san_pham: str, mau_sac: str, kich_co: str) -> str:
    import re
    from text_unidecode import unidecode

    clean_prod = re.sub(r"[^A-Z0-9]", "", unidecode(ma_san_pham).upper())
    clean_color = re.sub(r"[^A-Z0-9]", "", unidecode(mau_sac).upper())[:6] or "STD"
    clean_size = re.sub(r"[^A-Z0-9]", "", unidecode(kich_co).upper())[:4] or "FS"
    return f"{clean_prod}-{clean_color}-{clean_size}"


@transaction.atomic
def create_product_with_variants(
    *,
    actor: User,
    ma_san_pham: str,
    ten_hang_hoa: str,
    nhom_hang: str,
    don_vi_tinh: str = "Cái",
    don_gia_niem_yet: Decimal = Decimal("0"),
    ghi_chu: str = "",
    hinh_anh=None,
    trang_thai: str = SanPham.Status.ACTIVE,
    variants_data: list[dict] | None = None,
    min_threshold: int = 5,
) -> SanPham:
    """Create a product master and its SKU variants, initializing branch stock rows."""
    assert_roles(actor, User.Role.ADMIN, User.Role.MANAGER)

    clean_code = (ma_san_pham or "").strip().upper()
    if not clean_code:
        raise ValidationError({"ma_san_pham": "Mã hàng hóa không được để trống."})
    if SanPham.objects.filter(ma_san_pham__iexact=clean_code).exists():
        raise ValidationError({"ma_san_pham": f"Mã hàng hóa '{clean_code}' đã tồn tại trong hệ thống."})

    product = SanPham(
        ma_san_pham=clean_code,
        ten_hang_hoa=(ten_hang_hoa or "").strip(),
        nhom_hang=(nhom_hang or "").strip(),
        don_vi_tinh=(don_vi_tinh or "Cái").strip(),
        don_gia_niem_yet=Decimal(str(don_gia_niem_yet or 0)),
        ghi_chu=(ghi_chu or "").strip(),
        trang_thai=trang_thai or SanPham.Status.ACTIVE,
    )
    if hinh_anh:
        product.hinh_anh = hinh_anh
    product.full_clean()
    product.save()

    if not variants_data:
        variants_data = [
            {
                "ma_sku": f"{clean_code}-DEFAULT",
                "mau_sac": "Mặc định",
                "kich_co": "Freesize",
                "don_gia": product.don_gia_niem_yet,
            }
        ]

    for v_item in variants_data:
        mau = (v_item.get("mau_sac") or "Mặc định").strip()
        size = (v_item.get("kich_co") or "Freesize").strip().upper()
        sku = (v_item.get("ma_sku") or "").strip().upper() or generate_sku(clean_code, mau, size)
        price = Decimal(str(v_item.get("don_gia", product.don_gia_niem_yet)))
        threshold = int(v_item.get("muc_ton_toi_thieu", min_threshold))

        if BienThe.objects.filter(ma_sku__iexact=sku).exists():
            raise ValidationError(f"Mã SKU '{sku}' đã tồn tại trong hệ thống.")
        if BienThe.objects.filter(san_pham=product, mau_sac__iexact=mau, kich_co__iexact=size).exists():
            raise ValidationError(f"Biến thể màu '{mau}' - size '{size}' đã bị trùng lặp trong sản phẩm này.")

        variant = BienThe(
            san_pham=product,
            ma_sku=sku,
            mau_sac=mau,
            kich_co=size,
            don_gia=price,
            trang_thai=BienThe.Status.ACTIVE,
        )
        variant.full_clean()
        variant.save()
        ensure_variant_balances_across_branches(variant, min_threshold=threshold)

    return product


@transaction.atomic
def update_product_and_variants(
    *,
    actor: User,
    product: SanPham,
    ten_hang_hoa: str,
    nhom_hang: str,
    don_vi_tinh: str,
    don_gia_niem_yet: Decimal,
    ghi_chu: str = "",
    hinh_anh=None,
    trang_thai: str | None = None,
    variants_data: list[dict] | None = None,
    min_threshold: int | None = None,
) -> SanPham:
    """Update product fields and add/update its variants (UC-3.5)."""
    assert_roles(actor, User.Role.ADMIN, User.Role.MANAGER)

    product.ten_hang_hoa = (ten_hang_hoa or "").strip()
    product.nhom_hang = (nhom_hang or "").strip()
    product.don_vi_tinh = (don_vi_tinh or "Cái").strip()
    product.don_gia_niem_yet = Decimal(str(don_gia_niem_yet))
    product.ghi_chu = (ghi_chu or "").strip()
    if trang_thai in dict(SanPham.Status.choices):
        product.trang_thai = trang_thai
    if hinh_anh:
        product.hinh_anh = hinh_anh
    product.full_clean()
    product.save()

    if variants_data is not None:
        for v_item in variants_data:
            vid = v_item.get("id")
            mau = (v_item.get("mau_sac") or "").strip()
            size = (v_item.get("kich_co") or "").strip().upper()
            if not mau or not size:
                continue
            price = Decimal(str(v_item.get("don_gia", product.don_gia_niem_yet)))
            sku = (v_item.get("ma_sku") or "").strip().upper() or generate_sku(product.ma_san_pham, mau, size)
            threshold = (
                v_item.get("muc_ton_toi_thieu")
                if v_item.get("muc_ton_toi_thieu") is not None
                else v_item.get("min_threshold", min_threshold)
            )

            if vid:
                if BienThe.objects.exclude(pk=vid).filter(ma_sku__iexact=sku).exists():
                    raise ValidationError(f"Mã SKU '{sku}' đã tồn tại trong hệ thống.")
                if BienThe.objects.exclude(pk=vid).filter(san_pham=product, mau_sac__iexact=mau, kich_co__iexact=size).exists():
                    raise ValidationError(f"Biến thể màu '{mau}' - size '{size}' đã bị trùng lặp trong sản phẩm này.")
                variant = BienThe.objects.get(pk=vid, san_pham=product)
                variant.ma_sku = sku
                variant.mau_sac = mau
                variant.kich_co = size
                variant.don_gia = price
                if v_item.get("trang_thai") in dict(BienThe.Status.choices):
                    variant.trang_thai = v_item["trang_thai"]
                variant.full_clean()
                variant.save()
                if threshold is not None:
                    new_th = max(0, int(threshold))
                    TonKho.objects.filter(bien_the=variant).update(muc_ton_toi_thieu=new_th)
                    for tk in TonKho.objects.select_related("co_so", "bien_the__san_pham").filter(bien_the=variant):
                        sync_low_stock_alert(tk)
            else:
                if BienThe.objects.filter(ma_sku__iexact=sku).exists():
                    raise ValidationError(f"Mã SKU '{sku}' đã tồn tại.")
                if BienThe.objects.filter(san_pham=product, mau_sac__iexact=mau, kich_co__iexact=size).exists():
                    raise ValidationError(f"Biến thể màu '{mau}' - size '{size}' đã bị trùng lặp trong sản phẩm này.")
                variant = BienThe(
                    san_pham=product,
                    ma_sku=sku,
                    mau_sac=mau,
                    kich_co=size,
                    don_gia=price,
                    trang_thai=BienThe.Status.ACTIVE,
                )
                variant.full_clean()
                variant.save()
                ensure_variant_balances_across_branches(
                    variant,
                    min_threshold=int(threshold) if threshold is not None else 5,
                )

    elif min_threshold is not None:
        new_th = max(0, int(min_threshold))
        TonKho.objects.filter(bien_the__san_pham=product).update(muc_ton_toi_thieu=new_th)
        for tk in TonKho.objects.select_related("co_so", "bien_the__san_pham").filter(bien_the__san_pham=product):
            sync_low_stock_alert(tk)

    return product


def has_product_transactions(product: SanPham) -> bool:
    """Return True if any variant of `product` has historical transactions or positive stock."""
    variant_ids = list(product.variants.values_list("id", flat=True))
    if not variant_ids:
        return False
    return (
        ChiTietPhieuNhapKho.objects.filter(bien_the_id__in=variant_ids).exists()
        or ChiTietPhieuXuatHangBan.objects.filter(bien_the_id__in=variant_ids).exists()
        or ChiTietYeuCauXuatHang.objects.filter(bien_the_id__in=variant_ids).exists()
        or ChiTietPhieuDieuChuyen.objects.filter(bien_the_id__in=variant_ids).exists()
        or ChiTietKiemKe.objects.filter(bien_the_id__in=variant_ids).exists()
        or StockMovement.objects.filter(bien_the_id__in=variant_ids).exists()
        or TonKho.objects.filter(bien_the_id__in=variant_ids, so_luong__gt=0).exists()
    )


@transaction.atomic
def delete_product(*, actor: User, product: SanPham) -> None:
    """
    Delete a product only if it has no associated transactions (UC-3.4).
    Otherwise raise a clear Vietnamese ValidationError per UC-3.4 E1.
    """
    assert_roles(actor, User.Role.ADMIN, User.Role.MANAGER)
    if has_product_transactions(product):
        raise ValidationError(
            "Không thể xóa hàng hóa đã phát sinh giao dịch nhập/xuất hoặc đang có tồn kho. "
            "Vui lòng chuyển sang trạng thái 'Ngừng kinh doanh'."
        )
    TonKho.objects.filter(bien_the__san_pham=product).delete()
    product.variants.all().delete()
    product.delete()


@transaction.atomic
def toggle_product_business_status(*, actor: User, product: SanPham) -> SanPham:
    """Discontinue or reactivate a product without deleting historical records (UC-3)."""
    assert_roles(actor, User.Role.ADMIN, User.Role.MANAGER)
    if product.trang_thai == SanPham.Status.ACTIVE:
        product.trang_thai = SanPham.Status.DISCONTINUED
        product.variants.all().update(trang_thai=BienThe.Status.INACTIVE)
    else:
        product.trang_thai = SanPham.Status.ACTIVE
        product.variants.all().update(trang_thai=BienThe.Status.ACTIVE)
    product.save(update_fields=["trang_thai", "updated_at"])
    for tk in TonKho.objects.select_related("co_so", "bien_the__san_pham").filter(bien_the__san_pham=product):
        sync_low_stock_alert(tk)
    return product
