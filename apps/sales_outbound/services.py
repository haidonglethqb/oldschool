"""
Sales Outbound Request & Receipt Services (Phase 4 - UC-5.1, UC-5.2, UC-5.4 to UC-5.13).
Enforces:
- Branch isolation (Manager/Staff only operate on their own branch)
- Atomic stock deduction with `select_for_update()` ONLY when receipt is finalized (`COMPLETED`, UC-5.11)
- Automatic low-stock evaluation after deduction (UC-5.13)
- Strict separation between Sales Outbound (`PhieuXuatHangBan`) and Interbranch Transfer (`PhieuDieuChuyen`)
"""
from dataclasses import dataclass
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import User
from apps.accounts.permissions import assert_branch_access, assert_roles
from apps.branches.models import CoSo
from apps.catalog.models import BienThe
from apps.inventory.models import StockMovement, TonKho
from apps.inventory.services import StockDeltaSpec, apply_stock_movements
from apps.notifications.models import ThongBao
from apps.notifications.services import create_notification, notify_branch_managers
from apps.sales_outbound.models import (
    ChiTietPhieuXuatHangBan,
    ChiTietYeuCauXuatHang,
    PhieuXuatHangBan,
    YeuCauXuatHang,
)


@dataclass
class OutboundRequestLineSpec:
    variant_id: int
    so_luong: int


@dataclass
class OutboundReceiptLineSpec:
    variant_id: int
    so_luong: int
    don_gia: Decimal | None = None
    ghi_chu: str = ""


def generate_next_request_code(branch: CoSo) -> str:
    prefix = f"YCX-{branch.ma_co_so}-{timezone.localdate().strftime('%Y%m%d')}-"
    last = (
        YeuCauXuatHang.objects.filter(ma_yeu_cau__startswith=prefix)
        .order_by("-ma_yeu_cau")
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.ma_yeu_cau.split("-")[-1]) + 1
        except ValueError:
            seq = YeuCauXuatHang.objects.count() + 1
    return f"{prefix}{seq:03d}"


def generate_next_outbound_code(branch: CoSo) -> str:
    prefix = f"PXB-{branch.ma_co_so}-{timezone.localdate().strftime('%Y%m%d')}-"
    last = (
        PhieuXuatHangBan.objects.filter(ma_phieu_xuat_hang_ban__startswith=prefix)
        .order_by("-ma_phieu_xuat_hang_ban")
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.ma_phieu_xuat_hang_ban.split("-")[-1]) + 1
        except ValueError:
            seq = PhieuXuatHangBan.objects.count() + 1
    return f"{prefix}{seq:03d}"


@transaction.atomic
def create_outbound_request(
    *,
    actor: User,
    co_so: CoSo,
    line_specs: list[OutboundRequestLineSpec],
    ten_khach_hang: str = "Khách lẻ tại quầy",
    sdt_khach_hang: str = "",
    dia_chi_giao: str = "",
    phuong_thuc_giao: str = YeuCauXuatHang.DeliveryMethod.COUNTER,
    ghi_chu: str = "",
) -> YeuCauXuatHang:
    """Create a Sales Outbound Request from Staff or Manager (Hình 5 - Proposed Workflow)."""
    assert_roles(actor, User.Role.STAFF, User.Role.MANAGER, User.Role.ADMIN)
    assert_branch_access(actor, co_so)

    if not line_specs:
        raise ValidationError("Yêu cầu xuất kho phải có ít nhất 1 sản phẩm.")

    seen = set()
    validated = []
    for idx, spec in enumerate(line_specs, start=1):
        variant = BienThe.objects.select_related("san_pham").filter(id=spec.variant_id).first()
        if not variant or variant.san_pham.trang_thai != "ACTIVE" or variant.trang_thai != "ACTIVE":
            raise ValidationError(f"Dòng {idx}: Sản phẩm không tồn tại hoặc đã ngừng kinh doanh.")
        if variant.id in seen:
            raise ValidationError(f"Dòng {idx}: Sản phẩm {variant.ma_sku} bị trùng lặp.")
        seen.add(variant.id)
        qty = int(spec.so_luong)
        if qty <= 0:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Số lượng yêu cầu phải lớn hơn 0.")
        validated.append((variant, qty))

    req = YeuCauXuatHang.objects.create(
        ma_yeu_cau=generate_next_request_code(co_so),
        co_so=co_so,
        ten_khach_hang=(ten_khach_hang or "Khách lẻ tại quầy").strip(),
        sdt_khach_hang=(sdt_khach_hang or "").strip(),
        dia_chi_giao=(dia_chi_giao or co_so.dia_chi).strip(),
        phuong_thuc_giao=phuong_thuc_giao or YeuCauXuatHang.DeliveryMethod.COUNTER,
        ghi_chu=(ghi_chu or "").strip(),
        trang_thai=YeuCauXuatHang.Status.PENDING,
        nguoi_yeu_cau=actor,
    )

    for variant, qty in validated:
        ChiTietYeuCauXuatHang.objects.create(
            yeu_cau=req,
            bien_the=variant,
            so_luong=qty,
        )

    try:
        url = reverse("sales_outbound:request_list")
    except Exception:
        url = "/outbound/requests/"
    notify_branch_managers(
        branch=co_so,
        notification_type=ThongBao.NotificationType.OUTBOUND_REQUESTED,
        title=f"[{co_so.ma_co_so}] Yêu cầu xuất bán mới: {req.ma_yeu_cau}",
        content=f"Nhân viên {actor.display_name} gửi yêu cầu xuất hàng bán ({req.ten_khach_hang}).",
        related_entity_type="YeuCauXuatHang",
        related_entity_id=req.id,
        target_url=url,
    )
    return req


@transaction.atomic
def reject_outbound_request(*, actor: User, request_obj: YeuCauXuatHang, reason: str = "") -> YeuCauXuatHang:
    """Reject a sales outbound request when stock is unavailable or request is cancelled."""
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    request_obj = YeuCauXuatHang.objects.select_for_update().get(pk=request_obj.pk)
    assert_branch_access(actor, request_obj.co_so)
    if request_obj.trang_thai != YeuCauXuatHang.Status.PENDING:
        raise ValidationError("Chỉ có thể từ chối yêu cầu xuất đang ở trạng thái chờ xử lý.")

    request_obj.trang_thai = YeuCauXuatHang.Status.REJECTED
    request_obj.nguoi_xu_ly = actor
    request_obj.thoi_gian_xu_ly = timezone.now()
    if reason:
        request_obj.ghi_chu = f"{request_obj.ghi_chu} | Lý do từ chối: {reason.strip()}".strip(" |")
    request_obj.save()

    try:
        req_url = reverse("sales_outbound:request_list")
    except Exception:
        req_url = "/outbound/requests/"

    create_notification(
        recipient=request_obj.nguoi_yeu_cau,
        branch=request_obj.co_so,
        notification_type=ThongBao.NotificationType.SYSTEM,
        title=f"Yêu cầu xuất {request_obj.ma_yeu_cau} bị từ chối",
        content=f"Quản lý {actor.display_name} đã từ chối yêu cầu xuất {request_obj.ma_yeu_cau}. {reason}",
        related_entity_type="YeuCauXuatHang",
        related_entity_id=request_obj.id,
        target_url=req_url,
    )
    return request_obj


def _validate_outbound_lines(branch: CoSo, line_specs: list[OutboundReceiptLineSpec]) -> tuple[list[dict], Decimal]:
    if not line_specs:
        raise ValidationError("Phiếu xuất hàng bán phải có ít nhất 1 dòng hàng hóa.")
    seen = set()
    validated = []
    grand_total = Decimal("0")

    for idx, spec in enumerate(line_specs, start=1):
        variant = BienThe.objects.select_related("san_pham").filter(id=spec.variant_id).first()
        if not variant or variant.san_pham.trang_thai != "ACTIVE" or variant.trang_thai != "ACTIVE":
            raise ValidationError(f"Dòng {idx}: Sản phẩm không tồn tại hoặc đã ngừng kinh doanh.")
        if variant.id in seen:
            raise ValidationError(f"Dòng {idx}: Sản phẩm {variant.ma_sku} bị trùng lặp trên phiếu xuất.")
        seen.add(variant.id)

        qty = int(spec.so_luong)
        if qty <= 0:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Số lượng xuất kho phải lớn hơn 0.")

        # Pre-check current stock availability at creation/update time (UC-5.1, UC-5.2, UC-5.9)
        balance = TonKho.objects.filter(co_so=branch, bien_the=variant).first()
        avail = balance.so_luong if balance else 0
        if qty > avail:
            raise ValidationError(
                f"Dòng {idx} ({variant.ma_sku} - {variant.san_pham.ten_hang_hoa}): "
                f"Số lượng xuất ({qty}) vượt quá tồn kho hiện tại của {branch.ten_co_so} ({avail})."
            )

        price = Decimal(str(spec.don_gia)) if spec.don_gia is not None else variant.don_gia
        if price < 0:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Đơn giá xuất không được âm.")

        line_total = Decimal(qty) * price
        grand_total += line_total
        validated.append(
            {
                "variant": variant,
                "so_luong": qty,
                "don_gia": price,
                "thanh_tien": line_total,
                "ghi_chu": (spec.ghi_chu or "").strip(),
            }
        )
    return validated, grand_total


@transaction.atomic
def create_outbound_receipt(
    *,
    actor: User,
    co_so: CoSo,
    line_specs: list[OutboundReceiptLineSpec],
    ma_phieu_xuat_hang_ban: str = "",
    yeu_cau_xuat: YeuCauXuatHang | None = None,
    ten_khach_hang: str = "Khách mua lẻ",
    sdt: str = "",
    dia_chi: str = "",
    phuong_thuc_giao: str = PhieuXuatHangBan.DeliveryMethod.COUNTER,
    ghi_chu: str = "",
    finalize_immediately: bool = False,
) -> PhieuXuatHangBan:
    """Create a Sales Outbound Receipt (UC-5.1, UC-5.2)."""
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    assert_branch_access(actor, co_so)

    code = (ma_phieu_xuat_hang_ban or "").strip().upper() or generate_next_outbound_code(co_so)
    if PhieuXuatHangBan.objects.filter(ma_phieu_xuat_hang_ban__iexact=code).exists():
        raise ValidationError({"ma_phieu_xuat_hang_ban": f"Mã phiếu xuất '{code}' đã tồn tại."})

    if yeu_cau_xuat:
        yeu_cau_xuat = YeuCauXuatHang.objects.select_for_update().get(pk=yeu_cau_xuat.pk)
        if yeu_cau_xuat.co_so_id != co_so.id:
            raise ValidationError("Yêu cầu xuất không thuộc cùng cơ sở với phiếu xuất.")
        if yeu_cau_xuat.trang_thai != YeuCauXuatHang.Status.PENDING or PhieuXuatHangBan.objects.filter(yeu_cau_xuat=yeu_cau_xuat).exists():
            raise ValidationError("Yêu cầu xuất hàng này đã được lập phiếu xuất hoặc đã xử lý trước đó.")

    validated_lines, grand_total = _validate_outbound_lines(co_so, line_specs)

    receipt = PhieuXuatHangBan.objects.create(
        ma_phieu_xuat_hang_ban=code,
        co_so=co_so,
        yeu_cau_xuat=yeu_cau_xuat,
        ten_khach_hang=(ten_khach_hang or "Khách mua lẻ").strip(),
        sdt=(sdt or co_so.sdt).strip(),
        dia_chi=(dia_chi or co_so.dia_chi).strip(),
        phuong_thuc_giao=phuong_thuc_giao or PhieuXuatHangBan.DeliveryMethod.COUNTER,
        ngay_xuat=timezone.now(),
        tong_tien=grand_total,
        trang_thai=PhieuXuatHangBan.Status.PENDING,
        ghi_chu=(ghi_chu or "").strip(),
        nguoi_tao=actor,
    )

    for item in validated_lines:
        ChiTietPhieuXuatHangBan.objects.create(
            phieu_xuat_hang_ban=receipt,
            bien_the=item["variant"],
            so_luong=item["so_luong"],
            don_gia=item["don_gia"],
            thanh_tien=item["thanh_tien"],
            ghi_chu=item["ghi_chu"],
        )

    if yeu_cau_xuat:
        yeu_cau_xuat.trang_thai = YeuCauXuatHang.Status.PROCESSED
        yeu_cau_xuat.nguoi_xu_ly = actor
        yeu_cau_xuat.thoi_gian_xu_ly = timezone.now()
        yeu_cau_xuat.save(update_fields=["trang_thai", "nguoi_xu_ly", "thoi_gian_xu_ly"])

    if finalize_immediately:
        receipt = finalize_outbound_receipt(actor=actor, receipt=receipt)

    return receipt


@transaction.atomic
def update_outbound_receipt(
    *,
    actor: User,
    receipt: PhieuXuatHangBan,
    line_specs: list[OutboundReceiptLineSpec],
    ten_khach_hang: str = "",
    sdt: str = "",
    dia_chi: str = "",
    phuong_thuc_giao: str = "",
    ghi_chu: str = "",
) -> PhieuXuatHangBan:
    """Update an unfinalized Sales Outbound Receipt (UC-5.9)."""
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    receipt = PhieuXuatHangBan.objects.select_for_update().select_related("co_so").get(pk=receipt.pk)
    assert_branch_access(actor, receipt.co_so)
    if not receipt.is_editable:
        raise ValidationError("Phiếu xuất đã được ghi nhận xuất kho hoặc đã hủy, không thể chỉnh sửa.")

    validated_lines, grand_total = _validate_outbound_lines(receipt.co_so, line_specs)
    if ten_khach_hang:
        receipt.ten_khach_hang = ten_khach_hang.strip()
    if sdt:
        receipt.sdt = sdt.strip()
    if dia_chi:
        receipt.dia_chi = dia_chi.strip()
    if phuong_thuc_giao:
        receipt.phuong_thuc_giao = phuong_thuc_giao
    receipt.ghi_chu = (ghi_chu or "").strip()
    receipt.tong_tien = grand_total
    receipt.save()

    receipt.lines.all().delete()
    for item in validated_lines:
        ChiTietPhieuXuatHangBan.objects.create(
            phieu_xuat_hang_ban=receipt,
            bien_the=item["variant"],
            so_luong=item["so_luong"],
            don_gia=item["don_gia"],
            thanh_tien=item["thanh_tien"],
            ghi_chu=item["ghi_chu"],
        )
    return receipt


@transaction.atomic
def finalize_outbound_receipt(*, actor: User, receipt: PhieuXuatHangBan) -> PhieuXuatHangBan:
    """
    Finalize a Sales Outbound Receipt (`Ghi nhận xuất kho`, UC-5.11).
    Atomically locks branch stock rows, verifies sufficiency, deducts stock,
    creates `SALE_OUT` ledger movements, and triggers low-stock warnings (UC-5.13).
    """
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    receipt = (
        PhieuXuatHangBan.objects.select_for_update(of=("self",))
        .select_related("co_so", "yeu_cau_xuat")
        .get(pk=receipt.pk)
    )
    assert_branch_access(actor, receipt.co_so)
    if receipt.trang_thai == PhieuXuatHangBan.Status.COMPLETED:
        raise ValidationError(f"Phiếu xuất {receipt.ma_phieu_xuat_hang_ban} đã được ghi nhận xuất kho trước đó.")
    if receipt.trang_thai != PhieuXuatHangBan.Status.PENDING:
        raise ValidationError("Chỉ có thể ghi nhận xuất kho cho phiếu đang ở trạng thái Chờ ghi nhận.")

    lines = list(receipt.lines.select_related("bien_the", "bien_the__san_pham").all())
    if not lines:
        raise ValidationError("Phiếu xuất không có dòng hàng hóa nào để ghi nhận.")

    now = timezone.now()
    deltas = [
        StockDeltaSpec(
            variant=line.bien_the,
            quantity_delta=-line.so_luong,
            unit_price_snapshot=line.don_gia,
            source_line_id=line.id,
            idempotency_key=f"SALE_OUT_FINALIZE:{receipt.id}:LINE:{line.id}",
            notes=f"Xuất hàng bán theo phiếu {receipt.ma_phieu_xuat_hang_ban} ({receipt.ten_khach_hang})",
        )
        for line in lines
    ]

    apply_stock_movements(
        branch=receipt.co_so,
        deltas=deltas,
        movement_type=StockMovement.MovementType.SALE_OUT,
        source_doc_type="PhieuXuatHangBan",
        source_doc_id=receipt.id,
        source_doc_code=receipt.ma_phieu_xuat_hang_ban,
        actor=actor,
        effective_at=now,
    )

    receipt.trang_thai = PhieuXuatHangBan.Status.COMPLETED
    receipt.nguoi_ghi_nhan = actor
    receipt.thoi_gian_ghi_nhan = now
    receipt.save(update_fields=["trang_thai", "nguoi_ghi_nhan", "thoi_gian_ghi_nhan", "updated_at"])

    if receipt.yeu_cau_xuat_id and receipt.yeu_cau_xuat.nguoi_yeu_cau_id:
        try:
            url = reverse("sales_outbound:outbound_detail", args=[receipt.id])
        except Exception:
            url = "/outbound/"
        create_notification(
            recipient=receipt.yeu_cau_xuat.nguoi_yeu_cau,
            branch=receipt.co_so,
            notification_type=ThongBao.NotificationType.OUTBOUND_COMPLETED,
            title=f"Đã xuất kho cho yêu cầu {receipt.yeu_cau_xuat.ma_yeu_cau}",
            content=(
                f"Phiếu xuất {receipt.ma_phieu_xuat_hang_ban} đã được ghi nhận hoàn tất. "
                f"Phương thức: {receipt.get_phuong_thuc_giao_display()}."
            ),
            related_entity_type="PhieuXuatHangBan",
            related_entity_id=receipt.id,
            target_url=url,
        )

    return receipt


@transaction.atomic
def delete_outbound_receipt(*, actor: User, receipt: PhieuXuatHangBan) -> str:
    """Delete an unfinalized Sales Outbound Receipt (UC-5.10)."""
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    receipt = PhieuXuatHangBan.objects.select_for_update(of=("self",)).select_related("yeu_cau_xuat").get(pk=receipt.pk)
    assert_branch_access(actor, receipt.co_so)
    if not receipt.is_deletable:
        raise ValidationError("Không thể xóa phiếu xuất hàng bán đã được ghi nhận xuất kho.")
    linked_request = receipt.yeu_cau_xuat
    code = receipt.ma_phieu_xuat_hang_ban
    receipt.delete()
    if linked_request and linked_request.trang_thai == YeuCauXuatHang.Status.PROCESSED:
        linked_request.trang_thai = YeuCauXuatHang.Status.PENDING
        linked_request.nguoi_xu_ly = None
        linked_request.thoi_gian_xu_ly = None
        linked_request.save(update_fields=["trang_thai", "nguoi_xu_ly", "thoi_gian_xu_ly"])
    return code
