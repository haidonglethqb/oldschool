"""Report Export & Snapshot Persistence Services (UC-7.3)."""
from django.http import HttpResponse
from django.utils import timezone
from apps.accounts.models import User
from apps.inventory.excel import build_excel_response
from apps.reports.models import BaoCao


def export_inventory_report_excel(report_data: dict) -> HttpResponse:
    """Export the filtered inventory & supply chain report to `.xlsx` (UC-7.3)."""
    branch = report_data["effective_branch"]
    branch_label = f"{branch.ma_co_so} - {branch.ten_co_so}" if branch else "Toàn hệ thống (Tất cả cơ sở)"
    start_d = report_data["start_date"].strftime("%d/%m/%Y")
    end_d = report_data["end_date"].strftime("%d/%m/%Y")

    headers = [
        "STT",
        "Mã SP",
        "Mã SKU",
        "Tên hàng hóa",
        "Màu / Size",
        "ĐVT",
        "Tồn đầu kỳ",
        "Nhập NCC",
        "Nhập điều chuyển",
        "Tổng nhập",
        "Xuất bán hàng",
        "Xuất điều chuyển",
        "Tổng xuất",
        "Tồn cuối kỳ",
        "Đang vận chuyển",
        "Đơn giá vốn (VNĐ)",
        "Giá trị tồn kho (VNĐ)",
        "Trạng thái",
    ]
    rows = []
    for idx, r in enumerate(report_data["rows"], start=1):
        rows.append([
            idx,
            r["ma_san_pham"],
            r["ma_sku"],
            r["ten_hang_hoa"],
            f"{r['mau_sac']} / {r['kich_co']}",
            r["don_vi_tinh"],
            r["opening_qty"],
            r["import_in_qty"],
            r["transfer_in_qty"],
            r["total_in_qty"],
            r["sale_out_qty"],
            r["transfer_out_qty"],
            r["total_out_qty"],
            r["closing_qty"],
            r["in_transit_qty"],
            int(r["unit_price"]),
            int(r["inventory_value"]),
            r["status_label"],
        ])

    totals = report_data["totals"]
    rows.append([
        "",
        "",
        "",
        "TỔNG CỘNG TOÀN BÁO CÁO",
        "",
        "",
        totals["opening_qty"],
        totals["import_in_qty"],
        totals["transfer_in_qty"],
        totals["total_in_qty"],
        totals["sale_out_qty"],
        totals["transfer_out_qty"],
        totals["total_out_qty"],
        totals["closing_qty"],
        totals["in_transit_qty"],
        "",
        int(totals["inventory_value"]),
        "",
    ])

    scope_code = branch.ma_co_so if branch else "ALL"
    filename = f"BaoCaoTonKho_{scope_code}_{report_data['start_date']}_{report_data['end_date']}.xlsx"
    return build_excel_response(
        filename=filename,
        sheet_title="BaoCaoTonKho",
        title_banner="BÁO CÁO XUẤT - NHẬP - TỒN KHO OLD SCHOOL",
        subtitle=f"Phạm vi: {branch_label} | Kỳ báo cáo: {start_d} - {end_d}",
        headers=headers,
        rows=rows,
    )


def save_report_snapshots(*, actor: User, report_data: dict) -> int:
    """Persist snapshot rows into `BaoCao` table for historical audit."""
    branch = report_data["effective_branch"]
    scope_code = branch.ma_co_so if branch else "ALL"
    stamp = timezone.now().strftime("%Y%m%d%H%M%S%f")[:17]
    count = 0
    for idx, r in enumerate(report_data["rows"], start=1):
        code = f"BC-{scope_code}-{stamp}-{idx:03d}"
        BaoCao.objects.create(
            ma_bao_cao=code,
            co_so=branch,
            bien_the=r["variant"],
            tu_ngay=report_data["start_date"],
            den_ngay=report_data["end_date"],
            ton_dau_ky=r["opening_qty"],
            nhap_kho=r["total_in_qty"],
            xuat_kho=r["total_out_qty"],
            ton_cuoi_ky=r["closing_qty"],
            gia_von=r["unit_price"],
            gia_tri_ton_kho=r["inventory_value"],
            trang_thai=r["status_label"],
            ghi_chu=f"Xuất bán: {r['sale_out_qty']} | Xuất ĐC: {r['transfer_out_qty']} | Đang VC: {r['in_transit_qty']}",
            nguoi_tao=actor,
        )
        count += 1
    return count
