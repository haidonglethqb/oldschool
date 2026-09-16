"""Selectors for Interbranch Transfers (UC-5.3)."""
from django.db.models import Q, QuerySet
from apps.accounts.models import User
from apps.branches.models import CoSo
from apps.transfers.models import PhieuDieuChuyen


def get_filtered_transfers(
    *,
    user: User,
    selected_branch: CoSo | None = None,
    direction: str = "",
    status: str = "",
    search_query: str = "",
) -> QuerySet[PhieuDieuChuyen]:
    qs = PhieuDieuChuyen.objects.select_related(
        "co_so_xuat", "co_so_nhan", "nguoi_tao", "nguoi_xuat", "nguoi_nhan"
    ).prefetch_related("lines", "lines__bien_the", "lines__bien_the__san_pham")

    branch = user.branch if user.role != User.Role.ADMIN else selected_branch
    if branch:
        if direction == "outgoing":
            qs = qs.filter(co_so_xuat=branch)
        elif direction == "incoming":
            qs = qs.filter(co_so_nhan=branch)
        else:
            qs = qs.filter(Q(co_so_xuat=branch) | Q(co_so_nhan=branch))

    if status:
        qs = qs.filter(trang_thai=status)
    if search_query:
        q = search_query.strip()
        qs = qs.filter(
            Q(ma_phieu_dieu_chuyen__icontains=q)
            | Q(co_so_xuat__ten_co_so__icontains=q)
            | Q(co_so_nhan__ten_co_so__icontains=q)
            | Q(ly_do__icontains=q)
        )
    return qs.order_by("-created_at", "-id")
