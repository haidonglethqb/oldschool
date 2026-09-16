from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from apps.accounts.forms import LoginForm
from apps.accounts.models import User
from apps.branches.models import CoSo

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def login_view(request):
    """Handle UC-1: Đăng nhập with role resolution and temporary lockout on repeated failures."""
    if request.user.is_authenticated:
        return redirect("catalog:product_list")

    form = LoginForm(request.POST or None)
    error_message = None

    if request.GET.get("expired") == "1":
        messages.warning(request, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.")

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            password = form.cleaned_data["password"]

            candidate = User.objects.filter(username__iexact=username).first()
            if candidate and candidate.is_temporarily_locked():
                remaining = int((candidate.locked_until - timezone.now()).total_seconds() // 60) + 1
                error_message = (
                    f"Tài khoản đã bị khóa tạm thời do nhập sai mật khẩu quá {MAX_FAILED_ATTEMPTS} lần. "
                    f"Vui lòng thử lại sau {remaining} phút."
                )
            elif candidate and not candidate.is_active:
                error_message = "Tài khoản của bạn đã ngừng hoạt động. Vui lòng liên hệ Chủ cửa hàng (Admin)."
            else:
                user = authenticate(request, username=candidate.username if candidate else username, password=password)
                if user is not None:
                    if user.failed_login_attempts > 0 or user.locked_until is not None:
                        user.failed_login_attempts = 0
                        user.locked_until = None
                        user.save(update_fields=["failed_login_attempts", "locked_until"])
                    login(request, user)
                    if user.branch_id:
                        request.session["selected_branch_id"] = user.branch_id
                    else:
                        request.session["selected_branch_id"] = "ALL"
                    messages.success(
                        request,
                        f"Xin chào {user.display_name}! Bạn đã đăng nhập với vai trò {user.role_badge_label}.",
                    )
                    next_url = request.POST.get("next") or request.GET.get("next")
                    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                        return redirect(next_url)
                    return redirect("catalog:product_list")
                else:
                    if candidate:
                        candidate.failed_login_attempts += 1
                        if candidate.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                            candidate.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
                            candidate.save(update_fields=["failed_login_attempts", "locked_until"])
                            error_message = (
                                f"Bạn đã nhập sai thông tin quá {MAX_FAILED_ATTEMPTS} lần cho phép. "
                                f"Tài khoản bị khóa tạm thời trong {LOCKOUT_MINUTES} phút."
                            )
                        else:
                            candidate.save(update_fields=["failed_login_attempts"])
                            error_message = "Sai mật khẩu hoặc tên đăng nhập, vui lòng thử lại."
                    else:
                        error_message = "Sai mật khẩu hoặc tên đăng nhập, vui lòng thử lại."
        else:
            error_message = "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu."

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
            "error_message": error_message,
            "next": request.GET.get("next", ""),
        },
    )


@login_required
def logout_view(request):
    """Handle UC-2: Đăng xuất with confirmation support."""
    if request.method == "POST":
        logout(request)
        messages.info(request, "Bạn đã đăng xuất khỏi hệ thống an toàn.")
        return redirect("accounts:login")
    return render(request, "accounts/logout_confirm.html")


@login_required
def switch_branch_view(request):
    """Allow ADMIN to switch branch context in the header selector; block non-admins."""
    if request.method != "POST":
        return redirect("catalog:product_list")

    target = request.POST.get("branch_id", "").strip()
    raw_next = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    next_url = (
        raw_next
        if url_has_allowed_host_and_scheme(raw_next, allowed_hosts={request.get_host()})
        else "/"
    )

    if request.user.role != User.Role.ADMIN:
        if target and str(request.user.branch_id) != target:
            raise PermissionDenied("Bạn chỉ được phép làm việc trong phạm vi cơ sở được phân công.")
        return redirect(next_url)

    if target.upper() == "ALL" or target == "":
        request.session["selected_branch_id"] = "ALL"
        messages.info(request, "Đã chuyển phạm vi xem sang: Tất cả cơ sở.")
    elif target.isdigit():
        branch = CoSo.objects.filter(id=int(target)).first()
        if branch:
            request.session["selected_branch_id"] = branch.id
            messages.info(request, f"Đã chuyển phạm vi xem sang: {branch.ten_co_so}.")
    return redirect(next_url)


def custom_permission_denied_view(request, exception=None):
    """Render a clear Vietnamese 403 Access Denied screen."""
    message = str(exception) if exception else "Bạn không có quyền truy cập vào chức năng hoặc dữ liệu của cơ sở này."
    return render(
        request,
        "403.html",
        {"error_message": message},
        status=403,
    )
