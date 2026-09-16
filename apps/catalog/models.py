from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class SanPham(models.Model):
    """Product master entity (Bảng 55 - SanPham, separated from variants)."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Đang kinh doanh"
        DISCONTINUED = "DISCONTINUED", "Ngừng kinh doanh"

    ma_san_pham = models.CharField("Mã hàng hóa", max_length=50, unique=True, db_index=True)
    ten_hang_hoa = models.CharField("Tên hàng hóa", max_length=200, db_index=True)
    nhom_hang = models.CharField("Nhóm hàng hóa", max_length=100, db_index=True)
    don_vi_tinh = models.CharField("Đơn vị tính", max_length=50, default="Cái")
    don_gia_niem_yet = models.DecimalField(
        "Đơn giá niêm yết",
        max_digits=14,
        decimal_places=0,
        default=Decimal("0"),
    )
    hinh_anh = models.ImageField("Hình ảnh", upload_to="products/", null=True, blank=True)
    ghi_chu = models.TextField("Mô tả / Ghi chú", blank=True, default="")
    trang_thai = models.CharField(
        "Trạng thái kinh doanh",
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "san_pham"
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Danh mục Sản phẩm"
        ordering = ["-created_at", "ma_san_pham"]
        constraints = [
            models.CheckConstraint(
                condition=Q(don_gia_niem_yet__gte=0),
                name="san_pham_nonnegative_price",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ma_san_pham} - {self.ten_hang_hoa}"

    def clean(self):
        super().clean()
        if self.ma_san_pham:
            self.ma_san_pham = self.ma_san_pham.strip().upper()
        if self.don_gia_niem_yet is not None and self.don_gia_niem_yet < 0:
            raise ValidationError({"don_gia_niem_yet": "Đơn giá không được nhỏ hơn 0."})


class BienThe(models.Model):
    """Product Variant / SKU entity (BienThe on ERD, Mục VI.1)."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Đang hoạt động"
        INACTIVE = "INACTIVE", "Ngừng hoạt động"

    san_pham = models.ForeignKey(
        SanPham,
        verbose_name="Sản phẩm",
        on_delete=models.PROTECT,
        related_name="variants",
    )
    ma_sku = models.CharField("Mã SKU", max_length=60, unique=True, db_index=True)
    mau_sac = models.CharField("Màu sắc", max_length=50, db_index=True)
    kich_co = models.CharField("Kích cỡ (Size)", max_length=30, db_index=True)
    don_gia = models.DecimalField(
        "Giá bán",
        max_digits=14,
        decimal_places=0,
        default=Decimal("0"),
    )
    trang_thai = models.CharField(
        "Trạng thái biến thể",
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bien_the"
        verbose_name = "Biến thể sản phẩm (SKU)"
        verbose_name_plural = "Danh sách Biến thể (SKU)"
        ordering = ["san_pham__ma_san_pham", "mau_sac", "kich_co"]
        constraints = [
            models.UniqueConstraint(
                fields=["san_pham", "mau_sac", "kich_co"],
                name="uniq_product_color_size",
            ),
            models.CheckConstraint(
                condition=Q(don_gia__gte=0),
                name="bien_the_nonnegative_price",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ma_sku} ({self.san_pham.ten_hang_hoa} - {self.mau_sac}/{self.kich_co})"

    @property
    def full_display_name(self) -> str:
        return f"{self.san_pham.ten_hang_hoa} ({self.mau_sac} - Size {self.kich_co})"

    def clean(self):
        super().clean()
        if self.ma_sku:
            self.ma_sku = self.ma_sku.strip().upper()
        if self.mau_sac:
            self.mau_sac = self.mau_sac.strip()
        if self.kich_co:
            self.kich_co = self.kich_co.strip().upper()
        if self.don_gia is not None and self.don_gia < 0:
            raise ValidationError({"don_gia": "Giá bán biến thể không được nhỏ hơn 0."})
