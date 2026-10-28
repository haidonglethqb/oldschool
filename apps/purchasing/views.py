"""Views for Warehouse Import Management (UC-4.1 to UC-4.11)."""
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.accounts.models import User
from apps.accounts.permissions import assert_branch_access, assert_can_manage_imports, role_required
from apps.branches.models import CoSo
from apps.catalog.models import BienThe
from apps.inventory.excel import build_excel_response, parse_import_excel
from apps.purchasing.forms import ImportReceiptHeaderForm, SupplierForm
from apps.purchasing.models import NhaCungCap, PhieuNhapKho
from apps.purchasing.selectors import (
    get_all_suppliers,
    get_filtered_import_receipts,
    get_import_activity_summary,
)
from apps.purchasing.services import (
    ImportLineSpec,
    approve_import_receipt,
    confirm_supplier_return,
    propose_supplier_return,
    create_import_receipt,
    create_supplier,
    delete_import_receipt,
    generate_next_import_code,
    return_import_receipt,
    update_import_receipt,
)


def _extract_import_lines_from_post(request) -> list[ImportLineSpec]:
    variant_ids = request.POST.getlist("line_variant_id")
    quantities = request.POST.getlist("line_so_luong")
    prices = request.POST.getlist("line_don_gia")
    discounts = request.POST.getlist("line_chiet_khau")
    notes = request.POST.getlist("line_ghi_chu")

    specs = []
    for idx, vid in enumerate(variant_ids):
        if not str(vid).strip():
            continue
        try:
            qty = int(quantities[idx]) if idx < len(quantities) else 0
            price = Decimal(str(prices[idx] or "0")) if idx < len(prices) else Decimal("0")
            disc = Decimal(str(discounts[idx] or "0")) if idx < len(discounts) and discounts[idx] != "" else Decimal("0")
            note = notes[idx] if idx < len(notes) else ""
            specs.append(
                ImportLineSpec(
                    variant_id=int(vid),
                    so_luong=qty,
                    don_gia=price,
                    chiet_khau=disc,
                    ghi_chu=note,
                )
            )
        except (ValueError, InvalidOperation) as exc:
            raise ValidationError(f"Dữ liệu dòng hàng thứ {idx + 1} không hợp lệ.") from exc
    return specs


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def import_list_view(request):
    assert_can_manage_imports(request.user)
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    supplier_id = request.GET.get("supplier", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if date_from and date_to and date_from > date_to:
        messages.warning(
            request,
            "Khoảng thời gian lọc không hợp lệ: 'Từ ngày' không được lớn hơn 'Đến ngày'.",
        )

    receipts = get_filtered_import_receipts(
        search_query=search_query,
        status=status_filter,
        supplier_id=supplier_id,
        date_from=date_from,
        date_to=date_to,
    )
    summary = get_import_activity_summary(receipts)
    return render(
        request,
        "purchasing/import_list.html",
        {
            "receipts": receipts,
            "summary": summary,
            "suppliers": NhaCungCap.objects.all(),
            "status_choices": PhieuNhapKho.Status.choices,
            "filters": {
                "q": search_query,
                "status": status_filter,
                "supplier": supplier_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def import_detail_view(request, receipt_id: int):
    assert_can_manage_imports(request.user)
    receipt = get_object_or_404(
        PhieuNhapKho.objects.select_related("nha_cung_cap", "co_so_nhan", "nguoi_tao", "nguoi_duyet")
        .prefetch_related("lines", "lines__bien_the", "lines__bien_the__san_pham"),
        pk=receipt_id,
    )
    return render(
        request,
        "purchasing/import_detail.html",
        {
            "receipt": receipt,
            "lines": receipt.lines.all(),
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def import_create_view(request):
    assert_can_manage_imports(request.user)
    variants = BienThe.objects.select_related("san_pham").filter(san_pham__trang_thai="ACTIVE", trang_thai="ACTIVE")
    excel_preview = None
    initial_lines = []

    if request.method == "POST":
        action = request.POST.get("form_action", "submit")
        if action == "upload_excel":
            excel_preview = parse_import_excel(request.FILES.get("excel_file"))
            if excel_preview["valid"]:
                initial_lines = excel_preview["rows"]
                messages.success(request, f"Đã đọc thành công {len(initial_lines)} dòng hàng từ file Excel. Vui lòng kiểm tra và bấm Lưu phiếu.")
            else:
                for err in excel_preview["errors"][:5]:
                    messages.error(request, err)
            header_form = ImportReceiptHeaderForm(request.POST)
        else:
            header_form = ImportReceiptHeaderForm(request.POST)
            if header_form.is_valid():
                try:
                    line_specs = _extract_import_lines_from_post(request)
                    submit_flag = action != "save_draft"
                    receipt = create_import_receipt(
                        actor=request.user,
                        nha_cung_cap=header_form.cleaned_data["nha_cung_cap"],
                        ma_phieu_nhap_kho=header_form.cleaned_data["ma_phieu_nhap_kho"],
                        ly_do_nhap=header_form.cleaned_data["ly_do_nhap"],
                        ghi_chu=header_form.cleaned_data["ghi_chu"],
                        line_specs=line_specs,
                        submit_for_approval=submit_flag,
                    )
                    messages.success(
                        request,
                        f"Đã lưu và phê duyệt phiếu nhập kho {receipt.ma_phieu_nhap_kho} (Tồn kho đã được cập nhật)." if (submit_flag and request.user.role == User.Role.ADMIN and approve_import_receipt(receipt_id=receipt.id, admin_user=request.user)) else f"Đã tạo phiếu nhập kho {receipt.ma_phieu_nhap_kho} ({receipt.get_trang_thai_display()}).",
                    )
                    return redirect("purchasing:import_detail", receipt_id=receipt.id)
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))
    else:
        header_form = ImportReceiptHeaderForm(initial={"ma_phieu_nhap_kho": generate_next_import_code()})

    return render(
        request,
        "purchasing/import_form.html",
        {
            "header_form": header_form,
            "supplier_form": SupplierForm(),
            "variants": variants,
            "excel_preview": excel_preview,
            "initial_lines": initial_lines,
            "is_edit": False,
            "central_warehouse": CoSo.get_central_warehouse(),
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def import_update_view(request, receipt_id: int):
    assert_can_manage_imports(request.user)
    receipt = get_object_or_404(
        PhieuNhapKho.objects.select_related("nha_cung_cap", "co_so_nhan").prefetch_related("lines", "lines__bien_the"),
        pk=receipt_id,
    )
    if not receipt.is_editable:
        messages.error(request, "Phiếu nhập kho đã được phê duyệt, không thể chỉnh sửa.")
        return redirect("purchasing:import_detail", receipt_id=receipt.id)

    variants = BienThe.objects.select_related("san_pham").filter(san_pham__trang_thai="ACTIVE", trang_thai="ACTIVE")
    initial_lines = [
        {
            "variant_id": line.bien_the_id,
            "ma_sku": line.bien_the.ma_sku,
            "ten_hang_hoa": line.bien_the.full_display_name,
            "so_luong": line.so_luong,
            "don_gia": str(line.don_gia),
            "chiet_khau": str(line.chiet_khau),
            "thanh_tien": str(line.thanh_tien),
            "ghi_chu": line.ghi_chu,
        }
        for line in receipt.lines.all()
    ]

    if request.method == "POST":
        header_form = ImportReceiptHeaderForm(request.POST)
        if header_form.is_valid():
            try:
                line_specs = _extract_import_lines_from_post(request)
                submit_flag = request.POST.get("form_action", "submit") != "save_draft"
                update_import_receipt(
                    actor=request.user,
                    receipt=receipt,
                    nha_cung_cap=header_form.cleaned_data["nha_cung_cap"],
                    ly_do_nhap=header_form.cleaned_data["ly_do_nhap"],
                    ghi_chu=header_form.cleaned_data["ghi_chu"],
                    line_specs=line_specs,
                    submit_for_approval=submit_flag,
                )
                messages.success(request, f"Đã cập nhật phiếu nhập kho {receipt.ma_phieu_nhap_kho}.")
                return redirect("purchasing:import_detail", receipt_id=receipt.id)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
    else:
        header_form = ImportReceiptHeaderForm(
            initial={
                "ma_phieu_nhap_kho": receipt.ma_phieu_nhap_kho,
                "nha_cung_cap": receipt.nha_cung_cap_id,
                "ly_do_nhap": receipt.ly_do_nhap,
                "ghi_chu": receipt.ghi_chu,
            }
        )

    return render(
        request,
        "purchasing/import_form.html",
        {
            "header_form": header_form,
            "supplier_form": SupplierForm(),
            "variants": variants,
            "initial_lines": initial_lines,
            "receipt": receipt,
            "is_edit": True,
            "central_warehouse": receipt.co_so_nhan,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def import_delete_view(request, receipt_id: int):
    receipt = get_object_or_404(PhieuNhapKho, pk=receipt_id)
    try:
        code = delete_import_receipt(actor=request.user, receipt=receipt)
        messages.success(request, f"Đã xóa phiếu nhập kho {code}.")
        return redirect("purchasing:import_list")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("purchasing:import_detail", receipt_id=receipt.id)


@role_required(User.Role.ADMIN)
@require_POST
def import_approve_view(request, receipt_id: int):
    receipt = get_object_or_404(PhieuNhapKho, pk=receipt_id)
    try:
        approve_import_receipt(actor=request.user, receipt=receipt)
        messages.success(request, f"Đã phê duyệt phiếu nhập kho {receipt.ma_phieu_nhap_kho} và cộng tồn kho thành công.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("purchasing:import_detail", receipt_id=receipt.id)


@role_required(User.Role.ADMIN)
@require_POST
def import_return_view(request, receipt_id: int):
    receipt = get_object_or_404(PhieuNhapKho, pk=receipt_id)
    reason = request.POST.get("ly_do_tra_lai", "")
    try:
        return_import_receipt(actor=request.user, receipt=receipt, reason=reason)
        messages.warning(request, f"Đã trả lại phiếu nhập kho {receipt.ma_phieu_nhap_kho} để chỉnh sửa.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("purchasing:import_detail", receipt_id=receipt.id)


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def import_export_excel_view(request, receipt_id: int):
    assert_can_manage_imports(request.user)
    receipt = get_object_or_404(
        PhieuNhapKho.objects.select_related("nha_cung_cap", "co_so_nhan", "nguoi_tao", "nguoi_duyet")
        .prefetch_related("lines", "lines__bien_the", "lines__bien_the__san_pham"),
        pk=receipt_id,
    )
    headers = ["STT", "Mã SKU", "Tên hàng hóa", "Màu / Size", "ĐVT", "Số lượng", "Đơn giá (VNĐ)", "Chiết khấu (VNĐ)", "Thành tiền (VNĐ)", "Ghi chú"]
    rows = []
    for idx, line in enumerate(receipt.lines.all(), start=1):
        rows.append([
            idx,
            line.bien_the.ma_sku,
            line.bien_the.san_pham.ten_hang_hoa,
            f"{line.bien_the.mau_sac} / {line.bien_the.kich_co}",
            line.bien_the.san_pham.don_vi_tinh,
            line.so_luong,
            int(line.don_gia),
            int(line.chiet_khau),
            int(line.thanh_tien),
            line.ghi_chu,
        ])
    rows.append(["", "", "TỔNG CỘNG", "", "", receipt.total_quantity, "", "", int(receipt.tong_tien), ""])
    return build_excel_response(
        filename=f"{receipt.ma_phieu_nhap_kho}.xlsx",
        sheet_title=receipt.ma_phieu_nhap_kho,
        title_banner=f"PHIẾU NHẬP KHO: {receipt.ma_phieu_nhap_kho}",
        subtitle=(
            f"NCC: {receipt.nha_cung_cap.ten_nha_cung_cap} | Cơ sở nhận: {receipt.co_so_nhan.ten_co_so} | "
            f"Trạng thái: {receipt.get_trang_thai_display()}"
        ),
        headers=headers,
        rows=rows,
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def import_report_export_view(request):
    """Export period Warehouse Import Activity Report to Excel (.xlsx) (UC-4.10 & UC-4.11)."""
    assert_can_manage_imports(request.user)
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    supplier_id = request.GET.get("supplier", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    receipts = list(
        get_filtered_import_receipts(
            search_query=search_query,
            status=status_filter,
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
        )
    )
    summary = get_import_activity_summary(receipts)
    headers = [
        "STT",
        "Mã phiếu nhập",
        "Ngày nhập",
        "Mã NCC",
        "Tên nhà cung cấp",
        "Cơ sở nhận",
        "Người lập",
        "Tổng SL",
        "Tổng tiền (VNĐ)",
        "Trạng thái",
    ]
    rows = []
    for idx, r in enumerate(receipts, start=1):
        rows.append([
            idx,
            r.ma_phieu_nhap_kho,
            r.ngay_nhap.strftime("%d/%m/%Y %H:%M"),
            r.nha_cung_cap.ma_nha_cung_cap,
            r.nha_cung_cap.ten_nha_cung_cap,
            r.co_so_nhan.ma_co_so,
            r.nguoi_tao.display_name,
            r.total_quantity,
            int(r.tong_tien),
            r.get_trang_thai_display(),
        ])
    rows.append([
        "",
        "TỔNG CỘNG (ĐÃ DUYỆT)",
        "",
        "",
        f"{summary['approved_count']}/{summary['total_count']} phiếu đã duyệt",
        "",
        "",
        summary["approved_quantity"],
        int(summary["approved_amount"]),
        "",
    ])
    period_label = f"Từ {date_from or 'đầu kỳ'} đến {date_to or 'hiện tại'}"
    return build_excel_response(
        filename="Bao_Cao_Hoat_Dong_Nhap_Kho.xlsx",
        sheet_title="BaoCaoNhapKho",
        title_banner="BÁO CÁO HOẠT ĐỘNG NHẬP KHO — OLD SCHOOL",
        subtitle=f"Kỳ báo cáo: {period_label} | Kho tổng: CS1",
        headers=headers,
        rows=rows,
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def supplier_list_create_view(request):
    assert_can_manage_imports(request.user)
    search_query = request.GET.get("q", "").strip()
    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            try:
                supplier = create_supplier(
                    actor=request.user,
                    ma_nha_cung_cap=form.cleaned_data["ma_nha_cung_cap"],
                    ten_nha_cung_cap=form.cleaned_data["ten_nha_cung_cap"],
                    dia_chi=form.cleaned_data["dia_chi"],
                    sdt=form.cleaned_data["sdt"],
                )
                messages.success(request, f"Đã thêm nhà cung cấp {supplier.ten_nha_cung_cap} ({supplier.ma_nha_cung_cap}).")
                next_url = request.POST.get("next") or "purchasing:supplier_list"
                return redirect(next_url)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
    else:
        form = SupplierForm()

    return render(
        request,
        "purchasing/supplier_list.html",
        {
            "suppliers": get_all_suppliers(search_query),
            "form": form,
            "search_query": search_query,
        },
    )



@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def import_propose_return_view(request, receipt_id: int):
    """Manager reports defective goods and requests returning to supplier."""
    receipt = get_object_or_404(PhieuNhapKho.objects.select_related("co_so_nhan"), pk=receipt_id)
    assert_branch_access(request.user, receipt.co_so_nhan)
    reason = request.POST.get("ly_do_loi_ncc", "").strip()
    try:
        propose_supplier_return(actor=request.user, receipt=receipt, reason=reason)
        messages.success(request, f"Đã gửi báo cáo hàng lỗi lô {receipt.ma_phieu_nhap_kho} đến Chủ cửa hàng.")
    except (ValidationError, PermissionDenied) as exc:
        msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        messages.error(request, msg)
    return redirect("purchasing:import_detail", receipt_id=receipt.id)


@role_required(User.Role.ADMIN)
@require_POST
def import_confirm_supplier_return_view(request, receipt_id: int):
    """Admin confirms returning defective goods to supplier."""
    receipt = get_object_or_404(PhieuNhapKho.objects.select_related("co_so_nhan"), pk=receipt_id)
    admin_note = request.POST.get("ghi_chu_chu", "").strip()
    try:
        confirm_supplier_return(actor=request.user, receipt=receipt, admin_note=admin_note)
        messages.success(request, f"Đã xác nhận trả hàng cho Nhà cung cấp đối với lô {receipt.ma_phieu_nhap_kho}.")
    except (ValidationError, PermissionDenied) as exc:
        msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        messages.error(request, msg)
    return redirect("purchasing:import_detail", receipt_id=receipt.id)
