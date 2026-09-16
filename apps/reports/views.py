"""Views for Dynamic Inventory & Supply Chain Reporting (UC-7.1 to UC-7.5)."""
import json
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.accounts.models import User
from apps.accounts.permissions import get_effective_branch, role_required
from apps.catalog.models import BienThe
from apps.catalog.selectors import get_distinct_categories
from apps.reports.selectors import build_inventory_report, get_variant_ledger_movements
from apps.reports.services import export_inventory_report_excel, save_report_snapshots


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def report_dashboard_view(request):
    selected_branch = get_effective_branch(request, allow_all_for_admin=True)
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    search_query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    color = request.GET.get("color", "").strip()
    size = request.GET.get("size", "").strip()
    stock_status = request.GET.get("stock_status", "").strip()
    report_tab = request.GET.get("tab", "all").strip()

    if date_from and date_to and date_from > date_to:
        messages.warning(
            request,
            "Khoảng thời gian lọc không hợp lệ: 'Từ ngày' không được lớn hơn 'Đến ngày'. Hệ thống đã tự động điều chỉnh khoảng ngày.",
        )

    report_data = build_inventory_report(
        user=request.user,
        selected_branch=selected_branch,
        date_from_str=date_from,
        date_to_str=date_to,
        search_query=search_query,
        category=category,
        color=color,
        size=size,
        stock_status=stock_status,
        report_tab=report_tab,
    )

    if request.GET.get("export") == "excel":
        return export_inventory_report_excel(report_data)

    chart_labels = [f"{r['ma_sku']} ({r['ten_hang_hoa'][:18]})" for r in report_data["top_selling_chart"]]
    chart_sales = [r["sale_out_qty"] for r in report_data["top_selling_chart"]]
    chart_closing = [r["closing_qty"] for r in report_data["top_selling_chart"]]

    colors = list(BienThe.objects.values_list("mau_sac", flat=True).distinct().order_by("mau_sac"))
    sizes = list(BienThe.objects.values_list("kich_co", flat=True).distinct().order_by("kich_co"))

    return render(
        request,
        "reports/report_dashboard.html",
        {
            "report": report_data,
            "categories": get_distinct_categories(),
            "colors": colors,
            "sizes": sizes,
            "chart_labels_json": json.dumps(chart_labels, ensure_ascii=False),
            "chart_sales_json": json.dumps(chart_sales),
            "chart_closing_json": json.dumps(chart_closing),
            "filters": {
                "date_from": report_data["start_date"].isoformat(),
                "date_to": report_data["end_date"].isoformat(),
                "q": search_query,
                "category": category,
                "color": color,
                "size": size,
                "stock_status": stock_status,
                "tab": report_tab,
            },
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
def report_variant_detail_view(request, variant_id: int):
    """Detailed stock ledger drill-down for a specific SKU (UC-7.2)."""
    selected_branch = get_effective_branch(request, allow_all_for_admin=True)
    variant = get_object_or_404(BienThe.objects.select_related("san_pham"), pk=variant_id)
    movements = get_variant_ledger_movements(user=request.user, variant=variant, selected_branch=selected_branch)
    return render(
        request,
        "reports/report_variant_detail.html",
        {
            "variant": variant,
            "movements": movements,
            "selected_branch": request.user.branch if request.user.role != User.Role.ADMIN else selected_branch,
        },
    )


@role_required(User.Role.ADMIN, User.Role.MANAGER)
@require_POST
def report_save_snapshot_view(request):
    selected_branch = get_effective_branch(request, allow_all_for_admin=True)
    report_data = build_inventory_report(
        user=request.user,
        selected_branch=selected_branch,
        date_from_str=request.POST.get("date_from", ""),
        date_to_str=request.POST.get("date_to", ""),
    )
    saved_count = save_report_snapshots(actor=request.user, report_data=report_data)
    messages.success(request, f"Đã lưu bản chụp báo cáo ({saved_count} dòng SKU) vào hệ thống.")
    return redirect("reports:report_dashboard")
