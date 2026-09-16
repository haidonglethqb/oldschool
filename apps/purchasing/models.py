from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class NhaCungCap(models.Model):
    """Supplier master entity (Bảng 56 - NhaCungCap)."""

    ma_nha_cung_cap = models.CharField("Mã nhà cung cấp", max_length=50, unique=True, db_index=True)
    ten_nha_cung_cap = models.CharField("Tên nhà cung cấp", max_length=200, db_index=True)
    dia_chi = models.CharField("Địa chỉ", max_length=255)
    sdt = models.CharField("Số điện thoại", max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nha_cung_cap"
        verbose_name = "Nhà cung cấp"
        verbose_name_plural = "Danh sách Nhà cung cấp"
        ordering = ["ma_nha_cung_cap"]

    def __str__(self) -> str:
        return f"{self.ma_nha_cung_cap} - {self.ten_nha_cung_cap}"


class PhieuNhapKho(models.Model):
    """Warehouse import receipt (Bảng 57 - PhieuNhapKho, UC-4.1 to UC-4.11)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Bản nháp"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Chờ duyệt"
        RETURNED = "RETURNED", "Trả lại chỉnh sửa"
        APPROVED = "APPROVED", "Đã duyệt"

    ma_phieu_nhap_kho = models.CharField("Mã phiếu nhập kho", max_length=50, unique=True, db_index=True)
    nha_cung_cap = models.ForeignKey(
        NhaCungCap,
        verbose_name="Nhà cung cấp",
        on_delete=models.PROTECT,
        related_name="import_receipts",
    )
    co_so_nhan = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở nhận kho",
        on_delete=models.PROTECT,
        related_name="import_receipts",
    )
    dia_chi = models.CharField("Địa chỉ giao nhận / NCC", max_length=255, blank=True, default="")
    sdt = models.CharField("Số điện thoại liên hệ", max_length=30, blank=True, default="")
    ngay_nhap = models.DateTimeField("Ngày nhập kho", default=timezone.now, db_index=True)
    ly_do_nhap = models.CharField("Lý do nhập kho", max_length=255, blank=True, default="Nhập hàng từ nhà cung cấp")
    tong_tien = models.DecimalField(
        "Tổng tiền",
        max_digits=16,
        decimal_places=0,
        default=Decimal("0"),
    )
    trang_thai = models.CharField(
        "Trạng thái",
        max_length=25,
        choices=Status.choices,
        default=Status.PENDING_APPROVAL,
        db_index=True,
    )
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")
    nguoi_tao = models.ForeignKey(
        "accounts.User",
        verbose_name="Người lập phiếu",
        on_delete=models.PROTECT,
        related_name="created_import_receipts",
    )
    nguoi_duyet = models.ForeignKey(
        "accounts.User",
        verbose_name="Người phê duyệt / xử lý",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_import_receipts",
    )
    thoi_gian_duyet = models.DateTimeField("Thời gian phê duyệt / xử lý", null=True, blank=True)
    ly_do_tra_lai = models.TextField("Lý do trả lại / từ chối", blank=True, default="")
    created_at = models.DateTimeField("Thời gian tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lần cuối", auto_now=True)

    class Meta:
        db_table = "phieu_nhap_kho"
        verbose_name = "Phiếu nhập kho"
        verbose_name_plural = "Danh sách Phiếu nhập kho"
        ordering = ["-ngay_nhap", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(tong_tien__gte=0),
                name="phieu_nhap_kho_nonnegative_total",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ma_phieu_nhap_kho} ({self.get_trang_thai_display()})"

    @property
    def is_editable(self) -> bool:
        return self.trang_thai in {
            self.Status.DRAFT,
            self.Status.PENDING_APPROVAL,
            self.Status.RETURNED,
        }

    @property
    def is_deletable(self) -> bool:
        return self.trang_thai in {
            self.Status.DRAFT,
            self.Status.PENDING_APPROVAL,
            self.Status.RETURNED,
        }

    @property
    def total_quantity(self) -> int:
        return sum(line.so_luong for line in self.lines.all())


class ChiTietPhieuNhapKho(models.Model):
    """Line item for a warehouse import receipt (Bảng 58 - ChiTietPhieuNhapKho)."""

    phieu_nhap_kho = models.ForeignKey(
        PhieuNhapKho,
        verbose_name="Phiếu nhập kho",
        on_delete=models.CASCADE,
        related_name="lines",
    )
    bien_the = models.ForeignKey(
        "catalog.BienThe",
        verbose_name="Biến thể sản phẩm (SKU)",
        on_delete=models.PROTECT,
        related_name="import_lines",
    )
    so_luong = models.IntegerField("Số lượng nhập")
    don_gia = models.DecimalField("Đơn giá nhập", max_digits=14, decimal_places=0)
    chiet_khau = models.DecimalField(
        "Chiết khấu (VNĐ)",
        max_digits=14,
        decimal_places=0,
        default=Decimal("0"),
    )
    thanh_tien = models.DecimalField("Thành tiền", max_digits=16, decimal_places=0)
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")

    class Meta:
        db_table = "chi_tiet_phieu_nhap_kho"
        verbose_name = "Chi tiết phiếu nhập kho"
        verbose_name_plural = "Chi tiết phiếu nhập kho"
        constraints = [
            models.CheckConstraint(
                condition=Q(so_luong__gt=0),
                name="ct_nhap_kho_positive_qty",
            ),
            models.CheckConstraint(
                condition=Q(don_gia__gte=0) & Q(chiet_khau__gte=0) & Q(thanh_tien__gte=0),
                name="ct_nhap_kho_nonnegative_amounts",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.phieu_nhap_kho.ma_phieu_nhap_kho} - {self.bien_the.ma_sku} x {self.so_luong}"

    def clean(self):
        super().clean()
        if self.so_luong is not None and self.so_luong <= 0:
            raise ValidationError({"so_luong": "Số lượng nhập kho phải lớn hơn 0."})
        if self.don_gia is not None and self.don_gia < 0:
            raise ValidationError({"don_gia": "Đơn giá nhập không được âm."})
        if self.chiet_khau is None:
            self.chiet_khau = Decimal("0")
        if self.chiet_khau < 0:
            raise ValidationError({"chiet_khau": "Chiết khấu không được âm."})
        if self.so_luong and self.don_gia is not None:
            gross = Decimal(self.so_luong) * self.don_gia
            if self.chiet_khau > gross:
                raise ValidationError({"chiet_khau": "Chiết khấu không được vượt quá tổng giá trị dòng hàng."})
            self.thanh_tien = gross - self.chiet_khau
