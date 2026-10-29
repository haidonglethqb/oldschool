"""
Dynamic Inventory & Supply Chain Reporting Engine (Phase 7 - UC-7.1 to UC-7.5 & Mục 13).
Computes period metrics directly from immutable `StockMovement` ledger and `TonKho` balances:
- Tồn đầu kỳ (`opening_qty`)
- Nhập từ NCC (`import_in_qty`) & Nhập điều chuyển (`transfer_in_qty`) -> Tổng nhập (`total_in_qty`)
- Xuất bán hàng (`sale_out_qty`) & Xuất điều chuyển (`transfer_out_qty`) -> Tổng xuất (`total_out_qty`)
- Tồn cuối kỳ (`closing_qty`)
- Hàng đang vận chuyển (`in_transit_qty`) from `DISPATCHED` interbranch transfers
- Phân loại: Bán chạy (`best_selling`), Bán chậm / Tồn lâu (`slow_moving`), Sắp hết / Hết hàng (`low_stock`)
- Giá vốn bình quân (`unit_price` / `cost_price`) tính theo DEC-07 từ các phiếu nhập đã duyệt
"""
from datetime import date, datetime, time
from decimal import Decimal
from django.db.models import Q, Sum
from django.utils import timezone
from apps.accounts.models import User
from apps.branches.models import CoSo
from apps.catalog.models import BienThe
from apps.inventory.models import StockMovement, TonKho
from apps.purchasing.models import ChiTietPhieuNhapKho, PhieuNhapKho
from apps.transfers.models import ChiTietPhieuDieuChuyen, PhieuDieuChuyen


def parse_report_dates(date_from_str: str = "", date_to_str: str = "") -> tuple[date, date]:
    today = timezone.localdate()
    default_start = today.replace(day=1)
    try:
        start_d = date.fromisoformat(date_from_str) if date_from_str else default_start
    except ValueError:
        start_d = default_start
    try:
        end_d = date.fromisoformat(date_to_str) if date_to_str else today
    except ValueError:
        end_d = today
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    return start_d, end_d


def build_inventory_report(
    *,
    user: User,
    selected_branch: CoSo | None = None,
    date_from_str: str = "",
    date_to_str: str = "",
    search_query: str = "",
    category: str = "",
    color: str = "",
    size: str = "",
    stock_status: str = "",
    report_tab: str = "all",
) -> dict:
    """
    Build the comprehensive inventory & supply chain report dataset.
    Enforces strict branch scoping: Managers only see their own branch.
    """
    effective_branch = user.branch if user.role != User.Role.ADMIN else selected_branch
    start_date, end_date = parse_report_dates(date_from_str, date_to_str)

    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max), tz)

    variants_qs = BienThe.objects.select_related("san_pham").filter(san_pham__trang_thai="ACTIVE")
    if search_query:
        q = search_query.strip()
        variants_qs = variants_qs.filter(
            Q(ma_sku__icontains=q)
            | Q(san_pham__ma_san_pham__icontains=q)
            | Q(san_pham__ten_hang_hoa__icontains=q)
        )
    if category:
        variants_qs = variants_qs.filter(san_pham__nhom_hang__iexact=category.strip())
    if color:
        variants_qs = variants_qs.filter(mau_sac__iexact=color.strip())
    if size:
        variants_qs = variants_qs.filter(kich_co__iexact=size.strip())

    variants = list(variants_qs.order_by("san_pham__ma_san_pham", "ma_sku"))
    variant_ids = [v.id for v in variants]

    # Current balances & min thresholds
    balances_qs = TonKho.objects.filter(bien_the_id__in=variant_ids)
    if effective_branch:
        balances_qs = balances_qs.filter(co_so=effective_branch)

    current_stock_map: dict[int, int] = {}
    min_threshold_map: dict[int, int] = {}
    for b in balances_qs:
        current_stock_map[b.bien_the_id] = current_stock_map.get(b.bien_the_id, 0) + b.so_luong
        min_threshold_map[b.bien_the_id] = max(min_threshold_map.get(b.bien_the_id, 0), b.muc_ton_toi_thieu)

    # Movements before start_dt -> opening stock
    movements_base = StockMovement.objects.filter(bien_the_id__in=variant_ids)
    if effective_branch:
        movements_base = movements_base.filter(co_so=effective_branch)

    opening_agg = (
        movements_base.filter(effective_at__lt=start_dt)
        .values("bien_the_id")
        .annotate(net_qty=Sum("quantity_delta"))
    )
    opening_map = {row["bien_the_id"]: int(row["net_qty"] or 0) for row in opening_agg}

    # Movements within [start_dt, end_dt] grouped by variant and movement_type
    period_agg = (
        movements_base.filter(effective_at__gte=start_dt, effective_at__lte=end_dt)
        .values("bien_the_id", "movement_type")
        .annotate(total_delta=Sum("quantity_delta"))
    )
    period_map: dict[int, dict[str, int]] = {}
    for row in period_agg:
        vid = row["bien_the_id"]
        mtype = row["movement_type"]
        period_map.setdefault(vid, {})[mtype] = int(row["total_delta"] or 0)

    # In-transit quantities (`DISPATCHED` transfers not yet received)
    in_transit_qs = ChiTietPhieuDieuChuyen.objects.filter(
        bien_the_id__in=variant_ids,
        phieu_dieu_chuyen__trang_thai=PhieuDieuChuyen.Status.DISPATCHED,
    )
    if effective_branch:
        in_transit_qs = in_transit_qs.filter(
            Q(phieu_dieu_chuyen__co_so_xuat=effective_branch) | Q(phieu_dieu_chuyen__co_so_nhan=effective_branch)
        )
    in_transit_agg = in_transit_qs.values("bien_the_id").annotate(transit_qty=Sum("so_luong_xuat"))
    in_transit_map = {row["bien_the_id"]: int(row["transit_qty"] or 0) for row in in_transit_agg}

    # Average cost per DEC-07: weighted average unit import price from APPROVED receipts
    approved_import_lines = (
        ChiTietPhieuNhapKho.objects.filter(
            bien_the_id__in=variant_ids,
            phieu_nhap_kho__trang_thai=PhieuNhapKho.Status.APPROVED,
        )
        .values("bien_the_id")
        .annotate(
            total_qty=Sum("so_luong"),
            total_amount=Sum("thanh_tien"),
        )
    )
    avg_cost_map: dict[int, Decimal] = {}
    for item in approved_import_lines:
        qty = item["total_qty"] or 0
        amt = item["total_amount"] or Decimal("0")
        if qty > 0:
            avg_cost_map[item["bien_the_id"]] = (amt / Decimal(qty)).quantize(Decimal("1"))

    rows = []
    totals = {
        "opening_qty": 0,
        "import_in_qty": 0,
        "transfer_in_qty": 0,
        "total_in_qty": 0,
        "sale_out_qty": 0,
        "transfer_out_qty": 0,
        "total_out_qty": 0,
        "closing_qty": 0,
        "in_transit_qty": 0,
        "inventory_value": Decimal("0"),
        "sales_revenue": Decimal("0"),
        "low_stock_count": 0,
        "out_of_stock_count": 0,
    }

    for v in variants:
        vid = v.id
        m_data = period_map.get(vid, {})
        opening_from_prior = opening_map.get(vid, 0)
        opening_in_period = m_data.get(StockMovement.MovementType.OPENING, 0)
        opening_qty = opening_from_prior + opening_in_period

        import_in_qty = max(0, m_data.get(StockMovement.MovementType.IMPORT_IN, 0))
        transfer_in_qty = max(0, m_data.get(StockMovement.MovementType.TRANSFER_IN, 0))
        adj_in_qty = max(0, m_data.get(StockMovement.MovementType.STOCKTAKE_ADJUST, 0))
        total_in_qty = import_in_qty + transfer_in_qty + adj_in_qty

        sale_out_qty = abs(min(0, m_data.get(StockMovement.MovementType.SALE_OUT, 0)))
        transfer_out_qty = abs(min(0, m_data.get(StockMovement.MovementType.TRANSFER_OUT, 0)))
        adj_out_qty = abs(min(0, m_data.get(StockMovement.MovementType.STOCKTAKE_ADJUST, 0)))
        total_out_qty = sale_out_qty + transfer_out_qty + adj_out_qty

        closing_qty = opening_qty + total_in_qty - total_out_qty
        current_qty = current_stock_map.get(vid, closing_qty)
        min_thresh = min_threshold_map.get(vid, 5)
        in_transit_qty = in_transit_map.get(vid, 0)

        if closing_qty <= 0:
            status_code = "OUT_OF_STOCK"
            status_label = "Hết hàng"
            badge_class = "badge-out-of-stock"
        elif closing_qty <= min_thresh:
            status_code = "LOW_STOCK"
            status_label = "Sắp hết hàng"
            badge_class = "badge-low-stock"
        else:
            status_code = "IN_STOCK"
            status_label = "Còn hàng"
            badge_class = "badge-in-stock"

        cost_price = avg_cost_map.get(vid, Decimal("0"))
        selling_price = v.don_gia
        unit_price = cost_price  # gia_von per DEC-07
        inv_value = Decimal(max(0, closing_qty)) * unit_price
        sales_rev = Decimal(sale_out_qty) * selling_price

        is_best_selling = sale_out_qty >= 3
        is_slow_moving = sale_out_qty == 0 and closing_qty > 0  # per DEC-07

        row_item = {
            "variant": v,
            "product": v.san_pham,
            "ma_san_pham": v.san_pham.ma_san_pham,
            "ma_sku": v.ma_sku,
            "ten_hang_hoa": v.san_pham.ten_hang_hoa,
            "mau_sac": v.mau_sac,
            "kich_co": v.kich_co,
            "danh_muc": v.san_pham.nhom_hang,
            "don_vi_tinh": v.san_pham.don_vi_tinh,
            "opening_qty": opening_qty,
            "import_in_qty": import_in_qty,
            "transfer_in_qty": transfer_in_qty,
            "total_in_qty": total_in_qty,
            "sale_out_qty": sale_out_qty,
            "transfer_out_qty": transfer_out_qty,
            "total_out_qty": total_out_qty,
            "closing_qty": closing_qty,
            "current_qty": current_qty,
            "min_threshold": min_thresh,
            "in_transit_qty": in_transit_qty,
            "unit_price": unit_price,
            "cost_price": cost_price,
            "selling_price": selling_price,
            "inventory_value": inv_value,
            "sales_revenue": sales_rev,
            "status_code": status_code,
            "status_label": status_label,
            "badge_class": badge_class,
            "is_best_selling": is_best_selling,
            "is_slow_moving": is_slow_moving,
        }

        if stock_status and status_code != stock_status:
            continue
        if report_tab == "best_selling" and not is_best_selling:
            continue
        if report_tab == "slow_moving" and not is_slow_moving:
            continue
        if report_tab == "low_stock" and status_code not in {"LOW_STOCK", "OUT_OF_STOCK"}:
            continue
        if report_tab == "in_transit" and in_transit_qty <= 0:
            continue

        rows.append(row_item)
        if status_code == "OUT_OF_STOCK":
            totals["out_of_stock_count"] += 1
        elif status_code == "LOW_STOCK":
            totals["low_stock_count"] += 1

        totals["opening_qty"] += opening_qty
        totals["import_in_qty"] += import_in_qty
        totals["transfer_in_qty"] += transfer_in_qty
        totals["total_in_qty"] += total_in_qty
        totals["sale_out_qty"] += sale_out_qty
        totals["transfer_out_qty"] += transfer_out_qty
        totals["total_out_qty"] += total_out_qty
        totals["closing_qty"] += closing_qty
        totals["in_transit_qty"] += in_transit_qty
        totals["inventory_value"] += inv_value
        totals["sales_revenue"] += sales_rev

    if report_tab == "best_selling":
        rows.sort(key=lambda r: (-r["sale_out_qty"], r["ma_sku"]))
    elif report_tab == "slow_moving":
        rows.sort(key=lambda r: (-r["closing_qty"], r["ma_sku"]))

    top_selling_chart = sorted(rows, key=lambda r: -r["sale_out_qty"])[:6]

    return {
        "effective_branch": effective_branch,
        "start_date": start_date,
        "end_date": end_date,
        "rows": rows,
        "totals": totals,
        "top_selling_chart": top_selling_chart,
        "report_tab": report_tab,
    }


def get_variant_ledger_movements(*, user: User, variant: BienThe, selected_branch: CoSo | None = None):
    effective_branch = user.branch if user.role != User.Role.ADMIN else selected_branch
    qs = StockMovement.objects.select_related("co_so", "bien_the", "actor").filter(bien_the=variant)
    if effective_branch:
        qs = qs.filter(co_so=effective_branch)
    return qs.order_by("-effective_at", "-id")[:100]
