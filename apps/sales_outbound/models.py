from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class YeuCauXuatHang(models.Model):
    """
    Lightweight Sales Outbound Request created by STAFF (Nhân viên bán hàng)
    per Proposed Workflow Hình 5 before Manager prepares the actual Outbound Receipt.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ quản lý xử lý"
        PROCESSED = "PROCESSED", "Đã lập phiếu xuất"
        REJECTED = "REJECTED", "Từ chối / Thiếu hàng"

    class DeliveryMethod(models.TextChoices):
        COUNTER = "COUNTER", "Bán trực tiếp tại quầy"
        DELIVERY = "DELIVERY", "Đóng gói giao hàng"

    ma_yeu_cau = models.CharField("Mã yêu cầu xuất", max_length=50, unique=True, db_index=True)
    co_so = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở",
        on_delete=models.PROTECT,
        related_name="outbound_requests",
    )
    ten_khach_hang = models.CharField("Tên khách hàng / Đơn hàng", max_length=150, blank=True, default="Khách lẻ tại quầy")
    sdt_khach_hang = models.CharField("Số điện thoại nhận hàng", max_length=30, blank=True, default="")
    dia_chi_giao = models.CharField("Địa chỉ giao hàng", max_length=255, blank=True, default="")
    phuong_thuc_giao = models.CharField(
        "Phương thức bán / giao",
        max_length=20,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.COUNTER,
    )
    ghi_chu = models.TextField("Ghi chú yêu cầu", blank=True, default="")
    trang_thai = models.CharField(
        "Trạng thái",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    nguoi_yeu_cau = models.ForeignKey(
        "accounts.User",
        verbose_name="Nhân viên yêu cầu",
        on_delete=models.PROTECT,
        related_name="created_outbound_requests",
    )
    nguoi_xu_ly = models.ForeignKey(
        "accounts.User",
        verbose_name="Quản lý xử lý",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="processed_outbound_requests",
    )
    ngay_yeu_cau = models.DateTimeField("Thời gian yêu cầu", default=timezone.now)
    thoi_gian_xu_ly = models.DateTimeField("Thời gian xử lý", null=True, blank=True)

    class Meta:
        db_table = "yeu_cau_xuat_hang"
        verbose_name = "Yêu cầu xuất kho bán hàng"
        verbose_name_plural = "Danh sách Yêu cầu xuất kho bán hàng"
        ordering = ["-ngay_yeu_cau", "-id"]

    def __str__(self) -> str:
        return f"{self.ma_yeu_cau} ({self.co_so.ma_co_so} - {self.get_trang_thai_display()})"


class ChiTietYeuCauXuatHang(models.Model):
    yeu_cau = models.ForeignKey(
        YeuCauXuatHang,
        verbose_name="Yêu cầu xuất",
        on_delete=models.CASCADE,
        related_name="lines",
    )
    bien_the = models.ForeignKey(
        "catalog.BienThe",
        verbose_name="Biến thể (SKU)",
        on_delete=models.PROTECT,
        related_name="outbound_request_lines",
    )
    so_luong = models.IntegerField("Số lượng yêu cầu")

    class Meta:
        db_table = "chi_tiet_yeu_cau_xuat_hang"
        verbose_name = "Chi tiết yêu cầu xuất"
        verbose_name_plural = "Chi tiết yêu cầu xuất"
        constraints = [
            models.CheckConstraint(
                condition=Q(so_luong__gt=0),
                name="ct_yc_xuat_positive_qty",
            ),
        ]


class PhieuXuatHangBan(models.Model):
    """Sales Outbound Receipt (Bảng 59 - PhieuXuatHangBan, UC-5.4 to UC-5.12)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ ghi nhận"
        COMPLETED = "COMPLETED", "Đã ghi nhận xuất kho"
        CANCELLED = "CANCELLED", "Đã hủy"

    class DeliveryMethod(models.TextChoices):
        COUNTER = "COUNTER", "Bán trực tiếp tại quầy"
        DELIVERY = "DELIVERY", "Đóng gói giao hàng"

    ma_phieu_xuat_hang_ban = models.CharField("Mã phiếu xuất", max_length=50, unique=True, db_index=True)
    co_so = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở xuất kho",
        on_delete=models.PROTECT,
        related_name="sales_outbound_receipts",
    )
    yeu_cau_xuat = models.OneToOneField(
        YeuCauXuatHang,
        verbose_name="Yêu cầu xuất liên quan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outbound_receipt",
    )
    ten_khach_hang = models.CharField("Khách hàng / Người nhận", max_length=150, blank=True, default="Khách mua lẻ")
    sdt = models.CharField("Số điện thoại liên hệ", max_length=30)
    dia_chi = models.CharField("Địa chỉ giao / xuất hàng", max_length=255)
    phuong_thuc_giao = models.CharField(
        "Phương thức giao nhận",
        max_length=20,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.COUNTER,
    )
    ngay_xuat = models.DateTimeField("Ngày xuất kho", default=timezone.now, db_index=True)
    tong_tien = models.DecimalField(
        "Tổng tiền",
        max_digits=16,
        decimal_places=0,
        default=Decimal("0"),
    )
    trang_thai = models.CharField(
        "Trạng thái xử lý",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")
    nguoi_tao = models.ForeignKey(
        "accounts.User",
        verbose_name="Người lập phiếu",
        on_delete=models.PROTECT,
        related_name="created_outbound_receipts",
    )
    nguoi_ghi_nhan = models.ForeignKey(
        "accounts.User",
        verbose_name="Người ghi nhận xuất kho",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finalized_outbound_receipts",
    )
    thoi_gian_ghi_nhan = models.DateTimeField("Thời điểm ghi nhận hoàn tất", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "phieu_xuat_hang_ban"
        verbose_name = "Phiếu xuất hàng bán"
        verbose_name_plural = "Danh sách Phiếu xuất hàng bán"
        ordering = ["-ngay_xuat", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(tong_tien__gte=0),
                name="phieu_xuat_ban_nonnegative_total",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ma_phieu_xuat_hang_ban} ({self.co_so.ma_co_so} - {self.get_trang_thai_display()})"

    @property
    def is_editable(self) -> bool:
        return self.trang_thai == self.Status.PENDING

    @property
    def is_deletable(self) -> bool:
        return self.trang_thai in {self.Status.PENDING, self.Status.CANCELLED}

    @property
    def is_printable(self) -> bool:
        return self.trang_thai == self.Status.COMPLETED

    @property
    def total_quantity(self) -> int:
        return sum(line.so_luong for line in self.lines.all())


class ChiTietPhieuXuatHangBan(models.Model):
    """Line item for Sales Outbound Receipt (Bảng 60 - ChiTietPhieuXuatHangBan)."""

    phieu_xuat_hang_ban = models.ForeignKey(
        PhieuXuatHangBan,
        verbose_name="Phiếu xuất hàng bán",
        on_delete=models.CASCADE,
        related_name="lines",
    )
    bien_the = models.ForeignKey(
        "catalog.BienThe",
        verbose_name="Biến thể sản phẩm (SKU)",
        on_delete=models.PROTECT,
        related_name="sales_outbound_lines",
    )
    so_luong = models.IntegerField("Số lượng xuất")
    don_gia = models.DecimalField("Đơn giá bán", max_digits=14, decimal_places=0)
    thanh_tien = models.DecimalField("Thành tiền", max_digits=16, decimal_places=0)
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")

    class Meta:
        db_table = "chi_tiet_phieu_xuat_hang_ban"
        verbose_name = "Chi tiết phiếu xuất hàng bán"
        verbose_name_plural = "Chi tiết phiếu xuất hàng bán"
        constraints = [
            models.CheckConstraint(
                condition=Q(so_luong__gt=0),
                name="ct_xuat_ban_positive_qty",
            ),
            models.CheckConstraint(
                condition=Q(don_gia__gte=0) & Q(thanh_tien__gte=0),
                name="ct_xuat_ban_nonnegative_amounts",
            ),
        ]

    def clean(self):
        super().clean()
        if self.so_luong is not None and self.so_luong <= 0:
            raise ValidationError({"so_luong": "Số lượng xuất kho phải lớn hơn 0."})
        if self.don_gia is not None and self.don_gia < 0:
            raise ValidationError({"don_gia": "Đơn giá xuất không được âm."})
        if self.so_luong and self.don_gia is not None:
            self.thanh_tien = Decimal(self.so_luong) * self.don_gia
