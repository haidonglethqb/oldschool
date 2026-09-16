"""Centralized RBAC and branch-isolation policies for Old School."""
from functools import wraps
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from apps.accounts.models import User
from apps.branches.models import CoSo


def get_effective_branch(request, allow_all_for_admin: bool = True):
    """
    Determine the active branch for the current request.
    - MANAGER / STAFF: Always locked to `request.user.branch`.
    - ADMIN: Uses `?branch=<id|code>` or session `selected_branch_id`.
      If `allow_all_for_admin` is False and no branch is selected, defaults to Central Warehouse (CS1).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None

    if user.role in {User.Role.MANAGER, User.Role.STAFF}:
        return user.branch

    # ADMIN role
    branch_param = request.GET.get("branch") or request.GET.get("co_so")
    if branch_param:
        if branch_param.upper() == "ALL" and allow_all_for_admin:
            request.session["selected_branch_id"] = "ALL"
            return None
        branch = (
            CoSo.objects.filter(id=branch_param).first()
            if str(branch_param).isdigit()
            else CoSo.objects.filter(ma_co_so__iexact=branch_param).first()
        )
        if branch:
            request.session["selected_branch_id"] = branch.id
            return branch

    session_branch = request.session.get("selected_branch_id")
    if session_branch == "ALL" and allow_all_for_admin:
        return None
    if session_branch and str(session_branch).isdigit():
        branch = CoSo.objects.filter(id=int(session_branch)).first()
        if branch:
            return branch

    if allow_all_for_admin:
        return None
    return CoSo.get_central_warehouse() or CoSo.objects.first()


def assert_roles(user, *allowed_roles):
    """Ensure the user is authenticated, active, and has one of the allowed business roles."""
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Bạn cần đăng nhập bằng tài khoản hợp lệ để thực hiện thao tác này.")
    if user.role not in allowed_roles:
        raise PermissionDenied("Bạn không có quyền thực hiện chức năng này.")


def assert_branch_access(user, branch_or_id):
    """
    Ensure the user is authorized to access or mutate data belonging to `branch_or_id`.
    Never trust browser-supplied branch IDs for Manager or Staff users.
    """
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Phiên đăng nhập không hợp lệ.")
    if user.role == User.Role.ADMIN:
        return True
    branch_id = branch_or_id.id if hasattr(branch_or_id, "id") else int(branch_or_id)
    if not user.branch_id or user.branch_id != branch_id:
        raise PermissionDenied("Bạn không có quyền truy cập hoặc thao tác dữ liệu của cơ sở khác.")
    return True


def is_central_warehouse(branch: CoSo | None) -> bool:
    if not branch:
        return False
    if branch.is_central_warehouse:
        return True
    cw_code = getattr(settings, "CENTRAL_WAREHOUSE_CODE", "CS1")
    return branch.ma_co_so.upper() == cw_code.upper()


def assert_can_manage_imports(user, branch: CoSo | None = None):
    """
    Import receipts are created/managed by CS1 (Kho tổng) Manager (or Admin).
    """
    assert_roles(user, User.Role.ADMIN, User.Role.MANAGER)
    if user.role == User.Role.MANAGER:
        if not is_central_warehouse(user.branch):
            raise PermissionDenied("Chỉ Quản lý Cơ sở 1 (Kho tổng) mới có quyền lập và quản lý phiếu nhập kho.")
        if branch and branch.id != user.branch_id:
            raise PermissionDenied("Quản lý Kho tổng chỉ được phép thao tác phiếu nhập thuộc Kho tổng.")


def scope_queryset_by_branch(queryset, user, branch_field: str = "co_so", selected_branch: CoSo | None = None):
    """Filter a queryset according to the user's branch authorization."""
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.role == User.Role.ADMIN:
        if selected_branch is not None:
            return queryset.filter(**{branch_field: selected_branch})
        return queryset
    if not user.branch_id:
        return queryset.none()
    return queryset.filter(**{f"{branch_field}_id": user.branch_id})


def role_required(*allowed_roles):
    """View decorator enforcing login and allowed business roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not request.user.is_active:
                raise PermissionDenied("Tài khoản đã bị vô hiệu hóa.")
            if allowed_roles and request.user.role not in allowed_roles:
                raise PermissionDenied("Bạn không có quyền truy cập trang này.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
