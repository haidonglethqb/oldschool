from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from apps.accounts.models import User
from apps.accounts.permissions import get_effective_branch, role_required
from apps.catalog.forms import ProductForm
from apps.catalog.models import BienThe, SanPham
from apps.catalog.selectors import evaluate_product_row, list_catalog_products
from apps.catalog.services import (
    create_product_with_variants,
    delete_product,
    has_product_transactions,
    toggle_product_business_status,
    update_product_and_variants,
)
from apps.inventory.models import StockStatus, TonKho


def _extract_variants_from_post(request, default_price: Decimal) -> list[dict]:
    ids = request.POST.getlist("variant_id[]")
    skus = request.POST.getlist("variant_sku[]")
    colors = request.POST.getlist("variant_color[]")
    sizes = request.POST.getlist("variant_size[]")
    prices = request.POST.getlist("variant_price[]")
    thresholds = request.POST.getlist("variant_threshold[]")

    variants = []
    max_len = max(len(colors), len(sizes), len(skus))
    for i in range(max_len):
        c = (colors[i] if i < len(colors) else "").strip()
        s = (sizes[i] if i < len(sizes) else "").strip()
        sku = (skus[i] if i < len(skus) else "").strip()
        vid = (ids[i] if i < len(ids) else "").strip()
        p_raw = (prices[i] if i < len(prices) else "").strip()
        t_raw = (thresholds[i] if i < len(thresholds) else "").strip()

        if not c and not s and not sku:
            continue
        try:
            price = Decimal(p_raw) if p_raw else default_price
        except InvalidOperation:
            price = default_price
        try:
            threshold = int(t_raw) if t_raw else 5
        except ValueError:
            threshold = 5

        variants.append(
            {
                "id": int(vid) if vid.isdigit() else None,
                "ma_sku": sku,
                "mau_sac": c or "Mặc định",
                "kich_co": s or "Freesize",
                "don_gia": price,
                "muc_ton_toi_thieu": threshold,
            }
        )
    return variants


@login_required
def product_list_view(request):
    """Handle UC-3, UC-3.1, UC-3.6, UC-3.7, and UC-5.1: Product list, search, filter, stock status."""
    active_branch = get_effective_branch(request, allow_all_for_admin=True)
    ma_hang = request.GET.get("ma_hang", "").strip()
    ten_hang = request.GET.get("ten_hang", "").strip()
    q = request.GET.get("q", "").strip()
    nhom_hang = request.GET.get("nhom_hang", "").strip()
    mau_sac = request.GET.get("mau_sac", "").strip()
    kich_co = request.GET.get("kich_co", "").strip()
    tinh_trang = request.GET.get("tinh_trang", "").strip()
    trang_thai_kd = request.GET.get("trang_thai_kd", "").strip()

    products = list_catalog_products(
        user=request.user,
        active_branch=active_branch,
        ma_hang=ma_hang,
        ten_hang=ten_hang,
        q=q,
        nhom_hang=nhom_hang,
        mau_sac=mau_sac,
        kich_co=kich_co,
        tinh_trang=tinh_trang,
        trang_thai_kd=trang_thai_kd,
    )

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    categories = list(SanPham.objects.values_list("nhom_hang", flat=True).distinct().order_by("nhom_hang"))
    colors = list(BienThe.objects.values_list("mau_sac", flat=True).distinct().order_by("mau_sac"))
    sizes = list(BienThe.objects.values_list("kich_co", flat=True).distinct().order_by("kich_co"))

    return render(
        request,
        "catalog/product_list.html",
        {
            "page_obj": page_obj,
            "products": page_obj.object_list,
            "categories": categories,
            "colors": colors,
            "sizes": sizes,
            "stock_statuses": StockStatus.choices,
            "filters": {
                "ma_hang": ma_hang,
                "ten_hang": ten_hang,
                "q": q,
                "nhom_hang": nhom_hang,
                "mau_sac": mau_sac,
                "kich_co": kich_co,
                "tinh_trang": tinh_trang,
                "trang_thai_kd": trang_thai_kd,
            },
            "can_edit": request.user.role in {User.Role.ADMIN, User.Role.MANAGER},
        },
    )


@login_required
def product_detail_view(request, pk: int):
    """Handle UC-3.2: View detailed product info, variants, and branch stock breakdown."""
    product = SanPham.objects.filter(pk=pk).first()
    if not product:
        messages.error(request, "Dữ liệu hàng hóa không tồn tại hoặc đã bị xóa.")
        return redirect("catalog:product_list")

    active_branch = get_effective_branch(request, allow_all_for_admin=True)
    evaluate_product_row(product, active_branch)

    # Full branch × variant stock table
    branch_balances = TonKho.objects.select_related("co_so", "bien_the").filter(bien_the__san_pham=product)
    if request.user.role in {User.Role.MANAGER, User.Role.STAFF} and request.user.branch_id:
        branch_balances = branch_balances.filter(co_so_id=request.user.branch_id)

    return render(
        request,
        "catalog/product_detail.html",
        {
            "product": product,
            "branch_balances": branch_balances.order_by("bien_the__ma_sku", "co_so__ma_co_so"),
            "can_edit": request.user.role in {User.Role.ADMIN, User.Role.MANAGER},
            "has_transactions": has_product_transactions(product),
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def product_create_view(request):
    """Handle UC-3.3: Create new product and its SKU variants."""
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            cd = form.cleaned_data
            variants_data = _extract_variants_from_post(request, cd["don_gia_niem_yet"])
            try:
                product = create_product_with_variants(
                    actor=request.user,
                    ma_san_pham=cd["ma_san_pham"],
                    ten_hang_hoa=cd["ten_hang_hoa"],
                    nhom_hang=cd["nhom_hang"],
                    don_vi_tinh=cd["don_vi_tinh"],
                    don_gia_niem_yet=cd["don_gia_niem_yet"],
                    ghi_chu=cd["ghi_chu"],
                    hinh_anh=cd.get("hinh_anh"),
                    trang_thai=cd["trang_thai"],
                    variants_data=variants_data,
                    min_threshold=cd.get("muc_ton_toi_thieu") or 5,
                )
                messages.success(request, f"Đã lưu thành công mặt hàng {product.ma_san_pham} - {product.ten_hang_hoa}.")
                return redirect("catalog:product_list")
            except ValidationError as exc:
                err_msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
                messages.error(request, err_msg)
        else:
            messages.error(request, "Dữ liệu nhập chưa hợp lệ. Vui lòng kiểm tra lại các trường thông tin bắt buộc.")

    return render(
        request,
        "catalog/product_form.html",
        {
            "form": form,
            "is_edit": False,
            "existing_variants": [],
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def product_edit_view(request, pk: int):
    """Handle UC-3.5: Update existing product and variants."""
    product = SanPham.objects.filter(pk=pk).first()
    if not product:
        messages.error(request, "Dữ liệu hàng hóa không tồn tại hoặc đã bị xóa.")
        return redirect("catalog:product_list")

    first_bal = TonKho.objects.filter(bien_the__san_pham=product).first()
    initial_threshold = first_bal.muc_ton_toi_thieu if first_bal else 5
    form = ProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
        initial={"muc_ton_toi_thieu": initial_threshold},
    )

    if request.method == "POST":
        if form.is_valid():
            cd = form.cleaned_data
            variants_data = _extract_variants_from_post(request, cd["don_gia_niem_yet"])
            try:
                update_product_and_variants(
                    actor=request.user,
                    product=product,
                    ten_hang_hoa=cd["ten_hang_hoa"],
                    nhom_hang=cd["nhom_hang"],
                    don_vi_tinh=cd["don_vi_tinh"],
                    don_gia_niem_yet=cd["don_gia_niem_yet"],
                    ghi_chu=cd["ghi_chu"],
                    hinh_anh=cd.get("hinh_anh"),
                    trang_thai=cd["trang_thai"],
                    variants_data=variants_data if variants_data else None,
                    min_threshold=cd.get("muc_ton_toi_thieu"),
                )
                messages.success(request, f"Đã lưu thành công thông tin mặt hàng {product.ma_san_pham}.")
                return redirect("catalog:product_list")
            except ValidationError as exc:
                err_msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
                messages.error(request, err_msg)
        else:
            messages.error(request, "Vui lòng kiểm tra lại dữ liệu nhập.")

    existing_variants = list(product.variants.all())
    for v in existing_variants:
        v_bal = TonKho.objects.filter(bien_the=v).first()
        v.min_threshold = v_bal.muc_ton_toi_thieu if v_bal else initial_threshold

    return render(
        request,
        "catalog/product_form.html",
        {
            "form": form,
            "product": product,
            "is_edit": True,
            "existing_variants": existing_variants,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def product_delete_view(request, pk: int):
    """Handle UC-3.4: Delete eligible product or reject if it has transactions."""
    if request.method != "POST":
        return redirect("catalog:product_list")

    product = SanPham.objects.filter(pk=pk).first()
    if not product:
        messages.error(request, "Dữ liệu hàng hóa không tồn tại hoặc đã bị xóa.")
        return redirect("catalog:product_list")

    try:
        code = product.ma_san_pham
        delete_product(actor=request.user, product=product)
        messages.success(request, f"Đã xóa thành công mặt hàng {code}.")
    except ValidationError as exc:
        err_msg = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        messages.error(request, err_msg)

    return redirect("catalog:product_list")


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def product_toggle_status_view(request, pk: int):
    """Handle UC-3: Discontinue or reactivate product business status."""
    if request.method != "POST":
        return redirect("catalog:product_detail", pk=pk)

    product = get_object_or_404(SanPham, pk=pk)
    toggle_product_business_status(actor=request.user, product=product)
    messages.success(
        request,
        f"Đã chuyển trạng thái mặt hàng {product.ma_san_pham} sang: {product.get_trang_thai_display()}.",
    )
    return redirect("catalog:product_detail", pk=product.id)
