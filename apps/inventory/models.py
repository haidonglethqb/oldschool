from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StockStatus(models.TextChoices):
    IN_STOCK = "IN_STOCK", "Còn hàng"
    LOW_STOCK = "LOW_STOCK", "Sắp hết hàng"
    OUT_OF_STOCK = "OUT_OF_STOCK", "Hết hàng"


class TonKho(models.Model):
    """Branch-specific stock balance per product variant (TonKho)."""

    co_so = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở",
        on_delete=models.PROTECT,
        related_name="stock_balances",
    )
    bien_the = models.ForeignKey(
        "catalog.BienThe",
        verbose_name="Biến thể (SKU)",
        on_delete=models.PROTECT,
        related_name="stock_balances",
    )
    so_luong = models.IntegerField("Số lượng hiện tại", default=0)
    muc_ton_toi_thieu = models.IntegerField("Định mức tồn tối thiểu", default=5)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    class Meta:
        db_table = "ton_kho"
        verbose_name = "Tồn kho"
        verbose_name_plural = "Danh sách Tồn kho"
        ordering = ["co_so__ma_co_so", "bien_the__ma_sku"]
        constraints = [
            models.UniqueConstraint(
                fields=["co_so", "bien_the"],
                name="uniq_branch_variant_stock",
            ),
            models.CheckConstraint(
                condition=Q(so_luong__gte=0) & Q(muc_ton_toi_thieu__gte=0),
                name="ton_kho_nonnegative_quantities",
            ),
        ]
        indexes = [
            models.Index(fields=["co_so", "so_luong"]),
        ]

    def __str__(self) -> str:
        return f"{self.co_so.ma_co_so} | {self.bien_the.ma_sku}: {self.so_luong}"

    @property
    def stock_status(self) -> str:
        if self.so_luong <= 0:
            return StockStatus.OUT_OF_STOCK
        if self.so_luong <= self.muc_ton_toi_thieu:
            return StockStatus.LOW_STOCK
        return StockStatus.IN_STOCK

    @property
    def trang_thai_ton(self) -> str:
        """Vietnamese alias for stock_status property."""
        return self.stock_status

    @property
    def stock_status_label(self) -> str:
        return dict(StockStatus.choices).get(self.stock_status, "Còn hàng")

    @property
    def stock_status_badge_class(self) -> str:
        status = self.stock_status
        if status == StockStatus.OUT_OF_STOCK:
            return "os-badge-out-of-stock"
        if status == StockStatus.LOW_STOCK:
            return "os-badge-low-stock"
        return "os-badge-in-stock"


class StockMovement(models.Model):
    """Immutable inventory ledger record for auditability and dynamic reporting."""

    class MovementType(models.TextChoices):
        OPENING = "OPENING", "Tồn đầu kỳ"
        IMPORT_IN = "IMPORT_IN", "Nhập kho từ NCC"
        IMPORT_APPROVED = "IMPORT_APPROVED", "Nhập kho từ NCC (Đã duyệt)"
        SALE_OUT = "SALE_OUT", "Xuất bán hàng"
        SALES_OUTBOUND = "SALES_OUTBOUND", "Xuất kho bán hàng"
        TRANSFER_OUT = "TRANSFER_OUT", "Xuất điều chuyển"
        TRANSFER_IN = "TRANSFER_IN", "Nhập điều chuyển"
        STOCKTAKE_ADJUST = "STOCKTAKE_ADJUST", "Điều chỉnh kiểm kê"
        ADJUSTMENT = "ADJUSTMENT", "Điều chỉnh tồn kho"

    co_so = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở",
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    bien_the = models.ForeignKey(
        "catalog.BienThe",
        verbose_name="Biến thể (SKU)",
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    movement_type = models.CharField(
        "Loại biến động",
        max_length=30,
        choices=MovementType.choices,
        db_index=True,
    )
    quantity_delta = models.IntegerField("Số lượng biến động (+/-)")
    balance_after = models.IntegerField("Tồn sau giao dịch")
    unit_price_snapshot = models.DecimalField(
        "Đơn giá giao dịch",
        max_digits=14,
        decimal_places=0,
        default=Decimal("0"),
    )
    source_doc_type = models.CharField("Loại chứng từ gốc", max_length=50, db_index=True)
    source_doc_id = models.PositiveBigIntegerField("ID chứng từ gốc", db_index=True)
    source_doc_code = models.CharField("Mã chứng từ gốc", max_length=60, blank=True, default="", db_index=True)
    source_line_id = models.PositiveBigIntegerField("ID dòng chi tiết", null=True, blank=True)
    actor = models.ForeignKey(
        "accounts.User",
        verbose_name="Người thực hiện",
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    effective_at = models.DateTimeField("Thời điểm hiệu lực", default=timezone.now, db_index=True)
    created_at = models.DateTimeField("Thời điểm ghi sổ", auto_now_add=True)
    idempotency_key = models.CharField("Khóa chống trùng lặp", max_length=120, unique=True)
    notes = models.CharField("Ghi chú", max_length=255, blank=True, default="")

    class Meta:
        db_table = "so_cai_ton_kho"
        verbose_name = "Sổ cái biến động tồn kho"
        verbose_name_plural = "Sổ cái biến động tồn kho"
        ordering = ["-effective_at", "-id"]
        indexes = [
            models.Index(fields=["co_so", "effective_at"]),
            models.Index(fields=["bien_the", "effective_at"]),
            models.Index(fields=["movement_type", "effective_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(quantity_delta=0),
                name="stock_movement_nonzero_delta",
            ),
            models.CheckConstraint(
                condition=Q(balance_after__gte=0),
                name="stock_movement_nonnegative_balance_after",
            ),
        ]

    def __str__(self) -> str:
        sign = "+" if self.quantity_delta > 0 else ""
        return f"[{self.effective_at:%Y-%m-%d %H:%M}] {self.co_so.ma_co_so} {self.bien_the.ma_sku}: {sign}{self.quantity_delta} -> {self.balance_after}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Bản ghi sổ cái tồn kho (StockMovement) là bất biến, không được phép sửa đổi.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Không được phép xóa lịch sử biến động tồn kho.")
