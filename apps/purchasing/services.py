"""
Warehouse Import & Supplier Management Services (Phase 3 - UC-4.1 to UC-4.11).
Enforces DEC-01: Stock increases ONLY when ADMIN approves an import receipt (UC-4.9).
"""
from dataclasses import dataclass
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User
from apps.accounts.permissions import assert_can_manage_imports, assert_roles
from apps.branches.models import CoSo
from apps.catalog.models import BienThe
from apps.inventory.models import StockMovement
from apps.inventory.services import StockDeltaSpec, apply_stock_movements
from apps.notifications.models import ThongBao
from apps.notifications.services import notify_admins, notify_branch_managers
from apps.purchasing.models import ChiTietPhieuNhapKho, NhaCungCap, PhieuNhapKho


@dataclass
class ImportLineSpec:
    variant_id: int
    so_luong: int
    don_gia: Decimal
    chiet_khau: Decimal = Decimal("0")
    ghi_chu: str = ""


def generate_next_import_code() -> str:
    prefix = f"PNK-{timezone.localdate().strftime('%Y%m%d')}-"
    last = (
        PhieuNhapKho.objects.filter(ma_phieu_nhap_kho__startswith=prefix)
        .order_by("-ma_phieu_nhap_kho")
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.ma_phieu_nhap_kho.split("-")[-1]) + 1
        except ValueError:
            seq = PhieuNhapKho.objects.count() + 1
    return f"{prefix}{seq:03d}"


def create_supplier(*, actor: User, ma_nha_cung_cap: str, ten_nha_cung_cap: str, dia_chi: str, sdt: str) -> NhaCungCap:
    """Create a new supplier (UC-4.11)."""
    assert_can_manage_imports(actor)
    code = ma_nha_cung_cap.strip().upper()
    if not code or not ten_nha_cung_cap.strip() or not dia_chi.strip() or not sdt.strip():
        raise ValidationError("Vui lòng nhập đầy đủ Mã nhà cung cấp, Tên nhà cung cấp, Địa chỉ và Số điện thoại.")
    if NhaCungCap.objects.filter(ma_nha_cung_cap__iexact=code).exists():
        raise ValidationError({"ma_nha_cung_cap": f"Mã nhà cung cấp '{code}' đã tồn tại trong hệ thống."})
    return NhaCungCap.objects.create(
        ma_nha_cung_cap=code,
        ten_nha_cung_cap=ten_nha_cung_cap.strip(),
        dia_chi=dia_chi.strip(),
        sdt=sdt.strip(),
    )


def _validate_and_build_lines(line_specs: list[ImportLineSpec]) -> tuple[list[dict], Decimal]:
    if not line_specs:
        raise ValidationError("Phiếu nhập kho phải có ít nhất 1 dòng hàng hóa.")
    seen_variants = set()
    validated_lines = []
    grand_total = Decimal("0")

    for idx, spec in enumerate(line_specs, start=1):
        variant = BienThe.objects.select_related("san_pham").filter(id=spec.variant_id).first()
        if not variant or variant.san_pham.trang_thai != "ACTIVE" or variant.trang_thai != "ACTIVE":
            raise ValidationError(f"Dòng {idx}: Mã hàng / SKU không tồn tại hoặc đã ngừng kinh doanh.")
        if variant.id in seen_variants:
            raise ValidationError(f"Dòng {idx}: Sản phẩm {variant.ma_sku} bị trùng lặp trên cùng một phiếu nhập.")
        seen_variants.add(variant.id)

        qty = int(spec.so_luong)
        if qty <= 0:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Số lượng nhập phải lớn hơn 0.")
        price = Decimal(str(spec.don_gia))
        if price < 0:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Đơn giá nhập không được âm.")
        disc = Decimal(str(spec.chiet_khau or "0"))
        if disc < 0:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Chiết khấu không được âm.")
        gross = Decimal(qty) * price
        if disc > gross:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Chiết khấu không được vượt quá thành tiền dòng hàng.")
        line_total = gross - disc
        grand_total += line_total
        validated_lines.append(
            {
                "variant": variant,
                "so_luong": qty,
                "don_gia": price,
                "chiet_khau": disc,
                "thanh_tien": line_total,
                "ghi_chu": (spec.ghi_chu or "").strip(),
            }
        )
    return validated_lines, grand_total


@transaction.atomic
def create_import_receipt(
    *,
    actor: User,
    nha_cung_cap: NhaCungCap,
    line_specs: list[ImportLineSpec],
    co_so_nhan: CoSo | None = None,
    ma_phieu_nhap_kho: str = "",
    ngay_nhap=None,
    ly_do_nhap: str = "Nhập hàng từ nhà cung cấp",
    ghi_chu: str = "",
    submit_for_approval: bool = True,
) -> PhieuNhapKho:
    """Create a warehouse import receipt at Central Warehouse (UC-4.1, UC-4.2)."""
    target_branch = co_so_nhan or CoSo.get_central_warehouse()
    if not target_branch:
        raise ValidationError("Chưa cấu hình Cơ sở 1 (Kho tổng) để nhận hàng nhập kho.")
    assert_can_manage_imports(actor, target_branch)

    code = (ma_phieu_nhap_kho or "").strip().upper() or generate_next_import_code()
    if PhieuNhapKho.objects.filter(ma_phieu_nhap_kho__iexact=code).exists():
        raise ValidationError({"ma_phieu_nhap_kho": f"Mã phiếu nhập kho '{code}' đã tồn tại."})

    validated_lines, grand_total = _validate_and_build_lines(line_specs)
    status = PhieuNhapKho.Status.PENDING_APPROVAL if submit_for_approval else PhieuNhapKho.Status.DRAFT

    receipt = PhieuNhapKho.objects.create(
        ma_phieu_nhap_kho=code,
        nha_cung_cap=nha_cung_cap,
        co_so_nhan=target_branch,
        dia_chi=nha_cung_cap.dia_chi,
        sdt=nha_cung_cap.sdt,
        ngay_nhap=ngay_nhap or timezone.now(),
        ly_do_nhap=(ly_do_nhap or "Nhập hàng từ nhà cung cấp").strip(),
        tong_tien=grand_total,
        trang_thai=status,
        ghi_chu=(ghi_chu or "").strip(),
        nguoi_tao=actor,
    )

    for item in validated_lines:
        ChiTietPhieuNhapKho.objects.create(
            phieu_nhap_kho=receipt,
            bien_the=item["variant"],
            so_luong=item["so_luong"],
            don_gia=item["don_gia"],
            chiet_khau=item["chiet_khau"],
            thanh_tien=item["thanh_tien"],
            ghi_chu=item["ghi_chu"],
        )

    if status == PhieuNhapKho.Status.PENDING_APPROVAL:
        try:
            url = reverse("purchasing:import_detail", args=[receipt.id])
        except Exception:
            url = "/purchasing/"
        notify_admins(
            notification_type=ThongBao.NotificationType.IMPORT_SUBMITTED,
            title=f"Phiếu nhập kho mới chờ duyệt: {receipt.ma_phieu_nhap_kho}",
            content=(
                f"Người lập: {actor.display_name} ({target_branch.ten_co_so}) | "
                f"NCC: {nha_cung_cap.ten_nha_cung_cap} | Tổng tiền: {grand_total:,.0f} VNĐ."
            ),
            branch=target_branch,
            related_entity_type="PhieuNhapKho",
            related_entity_id=receipt.id,
            target_url=url,
        )

    return receipt


@transaction.atomic
def update_import_receipt(
    *,
    actor: User,
    receipt: PhieuNhapKho,
    nha_cung_cap: NhaCungCap,
    line_specs: list[ImportLineSpec],
    ly_do_nhap: str = "",
    ghi_chu: str = "",
    submit_for_approval: bool = True,
) -> PhieuNhapKho:
    """Update an unapproved import receipt (UC-4.7)."""
    receipt = PhieuNhapKho.objects.select_for_update().get(pk=receipt.pk)
    assert_can_manage_imports(actor, receipt.co_so_nhan)
    if not receipt.is_editable:
        raise ValidationError("Không thể chỉnh sửa phiếu nhập kho đã được phê duyệt.")

    validated_lines, grand_total = _validate_and_build_lines(line_specs)
    receipt.nha_cung_cap = nha_cung_cap
    receipt.dia_chi = nha_cung_cap.dia_chi
    receipt.sdt = nha_cung_cap.sdt
    if ly_do_nhap:
        receipt.ly_do_nhap = ly_do_nhap.strip()
    receipt.ghi_chu = (ghi_chu or "").strip()
    receipt.tong_tien = grand_total
    if submit_for_approval:
        receipt.trang_thai = PhieuNhapKho.Status.PENDING_APPROVAL
    receipt.save()

    receipt.lines.all().delete()
    for item in validated_lines:
        ChiTietPhieuNhapKho.objects.create(
            phieu_nhap_kho=receipt,
            bien_the=item["variant"],
            so_luong=item["so_luong"],
            don_gia=item["don_gia"],
            chiet_khau=item["chiet_khau"],
            thanh_tien=item["thanh_tien"],
            ghi_chu=item["ghi_chu"],
        )

    return receipt


@transaction.atomic
def delete_import_receipt(*, actor: User, receipt: PhieuNhapKho) -> str:
    """Delete an unapproved import receipt (UC-4.8)."""
    receipt = PhieuNhapKho.objects.select_for_update().get(pk=receipt.pk)
    assert_can_manage_imports(actor, receipt.co_so_nhan)
    if not receipt.is_deletable:
        raise ValidationError("Không thể xóa phiếu nhập kho đã được phê duyệt và ghi nhận tồn kho.")
    code = receipt.ma_phieu_nhap_kho
    receipt.delete()
    return code


@transaction.atomic
def approve_import_receipt(*, actor: User, receipt: PhieuNhapKho) -> PhieuNhapKho:
    """
    Approve an import receipt (UC-4.9 - ADMIN only).
    Increases stock at `receipt.co_so_nhan` and records `IMPORT_IN` movements.
    """
    assert_roles(actor, User.Role.ADMIN)
    receipt = (
        PhieuNhapKho.objects.select_for_update()
        .select_related("co_so_nhan", "nha_cung_cap")
        .get(pk=receipt.pk)
    )
    if receipt.trang_thai == PhieuNhapKho.Status.APPROVED:
        raise ValidationError(f"Phiếu nhập kho {receipt.ma_phieu_nhap_kho} đã được phê duyệt trước đó.")
    if receipt.trang_thai not in {PhieuNhapKho.Status.PENDING_APPROVAL, PhieuNhapKho.Status.DRAFT, PhieuNhapKho.Status.RETURNED}:
        raise ValidationError("Trạng thái phiếu nhập kho không hợp lệ để phê duyệt.")

    lines = list(receipt.lines.select_related("bien_the", "bien_the__san_pham").all())
    if not lines:
        raise ValidationError("Phiếu nhập kho không có chi tiết hàng hóa để phê duyệt.")

    now = timezone.now()
    deltas = [
        StockDeltaSpec(
            variant=line.bien_the,
            quantity_delta=line.so_luong,
            unit_price_snapshot=line.don_gia,
            source_line_id=line.id,
            idempotency_key=f"IMPORT_APPROVE:{receipt.id}:LINE:{line.id}",
            notes=f"Nhập kho theo phiếu {receipt.ma_phieu_nhap_kho} ({receipt.nha_cung_cap.ten_nha_cung_cap})",
        )
        for line in lines
    ]

    apply_stock_movements(
        branch=receipt.co_so_nhan,
        deltas=deltas,
        movement_type=StockMovement.MovementType.IMPORT_IN,
        source_doc_type="PhieuNhapKho",
        source_doc_id=receipt.id,
        source_doc_code=receipt.ma_phieu_nhap_kho,
        actor=actor,
        effective_at=now,
    )

    receipt.trang_thai = PhieuNhapKho.Status.APPROVED
    receipt.nguoi_duyet = actor
    receipt.thoi_gian_duyet = now
    receipt.ly_do_tra_lai = ""
    receipt.save(update_fields=["trang_thai", "nguoi_duyet", "thoi_gian_duyet", "ly_do_tra_lai", "updated_at"])

    try:
        url = reverse("purchasing:import_detail", args=[receipt.id])
    except Exception:
        url = "/purchasing/"
    notify_branch_managers(
        branch=receipt.co_so_nhan,
        notification_type=ThongBao.NotificationType.IMPORT_APPROVED,
        title=f"Đã duyệt phiếu nhập kho {receipt.ma_phieu_nhap_kho}",
        content=f"Quản trị viên {actor.display_name} đã phê duyệt phiếu nhập kho {receipt.ma_phieu_nhap_kho}. Tồn kho đã được cộng.",
        related_entity_type="PhieuNhapKho",
        related_entity_id=receipt.id,
        target_url=url,
    )

    return receipt


@transaction.atomic
def return_import_receipt(*, actor: User, receipt: PhieuNhapKho, reason: str = "") -> PhieuNhapKho:
    """Return an import receipt to the creator for revision without changing stock (UC-4.9)."""
    assert_roles(actor, User.Role.ADMIN)
    receipt = PhieuNhapKho.objects.select_for_update().get(pk=receipt.pk)
    if receipt.trang_thai == PhieuNhapKho.Status.APPROVED:
        raise ValidationError("Không thể trả lại phiếu nhập kho đã được phê duyệt.")
    if receipt.trang_thai == PhieuNhapKho.Status.RETURNED:
        raise ValidationError("Phiếu nhập kho này đã ở trạng thái trả lại chỉnh sửa.")
    clean_reason = (reason or "Cần kiểm tra và bổ sung lại thông tin chứng từ nhập kho.").strip()
    receipt.trang_thai = PhieuNhapKho.Status.RETURNED
    receipt.nguoi_duyet = actor
    receipt.thoi_gian_duyet = timezone.now()
    receipt.ly_do_tra_lai = clean_reason
    receipt.save(update_fields=["trang_thai", "nguoi_duyet", "thoi_gian_duyet", "ly_do_tra_lai", "updated_at"])

    try:
        url = reverse("purchasing:import_detail", args=[receipt.id])
    except Exception:
        url = "/purchasing/"
    notify_branch_managers(
        branch=receipt.co_so_nhan,
        notification_type=ThongBao.NotificationType.IMPORT_RETURNED,
        title=f"Yêu cầu chỉnh sửa phiếu nhập {receipt.ma_phieu_nhap_kho}",
        content=f"Phiếu nhập {receipt.ma_phieu_nhap_kho} được trả lại để chỉnh sửa. Lý do: {clean_reason}",
        related_entity_type="PhieuNhapKho",
        related_entity_id=receipt.id,
        target_url=url,
    )
    return receipt
