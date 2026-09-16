"""Selectors for Warehouse Import Receipts and Suppliers (UC-4.3 to UC-4.6, UC-4.11)."""
from decimal import Decimal
from django.db.models import Q, QuerySet
from apps.purchasing.models import NhaCungCap, PhieuNhapKho


def get_filtered_import_receipts(
    *,
    search_query: str = "",
    status: str = "",
    supplier_id: str = "",
    date_from: str = "",
    date_to: str = "",
) -> QuerySet[PhieuNhapKho]:
    qs = PhieuNhapKho.objects.select_related(
        "nha_cung_cap", "co_so_nhan", "nguoi_tao", "nguoi_duyet"
    ).prefetch_related("lines", "lines__bien_the")

    if search_query:
        q = search_query.strip()
        qs = qs.filter(
            Q(ma_phieu_nhap_kho__icontains=q)
            | Q(nha_cung_cap__ten_nha_cung_cap__icontains=q)
            | Q(nha_cung_cap__ma_nha_cung_cap__icontains=q)
            | Q(ly_do_nhap__icontains=q)
        )
    if status:
        qs = qs.filter(trang_thai=status)
    if supplier_id and str(supplier_id).isdigit():
        qs = qs.filter(nha_cung_cap_id=int(supplier_id))
    if date_from and date_to and date_from > date_to:
        return qs.none()
    if date_from:
        qs = qs.filter(ngay_nhap__date__gte=date_from)
    if date_to:
        qs = qs.filter(ngay_nhap__date__lte=date_to)
    return qs.order_by("-ngay_nhap", "-id")


def get_import_activity_summary(receipts: QuerySet[PhieuNhapKho] | list[PhieuNhapKho]) -> dict:
    """Compute period import activity summary metrics for UC-4.11."""
    receipt_list = list(receipts)
    total_count = len(receipt_list)
    approved_count = 0
    pending_count = 0
    returned_count = 0
    approved_quantity = 0
    approved_amount = Decimal("0")
    total_amount = Decimal("0")

    for r in receipt_list:
        total_amount += r.tong_tien
        if r.trang_thai == PhieuNhapKho.Status.APPROVED:
            approved_count += 1
            approved_amount += r.tong_tien
            approved_quantity += sum(line.so_luong for line in r.lines.all())
        elif r.trang_thai == PhieuNhapKho.Status.PENDING_APPROVAL:
            pending_count += 1
        elif r.trang_thai == PhieuNhapKho.Status.RETURNED:
            returned_count += 1

    return {
        "total_count": total_count,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "returned_count": returned_count,
        "approved_quantity": approved_quantity,
        "approved_amount": approved_amount,
        "total_amount": total_amount,
    }


def get_all_suppliers(search_query: str = "") -> QuerySet[NhaCungCap]:
    qs = NhaCungCap.objects.all()
    if search_query:
        q = search_query.strip()
        qs = qs.filter(
            Q(ma_nha_cung_cap__icontains=q)
            | Q(ten_nha_cung_cap__icontains=q)
            | Q(sdt__icontains=q)
        )
    return qs.order_by("ma_nha_cung_cap")
