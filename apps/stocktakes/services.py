"""
Stocktake / Inventory Count Services (Phase 6 - UC-6.1 to UC-6.10).
Enforces:
- DEC-02: Only ADMIN can approve or reject a stocktake record (`UC-6.10`).
- DEC-03: Approving a stocktake record updates status and audit metadata (`APPROVED`)
  without silently overwriting physical stock (`TonKho.so_luong`).
- System quantity (`so_luong_he_thong`) is captured as an immutable snapshot at stocktake creation/update.
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
from apps.inventory.models import TonKho
from apps.notifications.models import ThongBao
from apps.notifications.services import notify_admins, notify_branch_managers
from apps.stocktakes.models import ChiTietKiemKe, KiemKe


@dataclass
class StocktakeLineSpec:
    variant_id: int
    so_luong_thuc_te: int
    xu_ly: str = ""
    ghi_chu: str = ""


def generate_next_stocktake_code(branch: CoSo) -> str:
    prefix = f"KK-{branch.ma_co_so}-{timezone.localdate().strftime('%Y%m%d')}-"
    last = (
        KiemKe.objects.filter(ma_kiem_ke__startswith=prefix)
        .order_by("-ma_kiem_ke")
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.ma_kiem_ke.split("-")[-1]) + 1
        except ValueError:
            seq = KiemKe.objects.count() + 1
    return f"{prefix}{seq:03d}"


def _validate_and_build_stocktake_lines(branch: CoSo, line_specs: list[StocktakeLineSpec]) -> list[dict]:
    if not line_specs:
        raise ValidationError("Biên bản kiểm kê phải có ít nhất 1 dòng hàng hóa.")
    seen = set()
    validated = []

    for idx, spec in enumerate(line_specs, start=1):
        variant = BienThe.objects.select_related("san_pham").filter(id=spec.variant_id).first()
        if not variant or variant.san_pham.trang_thai != "ACTIVE" or variant.trang_thai != "ACTIVE":
            raise ValidationError(f"Dòng {idx}: Mã hàng / SKU không tồn tại tại cơ sở kiểm kê.")
        if variant.id in seen:
            raise ValidationError(f"Dòng {idx}: Mã SKU {variant.ma_sku} bị trùng lặp trên cùng một biên bản kiểm kê.")
        seen.add(variant.id)

        try:
            actual_qty = int(spec.so_luong_thuc_te)
        except (ValueError, TypeError) as exc:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Số lượng kiểm thực tế không hợp lệ.") from exc
        if actual_qty < 0:
            raise ValidationError(f"Dòng {idx} ({variant.ma_sku}): Số lượng thực tế không được nhỏ hơn 0.")

        bal = TonKho.objects.filter(co_so=branch, bien_the=variant).first()
        sys_qty = bal.so_luong if bal else 0
        diff = actual_qty - sys_qty
        if diff == 0:
            recon_status = ChiTietKiemKe.ReconciliationStatus.MATCH
        elif diff < 0:
            recon_status = ChiTietKiemKe.ReconciliationStatus.SHORTAGE
        else:
            recon_status = ChiTietKiemKe.ReconciliationStatus.EXCESS

        validated.append(
            {
                "variant": variant,
                "so_luong_he_thong": sys_qty,
                "so_luong_thuc_te": actual_qty,
                "chenh_lech": diff,
                "trang_thai_doi_chieu": recon_status,
                "don_vi_tinh": variant.san_pham.don_vi_tinh,
                "don_gia": variant.don_gia,
                "xu_ly": (spec.xu_ly or "").strip(),
                "ghi_chu": (spec.ghi_chu or "").strip(),
            }
        )
    return validated


@transaction.atomic
def create_stocktake(
    *,
    actor: User,
    co_so: CoSo,
    line_specs: list[StocktakeLineSpec],
    ma_kiem_ke: str = "",
    ngay_kiem=None,
    nguoi_kiem_ke: str = "",
    muc_dich: str = "Kiểm kê định kỳ cuối ngày",
    ghi_chu: str = "",
) -> KiemKe:
    """Create an Inventory Count / Stocktake Record (UC-6.1, UC-6.2, UC-6.3)."""
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    assert_branch_access(actor, co_so)

    code = (ma_kiem_ke or "").strip().upper() or generate_next_stocktake_code(co_so)
    if KiemKe.objects.filter(ma_kiem_ke__iexact=code).exists():
        raise ValidationError({"ma_kiem_ke": f"Mã biên bản kiểm kê '{code}' đã tồn tại."})

    validated_lines = _validate_and_build_stocktake_lines(co_so, line_specs)

    stocktake = KiemKe.objects.create(
        ma_kiem_ke=code,
        co_so=co_so,
        ngay_kiem=ngay_kiem or timezone.localdate(),
        nguoi_kiem_ke=(nguoi_kiem_ke or actor.display_name).strip(),
        muc_dich=(muc_dich or "Kiểm kê định kỳ cuối ngày").strip(),
        ghi_chu=(ghi_chu or "").strip(),
        trang_thai=KiemKe.Status.PENDING,
        tao_boi=actor,
    )

    for item in validated_lines:
        ChiTietKiemKe.objects.create(
            kiem_ke=stocktake,
            bien_the=item["variant"],
            so_luong_he_thong=item["so_luong_he_thong"],
            so_luong_thuc_te=item["so_luong_thuc_te"],
            chenh_lech=item["chenh_lech"],
            trang_thai_doi_chieu=item["trang_thai_doi_chieu"],
            don_vi_tinh=item["don_vi_tinh"],
            don_gia=item["don_gia"],
            xu_ly=item["xu_ly"],
            ghi_chu=item["ghi_chu"],
        )

    try:
        url = reverse("stocktakes:stocktake_detail", args=[stocktake.id])
    except Exception:
        url = "/stocktakes/"
    notify_admins(
        notification_type=ThongBao.NotificationType.STOCKTAKE_SUBMITTED,
        title=f"[{co_so.ma_co_so}] Biên bản kiểm kê chờ duyệt: {stocktake.ma_kiem_ke}",
        content=(
            f"Quản lý {actor.display_name} ({co_so.ten_co_so}) đã gửi biên bản kiểm kê {stocktake.ma_kiem_ke} "
            f"({len(validated_lines)} dòng hàng)."
        ),
        branch=co_so,
        related_entity_type="KiemKe",
        related_entity_id=stocktake.id,
        target_url=url,
    )
    return stocktake


@transaction.atomic
def update_stocktake(
    *,
    actor: User,
    stocktake: KiemKe,
    line_specs: list[StocktakeLineSpec],
    nguoi_kiem_ke: str = "",
    muc_dich: str = "",
    ghi_chu: str = "",
) -> KiemKe:
    """Update an unapproved Stocktake Record (UC-6.8)."""
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    stocktake = KiemKe.objects.select_for_update().select_related("co_so").get(pk=stocktake.pk)
    assert_branch_access(actor, stocktake.co_so)
    if not stocktake.is_editable:
        raise ValidationError("Không thể chỉnh sửa biên bản kiểm kê đã được phê duyệt.")

    validated_lines = _validate_and_build_stocktake_lines(stocktake.co_so, line_specs)
    if nguoi_kiem_ke:
        stocktake.nguoi_kiem_ke = nguoi_kiem_ke.strip()
    if muc_dich:
        stocktake.muc_dich = muc_dich.strip()
    stocktake.ghi_chu = (ghi_chu or "").strip()
    stocktake.trang_thai = KiemKe.Status.PENDING
    stocktake.save()

    stocktake.lines.all().delete()
    for item in validated_lines:
        ChiTietKiemKe.objects.create(
            kiem_ke=stocktake,
            bien_the=item["variant"],
            so_luong_he_thong=item["so_luong_he_thong"],
            so_luong_thuc_te=item["so_luong_thuc_te"],
            chenh_lech=item["chenh_lech"],
            trang_thai_doi_chieu=item["trang_thai_doi_chieu"],
            don_vi_tinh=item["don_vi_tinh"],
            don_gia=item["don_gia"],
            xu_ly=item["xu_ly"],
            ghi_chu=item["ghi_chu"],
        )
    return stocktake


@transaction.atomic
def delete_stocktake(*, actor: User, stocktake: KiemKe) -> str:
    """Delete an unapproved Stocktake Record (UC-6.9)."""
    assert_roles(actor, User.Role.MANAGER, User.Role.ADMIN)
    stocktake = KiemKe.objects.select_for_update().get(pk=stocktake.pk)
    assert_branch_access(actor, stocktake.co_so)
    if not stocktake.is_deletable:
        raise ValidationError("Không thể xóa biên bản kiểm kê đã được phê duyệt.")
    code = stocktake.ma_kiem_ke
    stocktake.delete()
    return code


@transaction.atomic
def approve_stocktake(*, actor: User, stocktake: KiemKe) -> KiemKe:
    """
    Approve a Stocktake Record (UC-6.10 - ADMIN only).
    Per DEC-03 (and UC-6.10 / Bảng 47), approving a stocktake records administrative
    verification (`APPROVED`) without silently overwriting physical stock (`TonKho`).
    """
    assert_roles(actor, User.Role.ADMIN)
    stocktake = KiemKe.objects.select_for_update().select_related("co_so").get(pk=stocktake.pk)
    if stocktake.trang_thai == KiemKe.Status.APPROVED:
        raise ValidationError(f"Biên bản kiểm kê {stocktake.ma_kiem_ke} đã được phê duyệt trước đó.")
    if stocktake.trang_thai != KiemKe.Status.PENDING:
        raise ValidationError("Chỉ có thể phê duyệt biên bản kiểm kê đang ở trạng thái Chờ duyệt.")

    stocktake.trang_thai = KiemKe.Status.APPROVED
    stocktake.duyet_boi = actor
    stocktake.thoi_gian_duyet = timezone.now()
    stocktake.ly_do_tu_choi = ""
    stocktake.save(update_fields=["trang_thai", "duyet_boi", "thoi_gian_duyet", "ly_do_tu_choi"])

    try:
        url = reverse("stocktakes:stocktake_detail", args=[stocktake.id])
    except Exception:
        url = "/stocktakes/"
    notify_branch_managers(
        branch=stocktake.co_so,
        notification_type=ThongBao.NotificationType.STOCKTAKE_APPROVED,
        title=f"Đã phê duyệt biên bản kiểm kê {stocktake.ma_kiem_ke}",
        content=(
            f"Quản trị viên {actor.display_name} đã phê duyệt biên bản kiểm kê {stocktake.ma_kiem_ke} "
            f"tại {stocktake.co_so.ten_co_so}."
        ),
        related_entity_type="KiemKe",
        related_entity_id=stocktake.id,
        target_url=url,
    )
    return stocktake


@transaction.atomic
def reject_stocktake(*, actor: User, stocktake: KiemKe, reason: str = "") -> KiemKe:
    """Reject a Stocktake Record (UC-6.10 - ADMIN only)."""
    assert_roles(actor, User.Role.ADMIN)
    stocktake = KiemKe.objects.select_for_update().select_related("co_so").get(pk=stocktake.pk)
    if stocktake.trang_thai == KiemKe.Status.APPROVED:
        raise ValidationError("Không thể từ chối biên bản kiểm kê đã được phê duyệt.")
    if stocktake.trang_thai == KiemKe.Status.REJECTED:
        raise ValidationError("Biên bản kiểm kê này đã bị từ chối trước đó.")

    clean_reason = (reason or "Yêu cầu kiểm đếm lại các mặt hàng có chênh lệch.").strip()
    stocktake.trang_thai = KiemKe.Status.REJECTED
    stocktake.tu_choi_boi = actor
    stocktake.thoi_gian_tu_choi = timezone.now()
    stocktake.ly_do_tu_choi = clean_reason
    stocktake.save(update_fields=["trang_thai", "tu_choi_boi", "thoi_gian_tu_choi", "ly_do_tu_choi"])

    try:
        url = reverse("stocktakes:stocktake_detail", args=[stocktake.id])
    except Exception:
        url = "/stocktakes/"
    notify_branch_managers(
        branch=stocktake.co_so,
        notification_type=ThongBao.NotificationType.STOCKTAKE_REJECTED,
        title=f"Từ chối biên bản kiểm kê {stocktake.ma_kiem_ke}",
        content=f"Quản trị viên {actor.display_name} từ chối biên bản kiểm kê {stocktake.ma_kiem_ke}. Lý do: {clean_reason}",
        related_entity_type="KiemKe",
        related_entity_id=stocktake.id,
        target_url=url,
    )
    return stocktake
