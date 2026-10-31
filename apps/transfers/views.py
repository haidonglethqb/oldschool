"""Views for Interbranch Transfers (UC-5.3)."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.accounts.models import User
from apps.accounts.permissions import get_effective_branch, role_required
from apps.branches.models import CoSo
from apps.catalog.models import BienThe
from apps.inventory.models import TonKho
from apps.transfers.forms import TransferCreateForm
from apps.transfers.models import PhieuDieuChuyen
from apps.transfers.selectors import get_filtered_transfers
from apps.transfers.services import (
    TransferRequestLineSpec,
    accept_transfer,
    create_transfer_request,
    dispatch_transfer,
    receive_transfer,
    reject_transfer,
)


def _extract_initial_transfer_lines(request):
    vids = request.POST.getlist("line_variant_id")
    qtys = request.POST.getlist("line_so_luong")
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
            "so_luong": qtys[idx] if idx < len(qtys) else "",
            "ghi_chu": notes[idx] if idx < len(notes) else "",
        })
    return lines


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def transfer_list_view(request):
    selected_branch = get_effective_branch(request, allow_all_for_admin=True)
    direction = request.GET.get("direction", "").strip()
    status_filter = request.GET.get("status", "").strip()
    search_query = request.GET.get("q", "").strip()

    transfers = get_filtered_transfers(
        user=request.user,
        selected_branch=selected_branch,
        direction=direction,
        status=status_filter,
        search_query=search_query,
    )
    return render(
        request,
        "transfers/transfer_list.html",
        {
            "transfers": transfers,
            "status_choices": PhieuDieuChuyen.Status.choices,
            "selected_branch": selected_branch,
            "filters": {
                "direction": direction,
                "status": status_filter,
                "q": search_query,
            },
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def transfer_detail_view(request, transfer_id: int):
    transfer = get_object_or_404(
        PhieuDieuChuyen.objects.select_related("co_so_xuat", "co_so_nhan", "nguoi_tao", "nguoi_xuat", "nguoi_nhan")
        .prefetch_related("lines", "lines__bien_the", "lines__bien_the__san_pham"),
        pk=transfer_id,
    )
    if request.user.role == User.Role.MANAGER and request.user.branch_id not in {
        transfer.co_so_xuat_id,
        transfer.co_so_nhan_id,
    }:
        raise PermissionDenied("Bạn không có quyền truy cập phiếu điều chuyển của hai cơ sở khác.")

    lines = list(transfer.lines.all())
    stock_map = {
        t.bien_the_id: t.so_luong
        for t in TonKho.objects.filter(co_so=transfer.co_so_xuat, bien_the_id__in=[l.bien_the_id for l in lines])
    }
    for line in lines:
        line.source_available_stock = stock_map.get(line.bien_the_id, 0)

    can_manage_source = request.user.role == User.Role.ADMIN or request.user.branch_id == transfer.co_so_xuat_id
    can_manage_dest = request.user.role == User.Role.ADMIN or request.user.branch_id == transfer.co_so_nhan_id

    return render(
        request,
        "transfers/transfer_detail.html",
        {
            "transfer": transfer,
            "lines": lines,
            "can_manage_source": can_manage_source,
            "can_manage_dest": can_manage_dest,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def transfer_create_view(request):
    user_branch = get_effective_branch(request, allow_all_for_admin=False)
    central_wh = CoSo.get_central_warehouse()
    default_dest = CoSo.objects.exclude(id=user_branch.id).first() if user_branch else None

    variants = list(
        BienThe.objects.select_related("san_pham").filter(san_pham__trang_thai="ACTIVE", trang_thai="ACTIVE")
    )
    # Build stock matrix by branch & variant for interactive display
    branch_stocks = {}
    for t in TonKho.objects.select_related("co_so").all():
        branch_stocks.setdefault(t.bien_the_id, {})[t.co_so.ma_co_so] = t.so_luong
    for v in variants:
        v.stock_by_branch = branch_stocks.get(v.id, {})

    initial_lines = []
    if request.method == "POST":
        form = TransferCreateForm(request.POST)
        initial_lines = _extract_initial_transfer_lines(request)
        if form.is_valid():
            vids = request.POST.getlist("line_variant_id")
            qtys = request.POST.getlist("line_so_luong")
            notes = request.POST.getlist("line_ghi_chu")
            specs = []
            try:
                for idx, vid in enumerate(vids):
                    if not str(vid).strip():
                        continue
                    specs.append(
                        TransferRequestLineSpec(
                            variant_id=int(vid),
                            so_luong_yeu_cau=int(qtys[idx]),
                            ghi_chu=notes[idx] if idx < len(notes) else "",
                        )
                    )
                transfer = create_transfer_request(
                    actor=request.user,
                    co_so_xuat=form.cleaned_data["co_so_xuat"],
                    co_so_nhan=form.cleaned_data["co_so_nhan"],
                    ma_phieu_dieu_chuyen=form.cleaned_data["ma_phieu_dieu_chuyen"],
                    ly_do=form.cleaned_data["ly_do"],
                    ghi_chu=form.cleaned_data["ghi_chu"],
                    line_specs=specs,
                )
                transfer_action = request.POST.get("transfer_action", "dispatch_now")
                if transfer_action == "dispatch_now" and (request.user.role == User.Role.ADMIN or (request.user.branch_id and request.user.branch_id == transfer.co_so_xuat_id)):
                    transfer = dispatch_transfer(actor=request.user, transfer=transfer)
                    messages.success(request, f"Đã lập phiếu và xuất điều chuyển {transfer.ma_phieu_dieu_chuyen} sang {transfer.co_so_nhan.ten_co_so} (Đã trừ tồn kho {transfer.co_so_xuat.ma_co_so}).")
                else:
                    messages.success(request, f"Đã tạo phiếu yêu cầu điều chuyển {transfer.ma_phieu_dieu_chuyen}.")
                return redirect("transfers:transfer_detail", transfer_id=transfer.id)
            except (ValueError, ValidationError, PermissionDenied) as exc:
                msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
                messages.error(request, msg)
    else:
        form = TransferCreateForm(
            initial={
                "co_so_xuat": user_branch.id if user_branch else None,
                "co_so_nhan": default_dest.id if default_dest else None,
            }
        )

    return render(
        request,
        "transfers/transfer_form.html",
        {
            "form": form,
            "variants": variants,
            "branches": CoSo.objects.all(),
            "initial_lines": initial_lines,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def transfer_accept_view(request, transfer_id: int):
    transfer = get_object_or_404(PhieuDieuChuyen, pk=transfer_id)
    try:
        accept_transfer(actor=request.user, transfer=transfer)
        messages.success(request, f"Đã chấp nhận yêu cầu điều chuyển {transfer.ma_phieu_dieu_chuyen}.")
    except (ValidationError, PermissionDenied) as exc:
        msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        messages.error(request, msg)
    return redirect("transfers:transfer_detail", transfer_id=transfer.id)


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def transfer_reject_view(request, transfer_id: int):
    transfer = get_object_or_404(PhieuDieuChuyen, pk=transfer_id)
    reason = request.POST.get("reason", "Cơ sở xuất hiện không đủ tồn kho để điều chuyển.")
    try:
        reject_transfer(actor=request.user, transfer=transfer, reason=reason)
        messages.warning(request, f"Đã từ chối phiếu điều chuyển {transfer.ma_phieu_dieu_chuyen}.")
    except (ValidationError, PermissionDenied) as exc:
        msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        messages.error(request, msg)
    return redirect("transfers:transfer_detail", transfer_id=transfer.id)


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def transfer_dispatch_view(request, transfer_id: int):
    transfer = get_object_or_404(PhieuDieuChuyen.objects.prefetch_related("lines"), pk=transfer_id)
    dispatched_quantities = {}
    for line in transfer.lines.all():
        raw_val = request.POST.get(f"dispatch_qty_{line.id}")
        if raw_val is not None and str(raw_val).strip() != "":
            try:
                dispatched_quantities[line.id] = int(raw_val)
            except ValueError:
                messages.error(request, "Số lượng thực xuất không hợp lệ.")
                return redirect("transfers:transfer_detail", transfer_id=transfer.id)

    try:
        dispatch_transfer(actor=request.user, transfer=transfer, dispatched_quantities=dispatched_quantities)
        messages.success(
            request,
            f"Đã xác nhận xuất điều chuyển {transfer.ma_phieu_dieu_chuyen}. Đã trừ tồn kho tại {transfer.co_so_xuat.ten_co_so}.",
        )
    except (ValidationError, PermissionDenied) as exc:
        msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        messages.error(request, msg)
    return redirect("transfers:transfer_detail", transfer_id=transfer.id)


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def transfer_receive_view(request, transfer_id: int):
    transfer = get_object_or_404(PhieuDieuChuyen.objects.prefetch_related("lines"), pk=transfer_id)
    received_quantities = {}
    for line in transfer.lines.all():
        raw_val = request.POST.get(f"receive_qty_{line.id}")
        if raw_val is not None and str(raw_val).strip() != "":
            try:
                received_quantities[line.id] = int(raw_val)
            except ValueError:
                messages.error(request, "Số lượng thực nhận không hợp lệ.")
                return redirect("transfers:transfer_detail", transfer_id=transfer.id)

    shortage_note = request.POST.get("ghi_chu_chenh_lech", "")
    try:
        receive_transfer(
            actor=request.user,
            transfer=transfer,
            received_quantities=received_quantities,
            shortage_note=shortage_note,
        )
        messages.success(
            request,
            f"Đã xác nhận nhận hàng điều chuyển {transfer.ma_phieu_dieu_chuyen} và cộng tồn kho tại {transfer.co_so_nhan.ten_co_so}.",
        )
    except (ValidationError, PermissionDenied) as exc:
        msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        messages.error(request, msg)
    return redirect("transfers:transfer_detail", transfer_id=transfer.id)
