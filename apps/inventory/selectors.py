"""Selectors for querying stock balances and movements (UC-5.1)."""
from django.db.models import F, Q
from apps.accounts.models import User
from apps.branches.models import CoSo
from apps.inventory.models import StockStatus, TonKho


def list_stock_balances(
    *,
    user: User,
    branch: CoSo | None = None,
    query: str = "",
    nhom_hang: str = "",
    mau_sac: str = "",
    kich_co: str = "",
    stock_status: str = "",
    include_discontinued: bool = False,
):
    qs = TonKho.objects.select_related("co_so", "bien_the", "bien_the__san_pham")

    if user.role in {User.Role.MANAGER, User.Role.STAFF}:
        if branch is not None:
            qs = qs.filter(co_so=branch)
        elif user.branch_id:
            qs = qs.filter(co_so_id=user.branch_id)
    elif branch is not None:
        qs = qs.filter(co_so=branch)

    if not include_discontinued:
        qs = qs.filter(bien_the__san_pham__trang_thai="ACTIVE", bien_the__trang_thai="ACTIVE")

    if query:
        q = query.strip()
        qs = qs.filter(
            Q(bien_the__ma_sku__icontains=q)
            | Q(bien_the__san_pham__ma_san_pham__icontains=q)
            | Q(bien_the__san_pham__ten_hang_hoa__icontains=q)
            | Q(bien_the__san_pham__nhom_hang__icontains=q)
        )

    if nhom_hang:
        qs = qs.filter(bien_the__san_pham__nhom_hang__iexact=nhom_hang.strip())
    if mau_sac:
        qs = qs.filter(bien_the__mau_sac__iexact=mau_sac.strip())
    if kich_co:
        qs = qs.filter(bien_the__kich_co__iexact=kich_co.strip())

    if stock_status == StockStatus.OUT_OF_STOCK:
        qs = qs.filter(so_luong__lte=0)
    elif stock_status == StockStatus.LOW_STOCK:
        qs = qs.filter(so_luong__gt=0, so_luong__lte=F("muc_ton_toi_thieu"))
    elif stock_status == StockStatus.IN_STOCK:
        qs = qs.filter(so_luong__gt=F("muc_ton_toi_thieu"))

    return qs.order_by("bien_the__san_pham__ma_san_pham", "bien_the__ma_sku", "co_so__ma_co_so")
