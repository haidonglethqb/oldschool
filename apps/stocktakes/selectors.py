"""Selectors for Stocktake Records (UC-6.4 to UC-6.7)."""
from django.db.models import Q, QuerySet
from apps.accounts.models import User
from apps.accounts.permissions import scope_queryset_by_branch
from apps.branches.models import CoSo
from apps.stocktakes.models import KiemKe


def get_filtered_stocktakes(
    *,
    user: User,
    selected_branch: CoSo | None = None,
    search_query: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
) -> QuerySet[KiemKe]:
    qs = KiemKe.objects.select_related(
        "co_so", "tao_boi", "duyet_boi", "tu_choi_boi"
    ).prefetch_related("lines", "lines__bien_the")
    qs = scope_queryset_by_branch(qs, user, branch_field="co_so", selected_branch=selected_branch)

    if search_query:
        q = search_query.strip()
        qs = qs.filter(
            Q(ma_kiem_ke__icontains=q)
            | Q(nguoi_kiem_ke__icontains=q)
            | Q(muc_dich__icontains=q)
            | Q(ghi_chu__icontains=q)
        )
    if status:
        qs = qs.filter(trang_thai=status)
    if date_from and date_to and date_from > date_to:
        return qs.none()
    if date_from:
        qs = qs.filter(ngay_kiem__gte=date_from)
    if date_to:
        qs = qs.filter(ngay_kiem__lte=date_to)
    return qs.order_by("-thoi_gian_tao", "-id")
