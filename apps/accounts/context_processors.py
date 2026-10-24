"""Global template context processor for branch selection and notifications."""
from apps.accounts.permissions import get_effective_branch
from apps.branches.models import CoSo


def oldschool_global_context(request):
    system_branches = CoSo.objects.all().order_by("ma_co_so")

    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {
            "global_system_branches": system_branches,
        }

    user = request.user
    active_branch = get_effective_branch(request, allow_all_for_admin=True)
    all_branches = system_branches if user.is_business_admin else (
        CoSo.objects.filter(id=user.branch_id) if user.branch_id else CoSo.objects.none()
    )

    unread_count = 0
    recent_notifications = []
    try:
        from apps.notifications.views import _get_user_notifications_queryset

        notif_qs = _get_user_notifications_queryset(user, active_branch=active_branch).order_by("-created_at")
        unread_count = notif_qs.filter(da_doc=False).count()
        recent_notifications = list(notif_qs[:8])
    except Exception:
        pass

    return {
        "global_active_branch": active_branch,
        "global_all_branches": all_branches,
        "global_system_branches": system_branches,
        "global_unread_notifications_count": unread_count,
        "global_recent_notifications": recent_notifications,
    }
