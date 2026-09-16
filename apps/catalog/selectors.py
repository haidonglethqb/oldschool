"""Selectors for Product Catalogue with branch-scoped variant stock evaluation (UC-3.1, UC-3.6, UC-3.7)."""
from django.db.models import Prefetch, Q
from apps.accounts.models import User
from apps.branches.models import CoSo
from apps.catalog.models import BienThe, SanPham
from apps.inventory.models import StockStatus, TonKho


def evaluate_product_row(product: SanPham, active_branch: CoSo | None):
    """
    Attach computed stock total, variant breakdown, and branch stock status badge
    to a product instance for template rendering.
    """
    variants = list(product.variants.all())
    total_stock = 0
    has_out = False
    has_low = False
    has_in = False
    variant_rows = []

    for v in variants:
        balances = [
            b for b in v.stock_balances.all()
            if (active_branch is None or b.co_so_id == active_branch.id)
        ]
        v_qty = sum(b.so_luong for b in balances)
        v_min = max((b.muc_ton_toi_thieu for b in balances), default=5)
        total_stock += v_qty
        if v_qty <= 0:
            v_status = StockStatus.OUT_OF_STOCK
            v_label = "Hết hàng"
            v_badge = "os-badge-out-of-stock"
            has_out = True
        elif v_qty <= v_min:
            v_status = StockStatus.LOW_STOCK
            v_label = "Sắp hết hàng"
            v_badge = "os-badge-low-stock"
            has_low = True
        else:
            v_status = StockStatus.IN_STOCK
            v_label = "Còn hàng"
            v_badge = "os-badge-in-stock"
            has_in = True

        variant_rows.append(
            {
                "variant": v,
                "so_luong": v_qty,
                "muc_ton_toi_thieu": v_min,
                "stock_status": v_status,
                "stock_status_label": v_label,
                "stock_status_badge_class": v_badge,
            }
        )

    if not variants or total_stock <= 0:
        overall_status = StockStatus.OUT_OF_STOCK
        overall_label = "Hết hàng"
        overall_badge = "os-badge-out-of-stock"
    elif has_low or has_out:
        overall_status = StockStatus.LOW_STOCK
        overall_label = "Sắp hết hàng"
        overall_badge = "os-badge-low-stock"
    else:
        overall_status = StockStatus.IN_STOCK
        overall_label = "Còn hàng"
        overall_badge = "os-badge-in-stock"

    product.computed_total_stock = total_stock
    product.computed_stock_status = overall_status
    product.computed_stock_label = overall_label
    product.computed_stock_badge = overall_badge
    product.computed_variants = variant_rows
    return product


def list_catalog_products(
    *,
    user: User,
    active_branch: CoSo | None = None,
    ma_hang: str = "",
    ten_hang: str = "",
    q: str = "",
    nhom_hang: str = "",
    mau_sac: str = "",
    kich_co: str = "",
    tinh_trang: str = "",
    trang_thai_kd: str = "",
) -> list[SanPham]:
    qs = SanPham.objects.prefetch_related(
        Prefetch(
            "variants",
            queryset=BienThe.objects.prefetch_related(
                Prefetch("stock_balances", queryset=TonKho.objects.select_related("co_so"))
            ),
        )
    )

    if trang_thai_kd:
        qs = qs.filter(trang_thai=trang_thai_kd)

    if ma_hang:
        m = ma_hang.strip()
        qs = qs.filter(Q(ma_san_pham__icontains=m) | Q(variants__ma_sku__icontains=m))
    if ten_hang:
        qs = qs.filter(ten_hang_hoa__icontains=ten_hang.strip())
    if q:
        kw = q.strip()
        qs = qs.filter(
            Q(ma_san_pham__icontains=kw)
            | Q(ten_hang_hoa__icontains=kw)
            | Q(nhom_hang__icontains=kw)
            | Q(variants__ma_sku__icontains=kw)
        )
    if nhom_hang:
        qs = qs.filter(nhom_hang__iexact=nhom_hang.strip())
    if mau_sac:
        qs = qs.filter(variants__mau_sac__iexact=mau_sac.strip())
    if kich_co:
        qs = qs.filter(variants__kich_co__iexact=kich_co.strip())

    qs = qs.distinct().order_by("ma_san_pham")

    branch_scope = user.branch if user.role in {User.Role.MANAGER, User.Role.STAFF} else active_branch
    results = []
    for p in qs:
        evaluate_product_row(p, branch_scope)
        if tinh_trang:
            # Match either product overall status or any variant status at the branch
            matching_variant = any(vr["stock_status"] == tinh_trang for vr in p.computed_variants)
            if p.computed_stock_status != tinh_trang and not matching_variant:
                continue
        results.append(p)
    return results


def get_distinct_categories() -> list[str]:
    """Return sorted distinct product group names (`nhom_hang`)."""
    return list(
        SanPham.objects.exclude(nhom_hang="")
        .values_list("nhom_hang", flat=True)
        .distinct()
        .order_by("nhom_hang")
    )

