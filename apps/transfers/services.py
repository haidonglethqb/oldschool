"""
Interbranch Transfer Services (Phase 5 - UC-5.3 & Hình 6 of Specification).
Implements two-step stock accounting:
1. REQUESTED -> ACCEPTED / REJECTED by source branch manager (`co_so_xuat`).
2. DISPATCHED (`Xuất điều chuyển`): Atomically deducts `so_luong_xuat` from `co_so_xuat`
   with `TRANSFER_OUT` ledger movement. Destination stock is NOT increased yet (in-transit).
3. RECEIVED / RECEIVED_WITH_SHORTAGE (`Xác nhận nhận hàng`): Atomically increases
   `so_luong_nhan` at `co_so_nhan` with `TRANSFER_IN` ledger movement.
"""
from dataclasses import dataclass
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
from apps.notifications.services import notify_branch_managers
from apps.transfers.models import ChiTietPhieuDieuChuyen, PhieuDieuChuyen


@dataclass
class TransferRequestLineSpec:
    variant_id: int
    so_luong_yeu_cau: int
    ghi_chu: str = ""


def generate_next_transfer_code(source_branch: CoSo, dest_branch: CoSo) -> str:
    prefix = f"PDC-{source_branch.ma_co_so}-{dest_branch.ma_co_so}-{timezone.localdate().strftime('%Y%m%d')}-"
    last = (
        PhieuDieuChuyen.objects.filter(ma_phieu_dieu_chuyen__startswith=prefix)
        .order_by("-ma_phieu_dieu_chuyen")
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.ma_phieu_dieu_chuyen.split("-")[-1]) + 1
        except ValueError:
            seq = PhieuDieuChuyen.objects.count() + 1
    return f"{prefix}{seq:03d}"


@transaction.atomic
def create_transfer_request(
    *,
    actor: User,
    co_so_xuat: CoSo,
    co_so_nhan: CoSo,
    line_specs: list[TransferRequestLineSpec],
    ma_phieu_dieu_chuyen: str = "",
    ly_do: str = "Bổ sung tồn kho cơ sở thiếu hàng",
    ghi_chu: str = "",
) -> PhieuDieuChuyen:
    """
    Create an Interbranch Transfer Request (UC-5.3).
    Typically initiated by the receiving branch (`co_so_nhan`) or by ADMIN / source branch.
    For MANAGER, the actor must belong to either `co_so_nhan` or `co_so_xuat`.
    """
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    if co_so_xuat.id == co_so_nhan.id:
        raise ValidationError("Cơ sở xuất và Cơ sở nhận phải khác nhau.")
    if actor.role == User.Role.MANAGER and actor.branch_id not in {co_so_xuat.id, co_so_nhan.id}:
        raise PermissionDenied("Quản lý cơ sở chỉ được tạo phiếu điều chuyển liên quan đến cơ sở của mình.")

    if not line_specs:
        raise ValidationError("Phiếu điều chuyển phải có ít nhất 1 dòng hàng hóa.")

    code = (ma_phieu_dieu_chuyen or "").strip().upper() or generate_next_transfer_code(co_so_xuat, co_so_nhan)
    if PhieuDieuChuyen.objects.filter(ma_phieu_dieu_chuyen__iexact=code).exists():
        raise ValidationError({"ma_phieu_dieu_chuyen": f"Mã phiếu điều chuyển '{code}' đã tồn tại."})

    seen = set()
    validated = []
    for idx, spec in enumerate(line_specs, start=1):
        variant = BienThe.objects.select_related("san_pham").filter(id=spec.variant_id).first()
        if not variant or variant.san_pham.trang_thai != "ACTIVE" or variant.trang_thai != "ACTIVE":
            raise ValidationError(f"Dòng {idx}: Sản phẩm không tồn tại hoặc ngừng kinh doanh.")
        if variant.id in seen:
            raise ValidationError(f"Dòng {idx}: Sản phẩm {variant.ma_sku} bị trùng lặp.")
        seen.add(variant.id)
        qty = int(spec.so_luong_yeu_cau)
        if qty <= 0:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Số lượng yêu cầu phải lớn hơn 0.")
        validated.append((variant, qty, (spec.ghi_chu or "").strip()))

    transfer = PhieuDieuChuyen.objects.create(
        ma_phieu_dieu_chuyen=code,
        co_so_xuat=co_so_xuat,
        co_so_nhan=co_so_nhan,
        ngay_dieu_chuyen=timezone.localdate(),
        dia_chi_nhan=co_so_nhan.dia_chi,
        ly_do=(ly_do or "Bổ sung tồn kho cơ sở thiếu hàng").strip(),
        trang_thai=PhieuDieuChuyen.Status.REQUESTED,
        ghi_chu=(ghi_chu or "").strip(),
        nguoi_tao=actor,
    )

    for variant, qty, note in validated:
        ChiTietPhieuDieuChuyen.objects.create(
            phieu_dieu_chuyen=transfer,
            bien_the=variant,
            so_luong_yeu_cau=qty,
            so_luong_xuat=qty,
            so_luong_nhan=0,
            ghi_chu=note,
        )

    try:
        url = reverse("transfers:transfer_detail", args=[transfer.id])
    except Exception:
        url = "/transfers/"
    notify_branch_managers(
        branch=co_so_xuat,
        notification_type=ThongBao.NotificationType.TRANSFER_REQUESTED,
        title=f"Yêu cầu điều chuyển từ {co_so_nhan.ma_co_so}: {transfer.ma_phieu_dieu_chuyen}",
        content=(
            f"{co_so_nhan.ten_co_so} yêu cầu điều chuyển {len(validated)} mặt hàng từ {co_so_xuat.ten_co_so}. "
            f"Lý do: {transfer.ly_do}."
        ),
        related_entity_type="PhieuDieuChuyen",
        related_entity_id=transfer.id,
        target_url=url,
    )
    return transfer


@transaction.atomic
def accept_transfer(*, actor: User, transfer: PhieuDieuChuyen) -> PhieuDieuChuyen:
    """Source branch manager accepts the transfer request before dispatching."""
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    transfer = PhieuDieuChuyen.objects.select_for_update().select_related("co_so_xuat", "co_so_nhan").get(pk=transfer.pk)
    assert_branch_access(actor, transfer.co_so_xuat)
    if transfer.trang_thai != PhieuDieuChuyen.Status.REQUESTED:
        raise ValidationError("Chỉ có thể chấp nhận phiếu điều chuyển đang ở trạng thái Chờ xác nhận.")
    transfer.trang_thai = PhieuDieuChuyen.Status.ACCEPTED
    transfer.save(update_fields=["trang_thai", "updated_at"])
    return transfer


@transaction.atomic
def reject_transfer(*, actor: User, transfer: PhieuDieuChuyen, reason: str = "") -> PhieuDieuChuyen:
    """Source branch manager rejects the transfer request when stock cannot be supplied."""
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    transfer = PhieuDieuChuyen.objects.select_for_update().select_related("co_so_xuat", "co_so_nhan").get(pk=transfer.pk)
    assert_branch_access(actor, transfer.co_so_xuat)
    if transfer.trang_thai not in {PhieuDieuChuyen.Status.REQUESTED, PhieuDieuChuyen.Status.ACCEPTED}:
        raise ValidationError("Không thể từ chối phiếu điều chuyển đã xuất đi hoặc đã hoàn tất.")
    transfer.trang_thai = PhieuDieuChuyen.Status.REJECTED
    if reason:
        transfer.ghi_chu = f"{transfer.ghi_chu} | Từ chối: {reason.strip()}".strip(" |")
    transfer.save(update_fields=["trang_thai", "ghi_chu", "updated_at"])

    try:
        url = reverse("transfers:transfer_detail", args=[transfer.id])
    except Exception:
        url = "/transfers/"
    notify_branch_managers(
        branch=transfer.co_so_nhan,
        notification_type=ThongBao.NotificationType.SYSTEM,
        title=f"Từ chối điều chuyển {transfer.ma_phieu_dieu_chuyen}",
        content=f"{transfer.co_so_xuat.ten_co_so} từ chối yêu cầu điều chuyển {transfer.ma_phieu_dieu_chuyen}. {reason}",
        related_entity_type="PhieuDieuChuyen",
        related_entity_id=transfer.id,
        target_url=url,
    )
    return transfer


@transaction.atomic
def dispatch_transfer(
    *,
    actor: User,
    transfer: PhieuDieuChuyen,
    dispatched_quantities: dict[int, int] | None = None,
) -> PhieuDieuChuyen:
    """
    Step 1 of stock accounting: Source branch (`co_so_xuat`) dispatches goods (`DISPATCHED`).
    Deducts `so_luong_xuat` from `co_so_xuat` via `TRANSFER_OUT`.
    Destination branch stock (`co_so_nhan`) is NOT increased until `receive_transfer`.
    """
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    transfer = (
        PhieuDieuChuyen.objects.select_for_update()
        .select_related("co_so_xuat", "co_so_nhan")
        .get(pk=transfer.pk)
    )
    assert_branch_access(actor, transfer.co_so_xuat)
    if transfer.trang_thai == PhieuDieuChuyen.Status.DISPATCHED:
        raise ValidationError(f"Phiếu điều chuyển {transfer.ma_phieu_dieu_chuyen} đã được xuất đi trước đó.")
    if transfer.trang_thai not in {PhieuDieuChuyen.Status.REQUESTED, PhieuDieuChuyen.Status.ACCEPTED}:
        raise ValidationError("Trạng thái phiếu điều chuyển không hợp lệ để xuất kho.")

    lines = list(transfer.lines.select_related("bien_the", "bien_the__san_pham").all())
    if not lines:
        raise ValidationError("Phiếu điều chuyển không có dòng hàng hóa.")

    deltas = []
    for line in lines:
        qty_out = (
            int(dispatched_quantities[line.id])
            if dispatched_quantities and line.id in dispatched_quantities
            else (line.so_luong_xuat if line.so_luong_xuat > 0 else line.so_luong_yeu_cau)
        )
        if qty_out <= 0:
            raise ValidationError(f"Số lượng thực xuất của SKU {line.bien_the.ma_sku} phải lớn hơn 0.")
        if qty_out > line.so_luong_yeu_cau:
            raise ValidationError(
                f"Số lượng thực xuất ({qty_out}) của SKU {line.bien_the.ma_sku} không được vượt quá số lượng yêu cầu ({line.so_luong_yeu_cau})."
            )
        line.so_luong_xuat = qty_out
        line.save(update_fields=["so_luong_xuat"])

        deltas.append(
            StockDeltaSpec(
                variant=line.bien_the,
                quantity_delta=-qty_out,
                unit_price_snapshot=line.bien_the.don_gia,
                source_line_id=line.id,
                idempotency_key=f"TRANSFER_DISPATCH:{transfer.id}:LINE:{line.id}",
                notes=f"Xuất điều chuyển {transfer.ma_phieu_dieu_chuyen} từ {transfer.co_so_xuat.ma_co_so} sang {transfer.co_so_nhan.ma_co_so}",
            )
        )

    now = timezone.now()
    apply_stock_movements(
        branch=transfer.co_so_xuat,
        deltas=deltas,
        movement_type=StockMovement.MovementType.TRANSFER_OUT,
        source_doc_type="PhieuDieuChuyen",
        source_doc_id=transfer.id,
        source_doc_code=transfer.ma_phieu_dieu_chuyen,
        actor=actor,
        effective_at=now,
    )

    transfer.trang_thai = PhieuDieuChuyen.Status.DISPATCHED
    transfer.nguoi_xuat = actor
    transfer.thoi_gian_xuat = now
    transfer.save(update_fields=["trang_thai", "nguoi_xuat", "thoi_gian_xuat", "updated_at"])

    try:
        url = reverse("transfers:transfer_detail", args=[transfer.id])
    except Exception:
        url = "/transfers/"
    notify_branch_managers(
        branch=transfer.co_so_nhan,
        notification_type=ThongBao.NotificationType.TRANSFER_DISPATCHED,
        title=f"Hàng điều chuyển đang đến ({transfer.ma_phieu_dieu_chuyen})",
        content=(
            f"{transfer.co_so_xuat.ten_co_so} đã xuất hàng điều chuyển theo phiếu {transfer.ma_phieu_dieu_chuyen}. "
            f"Vui lòng kiểm đếm và xác nhận khi nhận hàng."
        ),
        related_entity_type="PhieuDieuChuyen",
        related_entity_id=transfer.id,
        target_url=url,
    )
    return transfer


@transaction.atomic
def receive_transfer(
    *,
    actor: User,
    transfer: PhieuDieuChuyen,
    received_quantities: dict[int, int] | None = None,
    shortage_note: str = "",
) -> PhieuDieuChuyen:
    """
    Step 2 of stock accounting: Destination branch (`co_so_nhan`) confirms receipt.
    Increases `co_so_nhan` stock by `so_luong_nhan` via `TRANSFER_IN`.
    If any line has `so_luong_nhan < so_luong_xuat`, status becomes `RECEIVED_WITH_SHORTAGE`.
    """
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    transfer = (
        PhieuDieuChuyen.objects.select_for_update()
        .select_related("co_so_xuat", "co_so_nhan")
        .get(pk=transfer.pk)
    )
    assert_branch_access(actor, transfer.co_so_nhan)
    if transfer.trang_thai in {PhieuDieuChuyen.Status.RECEIVED, PhieuDieuChuyen.Status.RECEIVED_WITH_SHORTAGE}:
        raise ValidationError(f"Phiếu điều chuyển {transfer.ma_phieu_dieu_chuyen} đã được xác nhận nhận hàng trước đó.")
    if transfer.trang_thai != PhieuDieuChuyen.Status.DISPATCHED:
        raise ValidationError("Chỉ có thể xác nhận nhận hàng cho phiếu điều chuyển đã xuất đi (Đang vận chuyển).")

    lines = list(transfer.lines.select_related("bien_the", "bien_the__san_pham").all())
    deltas = []
    has_shortage = False

    for line in lines:
        qty_in = (
            int(received_quantities[line.id])
            if received_quantities and line.id in received_quantities
            else line.so_luong_xuat
        )
        if qty_in < 0:
            raise ValidationError(f"Số lượng thực nhận của SKU {line.bien_the.ma_sku} không được âm.")
        if qty_in > line.so_luong_xuat:
            raise ValidationError(
                f"Số lượng thực nhận ({qty_in}) của SKU {line.bien_the.ma_sku} không được vượt quá số lượng đã xuất ({line.so_luong_xuat})."
            )
        if qty_in < line.so_luong_xuat:
            has_shortage = True

        line.so_luong_nhan = qty_in
        line.save(update_fields=["so_luong_nhan"])

        if qty_in > 0:
            deltas.append(
                StockDeltaSpec(
                    variant=line.bien_the,
                    quantity_delta=qty_in,
                    unit_price_snapshot=line.bien_the.don_gia,
                    source_line_id=line.id,
                    idempotency_key=f"TRANSFER_RECEIVE:{transfer.id}:LINE:{line.id}",
                    notes=f"Nhận điều chuyển {transfer.ma_phieu_dieu_chuyen} tại {transfer.co_so_nhan.ma_co_so}",
                )
            )

    if has_shortage and not (shortage_note or "").strip():
        raise ValidationError("Phát hiện thiếu hụt hàng điều chuyển. Vui lòng nhập ghi chú xử lý chênh lệch.")

    now = timezone.now()
    if deltas:
        apply_stock_movements(
            branch=transfer.co_so_nhan,
            deltas=deltas,
            movement_type=StockMovement.MovementType.TRANSFER_IN,
            source_doc_type="PhieuDieuChuyen",
            source_doc_id=transfer.id,
            source_doc_code=transfer.ma_phieu_dieu_chuyen,
            actor=actor,
            effective_at=now,
        )

    transfer.trang_thai = (
        PhieuDieuChuyen.Status.RECEIVED_WITH_SHORTAGE if has_shortage else PhieuDieuChuyen.Status.RECEIVED
    )
    transfer.nguoi_nhan = actor
    transfer.thoi_gian_nhan = now
    if shortage_note:
        transfer.ghi_chu_chenh_lech = shortage_note.strip()
    transfer.save(
        update_fields=["trang_thai", "nguoi_nhan", "thoi_gian_nhan", "ghi_chu_chenh_lech", "updated_at"]
    )

    try:
        url = reverse("transfers:transfer_detail", args=[transfer.id])
    except Exception:
        url = "/transfers/"
    notify_branch_managers(
        branch=transfer.co_so_xuat,
        notification_type=ThongBao.NotificationType.TRANSFER_RECEIVED,
        title=f"{transfer.co_so_nhan.ma_co_so} đã nhận điều chuyển {transfer.ma_phieu_dieu_chuyen}",
        content=(
            f"Trạng thái nhận: {transfer.get_trang_thai_display()}. "
            f"{transfer.ghi_chu_chenh_lech}"
        ),
        related_entity_type="PhieuDieuChuyen",
        related_entity_id=transfer.id,
        target_url=url,
    )
    return transfer
