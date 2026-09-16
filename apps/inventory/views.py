from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.accounts.permissions import get_effective_branch
from apps.catalog.models import BienThe
from apps.inventory.excel import build_excel_response
from apps.inventory.models import TonKho


@login_required
def api_variant_stock_view(request):
    """Return current stock and price for a variant at a branch."""
    variant_id = request.GET.get("variant_id")
    branch = get_effective_branch(request, allow_all_for_admin=False)
    if not variant_id or not str(variant_id).isdigit():
        return JsonResponse({"error": "Thiếu variant_id hợp lệ."}, status=400)

    variant = BienThe.objects.select_related("san_pham").filter(pk=int(variant_id)).first()
    if not variant:
        return JsonResponse({"error": "Không tìm thấy biến thể."}, status=404)

    bal = TonKho.objects.filter(co_so=branch, bien_the=variant).first() if branch else None
    return JsonResponse(
        {
            "variant_id": variant.id,
            "ma_sku": variant.ma_sku,
            "ten_hang_hoa": variant.full_display_name,
            "don_vi_tinh": variant.san_pham.don_vi_tinh,
            "don_gia": float(variant.don_gia),
            "so_luong_ton": bal.so_luong if bal else 0,
            "stock_status": bal.stock_status_label if bal else "Hết hàng",
        }
    )


@login_required
def download_excel_template_view(request, template_type: str):
    """Download ready-to-use .xlsx templates for Import, Outbound, or Stocktake."""
    sample_variants = list(BienThe.objects.select_related("san_pham").filter(trang_thai="ACTIVE")[:3])

    if template_type == "import":
        headers = ["Mã SKU", "Số lượng", "Đơn giá", "Chiết khấu", "Ghi chú"]
        rows = [
            [v.ma_sku, 20, int(v.don_gia * Decimal("0.65")), 0, f"Nhập lô mới {v.san_pham.ten_hang_hoa}"]
            for v in sample_variants
        ] or [["SP001-DEN-M", 20, 150000, 0, "Nhập hàng đợt 1"]]
        return build_excel_response(
            filename="mau_nhap_kho_oldschool.xlsx",
            sheet_title="MauNhapKho",
            title_banner="MẪU FILE EXCEL NHẬP KHO - OLD SCHOOL",
            subtitle="Điền Mã SKU, Số lượng (>0), Đơn giá nhập (>=0), Chiết khấu (VNĐ).",
            headers=headers,
            rows=rows,
        )

    if template_type == "outbound":
        headers = ["Mã SKU", "Số lượng", "Đơn giá", "Ghi chú"]
        rows = [
            [v.ma_sku, 2, int(v.don_gia), "Xuất bán tại quầy"]
            for v in sample_variants
        ] or [["SP001-DEN-M", 2, 250000, "Xuất bán khách lẻ"]]
        return build_excel_response(
            filename="mau_xuat_kho_oldschool.xlsx",
            sheet_title="MauXuatKho",
            title_banner="MẪU FILE EXCEL XUẤT KHO BÁN HÀNG - OLD SCHOOL",
            subtitle="Điền Mã SKU, Số lượng xuất (>0), Đơn giá bán.",
            headers=headers,
            rows=rows,
        )

    headers = ["Mã SKU", "Tên hàng hóa", "Đơn vị tính", "Số lượng thực tế", "Xử lý", "Ghi chú"]
    rows = [
        [v.ma_sku, v.full_display_name, v.san_pham.don_vi_tinh, 10, "Đối chiếu định kỳ", ""]
        for v in sample_variants
    ] or [["SP001-DEN-M", "Áo khoác Bomber (Đen - Size M)", "Cái", 10, "", ""]]
    return build_excel_response(
        filename="mau_kiem_ke_oldschool.xlsx",
        sheet_title="MauKiemKe",
        title_banner="MẪU FILE EXCEL KIỂM KÊ KHO - OLD SCHOOL",
        subtitle="Điền Mã SKU và Số lượng thực tế (>=0) kiểm đếm tại kho.",
        headers=headers,
        rows=rows,
    )
