"""Selectors for Sales Outbound Requests & Receipts (UC-5.4 to UC-5.8)."""
from django.db.models import Q, QuerySet
from apps.accounts.models import User
from apps.accounts.permissions import scope_queryset_by_branch
from apps.branches.models import CoSo
from apps.sales_outbound.models import PhieuXuatHangBan, YeuCauXuatHang


def get_filtered_outbound_receipts(
    *,
    user: User,
    selected_branch: CoSo | None = None,
    search_query: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
) -> QuerySet[PhieuXuatHangBan]:
    qs = PhieuXuatHangBan.objects.select_related(
        "co_so", "nguoi_tao", "nguoi_ghi_nhan", "yeu_cau_xuat"
    ).prefetch_related("lines", "lines__bien_the")
    qs = scope_queryset_by_branch(qs, user, branch_field="co_so", selected_branch=selected_branch)

    if search_query:
        q = search_query.strip()
        qs = qs.filter(
            Q(ma_phieu_xuat_hang_ban__icontains=q)
            | Q(ten_khach_hang__icontains=q)
            | Q(sdt__icontains=q)
            | Q(ghi_chu__icontains=q)
        )
    if status:
        qs = qs.filter(trang_thai=status)
    if date_from and date_to and date_from > date_to:
        return qs.none()
    if date_from:
        qs = qs.filter(ngay_xuat__date__gte=date_from)
    if date_to:
        qs = qs.filter(ngay_xuat__date__lte=date_to)
    return qs.order_by("-ngay_xuat", "-id")


def get_filtered_outbound_requests(
    *,
    user: User,
    selected_branch: CoSo | None = None,
    status: str = "",
    search_query: str = "",
) -> QuerySet[YeuCauXuatHang]:
    qs = YeuCauXuatHang.objects.select_related(
        "co_so", "nguoi_yeu_cau", "nguoi_xu_ly"
    ).prefetch_related("lines", "lines__bien_the", "lines__bien_the__san_pham")
    qs = scope_queryset_by_branch(qs, user, branch_field="co_so", selected_branch=selected_branch)
    if status:
        qs = qs.filter(trang_thai=status)
    if search_query:
        q = search_query.strip()
        qs = qs.filter(Q(ma_yeu_cau__icontains=q) | Q(ten_khach_hang__icontains=q) | Q(sdt_khach_hang__icontains=q))
    return qs.order_by("-ngay_yeu_cau", "-id")
