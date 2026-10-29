"""Views for Stocktake / Inventory Count Management (UC-6.1 to UC-6.10)."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.accounts.models import User
from apps.accounts.permissions import assert_branch_access, get_effective_branch, role_required
from apps.catalog.models import BienThe
from apps.inventory.excel import parse_stocktake_excel
from apps.inventory.models import TonKho
from apps.stocktakes.forms import StocktakeHeaderForm
from apps.stocktakes.models import KiemKe
from apps.stocktakes.selectors import get_filtered_stocktakes
from apps.stocktakes.services import (
    StocktakeLineSpec,
    approve_stocktake,
    create_stocktake,
    delete_stocktake,
    generate_next_stocktake_code,
    reject_stocktake,
    update_stocktake,
)


def _get_branch_variants_for_stocktake(branch):
    variants = list(
        BienThe.objects.select_related("san_pham").filter(san_pham__trang_thai="ACTIVE", trang_thai="ACTIVE")
    )
    stock_map = {
        t.bien_the_id: t.so_luong
        for t in TonKho.objects.filter(co_so=branch, bien_the__in=variants)
    }
    for v in variants:
        v.system_qty = stock_map.get(v.id, 0)
    return variants


def _extract_stocktake_lines(request) -> list[StocktakeLineSpec]:
    vids = request.POST.getlist("line_variant_id")
    actuals = request.POST.getlist("line_so_luong_thuc_te")
    actions = request.POST.getlist("line_xu_ly")
    notes = request.POST.getlist("line_ghi_chu")
    specs = []
    for idx, vid in enumerate(vids):
        if not str(vid).strip():
            continue
        try:
            actual_val = int(actuals[idx]) if idx < len(actuals) else 0
            specs.append(
                StocktakeLineSpec(
                    variant_id=int(vid),
                    so_luong_thuc_te=actual_val,
                    xu_ly=actions[idx] if idx < len(actions) else "",
                    ghi_chu=notes[idx] if idx < len(notes) else "",
                )
            )
        except ValueError as exc:
            raise ValidationError(f"Số lượng thực tế tại dòng {idx + 1} không hợp lệ.") from exc
    return specs


def _extract_initial_stocktake_lines(request):
    vids = request.POST.getlist("line_variant_id")
    actuals = request.POST.getlist("line_so_luong_thuc_te")
    actions = request.POST.getlist("line_xu_ly")
    notes = request.POST.getlist("line_ghi_chu")
    lines = []
    for idx, vid in enumerate(vids):
        if not str(vid).strip():
            continue
        try:
            vid_val = int(vid)
        except ValueError:
            vid_val = vid
        lines.append({
            "variant_id": vid_val,
            "so_luong_thuc_te": actuals[idx] if idx < len(actuals) else "",
            "xu_ly": actions[idx] if idx < len(actions) else "",
            "ghi_chu": notes[idx] if idx < len(notes) else "",
        })
    return lines


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def stocktake_list_view(request):
    selected_branch = get_effective_branch(request, allow_all_for_admin=True)
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if date_from and date_to and date_from > date_to:
        messages.warning(
            request,
            "Khoảng thời gian lọc không hợp lệ: 'Từ ngày' không được lớn hơn 'Đến ngày'.",
        )

    stocktakes = get_filtered_stocktakes(
        user=request.user,
        selected_branch=selected_branch,
        search_query=search_query,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return render(
        request,
        "stocktakes/stocktake_list.html",
        {
            "stocktakes": stocktakes,
            "status_choices": KiemKe.Status.choices,
            "selected_branch": selected_branch,
            "filters": {
                "q": search_query,
                "status": status_filter,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def stocktake_detail_view(request, stocktake_id: int):
    stocktake = get_object_or_404(
        KiemKe.objects.select_related("co_so", "tao_boi", "duyet_boi", "tu_choi_boi")
        .prefetch_related("lines", "lines__bien_the", "lines__bien_the__san_pham"),
        pk=stocktake_id,
    )
    assert_branch_access(request.user, stocktake.co_so)
    return render(
        request,
        "stocktakes/stocktake_detail.html",
        {
            "stocktake": stocktake,
            "lines": stocktake.lines.all(),
            "summary": stocktake.summary_counts,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def stocktake_create_view(request):
    target_branch = get_effective_branch(request, allow_all_for_admin=False)
    assert_branch_access(request.user, target_branch)
    variants = _get_branch_variants_for_stocktake(target_branch)
    excel_preview = None
    initial_lines = []

    if request.method == "POST":
        action = request.POST.get("form_action", "submit")
        if action == "upload_excel":
            excel_preview = parse_stocktake_excel(request.FILES.get("excel_file"), target_branch)
            if excel_preview["valid"]:
                initial_lines = excel_preview["rows"]
                messages.success(
                    request,
                    f"Đã đọc và đối chiếu {len(initial_lines)} dòng kiểm kê từ file Excel. Vui lòng kiểm tra trước khi Lưu.",
                )
            else:
                for err in excel_preview["errors"][:5]:
                    messages.error(request, err)
            header_form = StocktakeHeaderForm(request.POST)
        else:
            header_form = StocktakeHeaderForm(request.POST)
            initial_lines = _extract_initial_stocktake_lines(request)
            if header_form.is_valid():
                try:
                    specs = _extract_stocktake_lines(request)
                    stocktake = create_stocktake(
                        actor=request.user,
                        co_so=target_branch,
                        ma_kiem_ke=header_form.cleaned_data["ma_kiem_ke"],
                        nguoi_kiem_ke=header_form.cleaned_data["nguoi_kiem_ke"],
                        muc_dich=header_form.cleaned_data["muc_dich"],
                        ghi_chu=header_form.cleaned_data["ghi_chu"],
                        line_specs=specs,
                    )
                    messages.success(
                        request,
                        f"Đã lưu biên bản kiểm kê {stocktake.ma_kiem_ke}." if request.user.role == User.Role.ADMIN else f"Đã tạo và gửi biên bản kiểm kê {stocktake.ma_kiem_ke} ({stocktake.get_trang_thai_display()}).",
                    )
                    return redirect("stocktakes:stocktake_detail", stocktake_id=stocktake.id)
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))
    else:
        header_form = StocktakeHeaderForm(
            initial={
                "ma_kiem_ke": generate_next_stocktake_code(target_branch),
                "nguoi_kiem_ke": request.user.display_name,
            }
        )

    return render(
        request,
        "stocktakes/stocktake_form.html",
        {
            "header_form": header_form,
            "target_branch": target_branch,
            "variants": variants,
            "excel_preview": excel_preview,
            "initial_lines": initial_lines,
            "is_edit": False,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def stocktake_update_view(request, stocktake_id: int):
    stocktake = get_object_or_404(
        KiemKe.objects.select_related("co_so").prefetch_related("lines", "lines__bien_the"),
        pk=stocktake_id,
    )
    assert_branch_access(request.user, stocktake.co_so)
    if not stocktake.is_editable:
        messages.error(request, "Biên bản kiểm kê đã được phê duyệt, không thể chỉnh sửa.")
        return redirect("stocktakes:stocktake_detail", stocktake_id=stocktake.id)

    variants = _get_branch_variants_for_stocktake(stocktake.co_so)
    initial_lines = [
        {
            "variant_id": line.bien_the_id,
            "ma_sku": line.bien_the.ma_sku,
            "ten_hang_hoa": line.bien_the.full_display_name,
            "so_luong_he_thong": line.so_luong_he_thong,
            "so_luong_thuc_te": line.so_luong_thuc_te,
            "chenh_lech": line.chenh_lech,
            "xu_ly": line.xu_ly,
            "ghi_chu": line.ghi_chu,
        }
        for line in stocktake.lines.all()
    ]

    if request.method == "POST":
        header_form = StocktakeHeaderForm(request.POST)
        initial_lines = _extract_initial_stocktake_lines(request)
        if header_form.is_valid():
            try:
                specs = _extract_stocktake_lines(request)
                update_stocktake(
                    actor=request.user,
                    stocktake=stocktake,
                    nguoi_kiem_ke=header_form.cleaned_data["nguoi_kiem_ke"],
                    muc_dich=header_form.cleaned_data["muc_dich"],
                    ghi_chu=header_form.cleaned_data["ghi_chu"],
                    line_specs=specs,
                )
                messages.success(request, f"Đã cập nhật biên bản kiểm kê {stocktake.ma_kiem_ke}.")
                return redirect("stocktakes:stocktake_detail", stocktake_id=stocktake.id)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
    else:
        header_form = StocktakeHeaderForm(
            initial={
                "ma_kiem_ke": stocktake.ma_kiem_ke,
                "nguoi_kiem_ke": stocktake.nguoi_kiem_ke,
                "muc_dich": stocktake.muc_dich,
                "ghi_chu": stocktake.ghi_chu,
            }
        )

    return render(
        request,
        "stocktakes/stocktake_form.html",
        {
            "header_form": header_form,
            "target_branch": stocktake.co_so,
            "variants": variants,
            "initial_lines": initial_lines,
            "stocktake": stocktake,
            "is_edit": True,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def stocktake_delete_view(request, stocktake_id: int):
    stocktake = get_object_or_404(KiemKe, pk=stocktake_id)
    try:
        code = delete_stocktake(actor=request.user, stocktake=stocktake)
        messages.success(request, f"Đã xóa biên bản kiểm kê {code}.")
        return redirect("stocktakes:stocktake_list")
    except (ValidationError, PermissionDenied) as exc:
        msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        messages.error(request, msg)
        return redirect("stocktakes:stocktake_detail", stocktake_id=stocktake.id)


@role_required(User.Role.ADMIN)
@require_POST
def stocktake_approve_view(request, stocktake_id: int):
    stocktake = get_object_or_404(KiemKe, pk=stocktake_id)
    try:
        approve_stocktake(actor=request.user, stocktake=stocktake)
        messages.success(
            request,
            f"Đã phê duyệt biên bản kiểm kê {stocktake.ma_kiem_ke} (Giữ nguyên tồn kho hệ thống theo quy định kiểm soát).",
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("stocktakes:stocktake_detail", stocktake_id=stocktake.id)


@role_required(User.Role.ADMIN)
@require_POST
def stocktake_reject_view(request, stocktake_id: int):
    stocktake = get_object_or_404(KiemKe, pk=stocktake_id)
    reason = request.POST.get("ly_do_tu_choi", "")
    try:
        reject_stocktake(actor=request.user, stocktake=stocktake, reason=reason)
        messages.warning(request, f"Đã từ chối biên bản kiểm kê {stocktake.ma_kiem_ke}.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("stocktakes:stocktake_detail", stocktake_id=stocktake.id)
