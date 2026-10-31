"""Views for Sales Outbound Management (UC-5.1, UC-5.2, UC-5.4 to UC-5.12)."""
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.accounts.models import User
from apps.accounts.permissions import assert_branch_access, get_effective_branch, role_required
from apps.catalog.models import BienThe
from apps.inventory.excel import parse_outbound_excel
from apps.inventory.models import TonKho
from apps.sales_outbound.forms import OutboundReceiptHeaderForm, OutboundRequestForm
from apps.sales_outbound.models import PhieuXuatHangBan, YeuCauXuatHang
from apps.sales_outbound.selectors import get_filtered_outbound_receipts, get_filtered_outbound_requests
from apps.sales_outbound.services import (
    OutboundReceiptLineSpec,
    OutboundRequestLineSpec,
    create_outbound_receipt,
    create_outbound_request,
    delete_outbound_receipt,
    finalize_outbound_receipt,
    generate_next_outbound_code,
    reject_outbound_request,
    update_outbound_receipt,
)


def _get_branch_variant_catalog(branch):
    variants = list(
        BienThe.objects.select_related("san_pham").filter(san_pham__trang_thai="ACTIVE", trang_thai="ACTIVE")
    )
    stock_map = {}
    if branch:
        stock_map = {
            t.bien_the_id: t.so_luong
            for t in TonKho.objects.filter(co_so=branch, bien_the__in=variants)
        }
    for v in variants:
        v.branch_stock_qty = stock_map.get(v.id, 0)
    return variants


def _extract_outbound_lines(request) -> list[OutboundReceiptLineSpec]:
    vids = request.POST.getlist("line_variant_id")
    qtys = request.POST.getlist("line_so_luong")
    prices = request.POST.getlist("line_don_gia")
    notes = request.POST.getlist("line_ghi_chu")
    specs = []
    for idx, vid in enumerate(vids):
        if not str(vid).strip():
            continue
        try:
            qty = int(qtys[idx]) if idx < len(qtys) else 0
            price_str = prices[idx] if idx < len(prices) else ""
            price = Decimal(str(price_str)) if str(price_str).strip() != "" else None
            note = notes[idx] if idx < len(notes) else ""
            specs.append(
                OutboundReceiptLineSpec(
                    variant_id=int(vid),
                    so_luong=qty,
                    don_gia=price,
                    ghi_chu=note,
                )
            )
        except (ValueError, InvalidOperation) as exc:
            raise ValidationError(f"Dữ liệu dòng hàng thứ {idx + 1} không hợp lệ.") from exc
    return specs


def _extract_initial_outbound_lines(request) -> list[dict]:
    vids = request.POST.getlist("line_variant_id")
    qtys = request.POST.getlist("line_so_luong")
    prices = request.POST.getlist("line_don_gia")
    notes = request.POST.getlist("line_ghi_chu")
    int_vids = [int(v) for v in vids if str(v).isdigit()]
    v_map = {v.id: v for v in BienThe.objects.select_related("san_pham").filter(id__in=int_vids)}
    lines = []
    for idx, vid in enumerate(vids):
        if not str(vid).strip():
            continue
        v_obj = v_map.get(int(vid)) if str(vid).isdigit() else None
        lines.append({
            "variant_id": int(vid) if str(vid).isdigit() else "",
            "ma_sku": v_obj.ma_sku if v_obj else "",
            "ten_hang_hoa": v_obj.full_display_name if v_obj else "",
            "so_luong": qtys[idx] if idx < len(qtys) else "1",
            "don_gia": prices[idx] if idx < len(prices) else (str(v_obj.don_gia) if v_obj else "0"),
            "ghi_chu": notes[idx] if idx < len(notes) else "",
        })
    return lines


@role_required(User.Role.ADMIN, User.Role.MANAGER, User.Role.STAFF)
def outbound_list_view(request):
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

    receipts = get_filtered_outbound_receipts(
        user=request.user,
        selected_branch=selected_branch,
        search_query=search_query,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
    pending_requests = get_filtered_outbound_requests(
        user=request.user,
        selected_branch=selected_branch,
        status=YeuCauXuatHang.Status.PENDING,
    )[:10]

    return render(
        request,
        "sales_outbound/outbound_list.html",
        {
            "receipts": receipts,
            "pending_requests": pending_requests,
            "status_choices": PhieuXuatHangBan.Status.choices,
            "selected_branch": selected_branch,
            "filters": {
                "q": search_query,
                "status": status_filter,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER, User.Role.STAFF)
def outbound_detail_view(request, receipt_id: int):
    receipt = get_object_or_404(
        PhieuXuatHangBan.objects.select_related("co_so", "nguoi_tao", "nguoi_ghi_nhan", "yeu_cau_xuat")
        .prefetch_related("lines", "lines__bien_the", "lines__bien_the__san_pham"),
        pk=receipt_id,
    )
    assert_branch_access(request.user, receipt.co_so)
    return render(
        request,
        "sales_outbound/outbound_detail.html",
        {
            "receipt": receipt,
            "lines": receipt.lines.all(),
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER, User.Role.STAFF)
def outbound_print_view(request, receipt_id: int):
    """Printable Sales Outbound Slip (UC-5.12)."""
    receipt = get_object_or_404(
        PhieuXuatHangBan.objects.select_related("co_so", "nguoi_tao", "nguoi_ghi_nhan")
        .prefetch_related("lines", "lines__bien_the", "lines__bien_the__san_pham"),
        pk=receipt_id,
    )
    assert_branch_access(request.user, receipt.co_so)
    if not receipt.is_printable:
        messages.error(request, "Chỉ có thể in phiếu xuất kho sau khi đã ghi nhận hoàn tất xuất kho.")
        return redirect("sales_outbound:outbound_detail", receipt_id=receipt.id)
    return render(request, "sales_outbound/outbound_print.html", {"receipt": receipt, "lines": receipt.lines.all()})


@role_required(User.Role.ADMIN, User.Role.MANAGER, User.Role.STAFF)
def outbound_create_view(request):
    target_branch = get_effective_branch(request, allow_all_for_admin=False)
    assert_branch_access(request.user, target_branch)
    variants = _get_branch_variant_catalog(target_branch)

    request_id = request.GET.get("from_request") or request.POST.get("from_request")
    source_request = None
    initial_lines = []
    excel_preview = None

    if request_id and str(request_id).isdigit():
        source_request = YeuCauXuatHang.objects.prefetch_related("lines", "lines__bien_the").filter(
            pk=int(request_id), co_so=target_branch
        ).first()
        if source_request and request.method == "GET":
            for rline in source_request.lines.all():
                initial_lines.append(
                    {
                        "variant_id": rline.bien_the_id,
                        "ma_sku": rline.bien_the.ma_sku,
                        "ten_hang_hoa": rline.bien_the.full_display_name,
                        "so_luong": rline.so_luong,
                        "don_gia": str(rline.bien_the.don_gia),
                        "ghi_chu": "",
                    }
                )

    if request.method == "POST":
        action = request.POST.get("form_action", "save")
        if action == "upload_excel":
            excel_preview = parse_outbound_excel(request.FILES.get("excel_file"), target_branch)
            if excel_preview["valid"]:
                initial_lines = excel_preview["rows"]
                messages.success(request, f"Đã đọc {len(initial_lines)} dòng hàng xuất từ file Excel.")
            else:
                for err in excel_preview["errors"][:5]:
                    messages.error(request, err)
            header_form = OutboundReceiptHeaderForm(request.POST)
        else:
            header_form = OutboundReceiptHeaderForm(request.POST)
            initial_lines = _extract_initial_outbound_lines(request)
            if header_form.is_valid():
                try:
                    specs = _extract_outbound_lines(request)
                    finalize_now = action == "save_and_finalize"
                    receipt = create_outbound_receipt(
                        actor=request.user,
                        co_so=target_branch,
                        ma_phieu_xuat_hang_ban=header_form.cleaned_data["ma_phieu_xuat_hang_ban"],
                        yeu_cau_xuat=source_request,
                        ten_khach_hang=header_form.cleaned_data["ten_khach_hang"],
                        sdt=header_form.cleaned_data["sdt"],
                        dia_chi=header_form.cleaned_data["dia_chi"],
                        phuong_thuc_giao=header_form.cleaned_data["phuong_thuc_giao"],
                        ghi_chu=header_form.cleaned_data["ghi_chu"],
                        line_specs=specs,
                        finalize_immediately=finalize_now,
                    )
                    msg = f"Đã tạo phiếu xuất hàng bán {receipt.ma_phieu_xuat_hang_ban}"
                    if finalize_now:
                        msg += " và ghi nhận trừ tồn kho thành công."
                    messages.success(request, msg)
                    return redirect("sales_outbound:outbound_detail", receipt_id=receipt.id)
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))
    else:
        initial_data = {
            "ma_phieu_xuat_hang_ban": generate_next_outbound_code(target_branch),
            "ten_khach_hang": source_request.ten_khach_hang if source_request else "Khách mua lẻ tại quầy",
            "sdt": (source_request.sdt_khach_hang if source_request and source_request.sdt_khach_hang else target_branch.sdt),
            "dia_chi": (source_request.dia_chi_giao if source_request and source_request.dia_chi_giao else target_branch.dia_chi),
            "phuong_thuc_giao": source_request.phuong_thuc_giao if source_request else PhieuXuatHangBan.DeliveryMethod.COUNTER,
            "ghi_chu": source_request.ghi_chu if source_request else "",
        }
        header_form = OutboundReceiptHeaderForm(initial=initial_data)

    return render(
        request,
        "sales_outbound/outbound_form.html",
        {
            "header_form": header_form,
            "target_branch": target_branch,
            "variants": variants,
            "initial_lines": initial_lines,
            "source_request": source_request,
            "excel_preview": excel_preview,
            "is_edit": False,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER, User.Role.STAFF)
def outbound_update_view(request, receipt_id: int):
    receipt = get_object_or_404(
        PhieuXuatHangBan.objects.select_related("co_so").prefetch_related("lines", "lines__bien_the"),
        pk=receipt_id,
    )
    assert_branch_access(request.user, receipt.co_so)
    if not receipt.is_editable:
        messages.error(request, "Phiếu xuất đã ghi nhận hoàn tất, không thể chỉnh sửa.")
        return redirect("sales_outbound:outbound_detail", receipt_id=receipt.id)

    variants = _get_branch_variant_catalog(receipt.co_so)
    initial_lines = [
        {
            "variant_id": line.bien_the_id,
            "ma_sku": line.bien_the.ma_sku,
            "ten_hang_hoa": line.bien_the.full_display_name,
            "so_luong": line.so_luong,
            "don_gia": str(line.don_gia),
            "ghi_chu": line.ghi_chu,
        }
        for line in receipt.lines.all()
    ]

    if request.method == "POST":
        header_form = OutboundReceiptHeaderForm(request.POST)
        initial_lines = _extract_initial_outbound_lines(request)
        if header_form.is_valid():
            try:
                specs = _extract_outbound_lines(request)
                update_outbound_receipt(
                    actor=request.user,
                    receipt=receipt,
                    ten_khach_hang=header_form.cleaned_data["ten_khach_hang"],
                    sdt=header_form.cleaned_data["sdt"],
                    dia_chi=header_form.cleaned_data["dia_chi"],
                    phuong_thuc_giao=header_form.cleaned_data["phuong_thuc_giao"],
                    ghi_chu=header_form.cleaned_data["ghi_chu"],
                    line_specs=specs,
                )
                if request.POST.get("form_action") == "save_and_finalize":
                    finalize_outbound_receipt(actor=request.user, receipt=receipt)
                    messages.success(request, f"Đã cập nhật và ghi nhận xuất kho phiếu {receipt.ma_phieu_xuat_hang_ban}.")
                else:
                    messages.success(request, f"Đã cập nhật phiếu xuất {receipt.ma_phieu_xuat_hang_ban}.")
                return redirect("sales_outbound:outbound_detail", receipt_id=receipt.id)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
    else:
        header_form = OutboundReceiptHeaderForm(
            initial={
                "ma_phieu_xuat_hang_ban": receipt.ma_phieu_xuat_hang_ban,
                "ten_khach_hang": receipt.ten_khach_hang,
                "sdt": receipt.sdt,
                "dia_chi": receipt.dia_chi,
                "phuong_thuc_giao": receipt.phuong_thuc_giao,
                "ghi_chu": receipt.ghi_chu,
            }
        )

    return render(
        request,
        "sales_outbound/outbound_form.html",
        {
            "header_form": header_form,
            "target_branch": receipt.co_so,
            "variants": variants,
            "initial_lines": initial_lines,
            "receipt": receipt,
            "is_edit": True,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER, User.Role.STAFF)
@require_POST
def outbound_finalize_view(request, receipt_id: int):
    receipt = get_object_or_404(PhieuXuatHangBan, pk=receipt_id)
    try:
        finalize_outbound_receipt(actor=request.user, receipt=receipt)
        messages.success(request, f"Đã ghi nhận xuất kho thành công cho phiếu {receipt.ma_phieu_xuat_hang_ban}.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("sales_outbound:outbound_detail", receipt_id=receipt.id)


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def outbound_delete_view(request, receipt_id: int):
    receipt = get_object_or_404(PhieuXuatHangBan, pk=receipt_id)
    try:
        code = delete_outbound_receipt(actor=request.user, receipt=receipt)
        messages.success(request, f"Đã xóa phiếu xuất hàng bán {code}.")
        return redirect("sales_outbound:outbound_list")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("sales_outbound:outbound_detail", receipt_id=receipt.id)


@role_required(User.Role.ADMIN, User.Role.MANAGER, User.Role.STAFF)
def request_list_create_view(request):
    """Staff submit counter requests; Admin and Managers view and process them."""
    if request.method == "POST" and request.user.role != User.Role.STAFF:
        raise PermissionDenied("Chỉ Nhân viên bán hàng được tạo yêu cầu xuất từ quầy.")

    target_branch = get_effective_branch(request, allow_all_for_admin=True)
    can_create_request = request.user.role == User.Role.STAFF
    variants = _get_branch_variant_catalog(target_branch) if can_create_request else []
    status_filter = request.GET.get("status", "").strip()

    if request.method == "POST":
        form = OutboundRequestForm(request.POST)
        if form.is_valid():
            vids = request.POST.getlist("line_variant_id")
            qtys = request.POST.getlist("line_so_luong")
            specs = []
            try:
                for idx, vid in enumerate(vids):
                    if not str(vid).strip():
                        continue
                    specs.append(OutboundRequestLineSpec(variant_id=int(vid), so_luong=int(qtys[idx])))
                ly_do = form.cleaned_data["ly_do_xuat"].strip()
                extra_note = form.cleaned_data.get("ghi_chu_them", "").strip()
                full_reason = f"{ly_do} | {extra_note}".strip(" |") if extra_note else ly_do
                req_obj = create_outbound_request(
                    actor=request.user,
                    co_so=target_branch,
                    ten_khach_hang="Xuất bổ sung quầy/kệ",
                    ghi_chu=full_reason,
                    line_specs=specs,
                )
                messages.success(request, f"Đã gửi yêu cầu xuất hàng bán {req_obj.ma_yeu_cau} tới Quản lý cơ sở.")
                return redirect("sales_outbound:request_list")
            except (ValueError, ValidationError) as exc:
                msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
                messages.error(request, msg)
    else:
        form = OutboundRequestForm() if can_create_request else None

    requests_qs = get_filtered_outbound_requests(
        user=request.user,
        selected_branch=target_branch,
        status=status_filter,
    )
    return render(
        request,
        "sales_outbound/request_list.html",
        {
            "requests": requests_qs,
            "form": form,
            "variants": variants,
            "target_branch": target_branch,
            "status_filter": status_filter,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def request_reject_view(request, request_id: int):
    req_obj = get_object_or_404(YeuCauXuatHang, pk=request_id)
    reason = request.POST.get("reason", "Thiếu tồn kho tại cơ sở, cần điều chuyển bổ sung.")
    try:
        reject_outbound_request(actor=request.user, request_obj=req_obj, reason=reason)
        messages.warning(request, f"Đã từ chối yêu cầu xuất {req_obj.ma_yeu_cau}.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("sales_outbound:request_list")
