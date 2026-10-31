from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from apps.accounts.permissions import get_effective_branch
from apps.inventory.models import TonKho
from apps.notifications.models import ThongBao


def _get_user_notifications_queryset(user, active_branch=None):
    qs = ThongBao.objects.select_related("co_so", "bien_the", "bien_the__san_pham")
    if user.is_business_admin:
        qs = qs.filter(Q(nguoi_nhan=user) | Q(nguoi_nhan__isnull=True))
        if active_branch:
            qs = qs.filter(Q(co_so=active_branch) | Q(co_so__isnull=True))
        return qs
    return qs.filter(Q(nguoi_nhan=user) | (Q(nguoi_nhan__isnull=True, co_so=user.branch)))


@login_required
def notification_list_view(request):
    """Display notifications and low-stock warning overview (UC-5.13 & Section C.II)."""
    active_branch = get_effective_branch(request, allow_all_for_admin=True)
    qs = _get_user_notifications_queryset(request.user, active_branch=active_branch)

    notif_type = request.GET.get("loai", "").strip()
    unread_only = request.GET.get("chua_doc", "").strip()
    if notif_type:
        qs = qs.filter(loai_thong_bao=notif_type)
    if unread_only == "1":
        qs = qs.filter(da_doc=False)

    # Low stock items in scope (active products & active variants only)
    low_stock_qs = TonKho.objects.select_related("co_so", "bien_the", "bien_the__san_pham").filter(
        bien_the__trang_thai="ACTIVE",
        bien_the__san_pham__trang_thai="ACTIVE",
    )
    if request.user.is_business_admin:
        if active_branch:
            low_stock_qs = low_stock_qs.filter(co_so=active_branch)
    else:
        low_stock_qs = low_stock_qs.filter(co_so=request.user.branch)

    low_stock_items = [
        item for item in low_stock_qs.order_by("so_luong", "bien_the__ma_sku") if item.so_luong <= item.muc_ton_toi_thieu
    ]

    return render(
        request,
        "notifications/notification_list.html",
        {
            "notifications": qs[:100],
            "low_stock_items": low_stock_items,
            "notif_types": ThongBao.NotificationType.choices,
            "selected_type": notif_type,
            "unread_only": unread_only,
        },
    )


@login_required
def mark_notification_read_view(request, pk: int):
    active_branch = get_effective_branch(request, allow_all_for_admin=True)
    qs = _get_user_notifications_queryset(request.user, active_branch=active_branch)
    notif = get_object_or_404(qs, pk=pk)
    if not notif.da_doc:
        notif.da_doc = True
        notif.save(update_fields=["da_doc"])
    if notif.target_url and url_has_allowed_host_and_scheme(
        url=notif.target_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(notif.target_url)
    return redirect("notifications:list")


@login_required
def mark_all_read_view(request):
    if request.method == "POST":
        active_branch = get_effective_branch(request, allow_all_for_admin=True)
        qs = _get_user_notifications_queryset(request.user, active_branch=active_branch)
        qs.filter(da_doc=False).update(da_doc=True)
        messages.success(request, "Đã đánh dấu tất cả thông báo là đã đọc.")
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
        url=referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect("notifications:list")
