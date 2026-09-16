"""
Centralized Inventory Mutation & Ledger Service (Mục 6.6, 6.7 & 9 of System.md).
All stock balance changes MUST pass through this service.
"""
from dataclasses import dataclass
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from apps.branches.models import CoSo
from apps.catalog.models import BienThe
from apps.inventory.models import StockMovement, TonKho
from apps.notifications.services import sync_low_stock_alert


class InsufficientStockError(ValidationError):
    """Raised when an outbound or transfer operation exceeds available stock."""


class DuplicateStockEventError(ValidationError):
    """Raised when an idempotency key has already been processed."""


@dataclass
class StockDeltaSpec:
    variant: BienThe
    quantity_delta: int
    unit_price_snapshot: Decimal = Decimal("0")
    source_line_id: int | None = None
    idempotency_key: str = ""
    notes: str = ""


def ensure_stock_balance(branch: CoSo, variant: BienThe, min_threshold: int = 5) -> TonKho:
    """Safely ensure a `TonKho` row exists for `(branch, variant)`, handling concurrent creation."""
    balance = TonKho.objects.filter(co_so=branch, bien_the=variant).first()
    if balance:
        return balance
    try:
        with transaction.atomic():
            balance, _ = TonKho.objects.get_or_create(
                co_so=branch,
                bien_the=variant,
                defaults={"so_luong": 0, "muc_ton_toi_thieu": max(0, int(min_threshold))},
            )
            return balance
    except IntegrityError:
        return TonKho.objects.get(co_so=branch, bien_the=variant)


def ensure_variant_balances_across_branches(variant: BienThe, min_threshold: int = 5) -> list[TonKho]:
    """Ensure every branch has a stock balance row initialized for a newly created variant."""
    balances = []
    for branch in CoSo.objects.all():
        balances.append(ensure_stock_balance(branch, variant, min_threshold=min_threshold))
    return balances


@transaction.atomic
def apply_stock_movements(
    *,
    branch: CoSo,
    deltas: list[StockDeltaSpec],
    movement_type: str,
    source_doc_type: str,
    source_doc_id: int,
    source_doc_code: str,
    actor,
    effective_at=None,
) -> list[StockMovement]:
    """
    Atomically lock required `TonKho` rows in deterministic order, validate available stock,
    apply signed deltas, create immutable `StockMovement` records, and sync low-stock alerts.
    """
    if not deltas:
        raise ValidationError("Danh sách biến động tồn kho không được để trống.")

    effective_time = effective_at or timezone.now()

    # Ensure rows exist before locking so select_for_update locks every target row
    variant_map: dict[int, BienThe] = {}
    for spec in deltas:
        if spec.quantity_delta == 0:
            raise ValidationError(f"Số lượng biến động của SKU {spec.variant.ma_sku} phải khác 0.")
        if not spec.idempotency_key:
            raise ValidationError("Mỗi biến động tồn kho bắt buộc phải có khóa chống trùng lặp (idempotency_key).")
        variant_map[spec.variant.id] = spec.variant
        ensure_stock_balance(branch, spec.variant)

    # Check idempotency keys first
    requested_keys = [spec.idempotency_key for spec in deltas]
    if len(set(requested_keys)) != len(requested_keys):
        raise DuplicateStockEventError("Phát hiện khóa sự kiện tồn kho bị trùng lặp trong cùng một giao dịch.")

    if StockMovement.objects.filter(idempotency_key__in=requested_keys).exists():
        raise DuplicateStockEventError("Giao dịch tồn kho này đã được xử lý trước đó (trùng idempotency_key).")

    # Lock TonKho rows in ascending bien_the_id order to prevent deadlocks
    sorted_variant_ids = sorted(variant_map.keys())
    locked_balances = {
        b.bien_the_id: b
        for b in TonKho.objects.select_for_update()
        .select_related("co_so", "bien_the", "bien_the__san_pham")
        .filter(co_so=branch, bien_the_id__in=sorted_variant_ids)
        .order_by("bien_the_id")
    }

    # Aggregate net delta per variant to validate sufficiency before mutating
    running_balances = {vid: locked_balances[vid].so_luong for vid in sorted_variant_ids}
    for spec in deltas:
        vid = spec.variant.id
        new_qty = running_balances[vid] + int(spec.quantity_delta)
        if new_qty < 0:
            avail = running_balances[vid]
            req = abs(int(spec.quantity_delta))
            raise InsufficientStockError(
                f"Không đủ số lượng tồn kho tại {branch.ten_co_so} cho sản phẩm "
                f"{spec.variant.ma_sku} ({spec.variant.san_pham.ten_hang_hoa} - "
                f"{spec.variant.mau_sac}/{spec.variant.kich_co}): "
                f"Tồn hiện tại = {avail}, Số lượng cần xuất = {req}."
            )
        running_balances[vid] = new_qty

    created_movements: list[StockMovement] = []
    for spec in deltas:
        vid = spec.variant.id
        ton_kho = locked_balances[vid]
        ton_kho.so_luong = ton_kho.so_luong + int(spec.quantity_delta)
        ton_kho.save(update_fields=["so_luong", "updated_at"])

        movement = StockMovement.objects.create(
            co_so=branch,
            bien_the=spec.variant,
            movement_type=movement_type,
            quantity_delta=int(spec.quantity_delta),
            balance_after=ton_kho.so_luong,
            unit_price_snapshot=spec.unit_price_snapshot,
            source_doc_type=source_doc_type,
            source_doc_id=source_doc_id,
            source_doc_code=source_doc_code,
            source_line_id=spec.source_line_id,
            actor=actor,
            effective_at=effective_time,
            idempotency_key=spec.idempotency_key,
            notes=spec.notes,
        )
        created_movements.append(movement)

    # Sync low-stock warnings for all affected balances
    for vid in sorted_variant_ids:
        sync_low_stock_alert(locked_balances[vid])

    return created_movements


@transaction.atomic
def set_opening_stock(
    *,
    branch: CoSo,
    variant: BienThe,
    quantity: int,
    actor,
    min_threshold: int = 5,
    effective_at=None,
    notes: str = "Khởi tạo tồn kho đầu kỳ",
) -> TonKho:
    """Initialize opening stock balance and record an OPENING ledger movement if quantity > 0."""
    if quantity < 0:
        raise ValidationError("Số lượng tồn đầu kỳ không được âm.")
    balance = ensure_stock_balance(branch, variant, min_threshold=min_threshold)
    balance = TonKho.objects.select_for_update().get(pk=balance.pk)
    balance.muc_ton_toi_thieu = max(0, int(min_threshold))
    balance.save(update_fields=["muc_ton_toi_thieu", "updated_at"])

    delta = int(quantity) - balance.so_luong
    if delta != 0:
        idem_key = f"OPENING:{branch.ma_co_so}:{variant.ma_sku}:{timezone.now().timestamp()}"
        apply_stock_movements(
            branch=branch,
            deltas=[
                StockDeltaSpec(
                    variant=variant,
                    quantity_delta=delta,
                    unit_price_snapshot=variant.don_gia,
                    idempotency_key=idem_key,
                    notes=notes,
                )
            ],
            movement_type=StockMovement.MovementType.OPENING,
            source_doc_type="OpeningStock",
            source_doc_id=balance.id,
            source_doc_code=f"OPN-{branch.ma_co_so}-{variant.ma_sku}",
            actor=actor,
            effective_at=effective_at,
        )
        balance.refresh_from_db()
    else:
        sync_low_stock_alert(balance)
    return balance
