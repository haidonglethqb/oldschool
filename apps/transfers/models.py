from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class PhieuDieuChuyen(models.Model):
    """Interbranch Transfer Order (Bảng 61 - PhieuDieuChuyen, UC-5.3)."""

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Chờ cơ sở xuất xác nhận"
        ACCEPTED = "ACCEPTED", "Đã chấp nhận điều chuyển"
        REJECTED = "REJECTED", "Từ chối điều chuyển"
        DISPATCHED = "DISPATCHED", "Đang vận chuyển (Đã xuất)"
        RECEIVED = "RECEIVED", "Đã nhận đủ hàng"
        RECEIVED_WITH_SHORTAGE = "RECEIVED_WITH_SHORTAGE", "Đã nhận (Có thiếu hụt)"
        CANCELLED = "CANCELLED", "Đã hủy"

    ma_phieu_dieu_chuyen = models.CharField("Mã phiếu điều chuyển", max_length=50, unique=True, db_index=True)
    co_so_xuat = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở xuất hàng",
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
    )
    co_so_nhan = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở nhận hàng",
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
    )
    ngay_dieu_chuyen = models.DateField("Ngày yêu cầu điều chuyển", default=timezone.localdate, db_index=True)
    dia_chi_nhan = models.CharField("Địa chỉ nhận hàng", max_length=255, blank=True, default="")
    ly_do = models.CharField("Lý do điều chuyển", max_length=255, default="Bổ sung tồn kho cơ sở thiếu hàng")
    trang_thai = models.CharField(
        "Trạng thái điều chuyển",
        max_length=30,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")
    ghi_chu_chenh_lech = models.TextField("Ghi chú xử lý chênh lệch / thiếu hụt", blank=True, default="")

    nguoi_tao = models.ForeignKey(
        "accounts.User",
        verbose_name="Người tạo yêu cầu",
        on_delete=models.PROTECT,
        related_name="requested_transfers",
    )
    nguoi_xuat = models.ForeignKey(
        "accounts.User",
        verbose_name="Người xuất hàng",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dispatched_transfers",
    )
    nguoi_nhan = models.ForeignKey(
        "accounts.User",
        verbose_name="Người nhận hàng",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="received_transfers",
    )
    created_at = models.DateTimeField("Thời điểm tạo", auto_now_add=True)
    thoi_gian_xuat = models.DateTimeField("Thời điểm xuất đi", null=True, blank=True)
    thoi_gian_nhan = models.DateTimeField("Thời điểm xác nhận nhận", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "phieu_dieu_chuyen"
        verbose_name = "Phiếu điều chuyển"
        verbose_name_plural = "Danh sách Phiếu điều chuyển"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(co_so_xuat=F("co_so_nhan")),
                name="phieu_dieu_chuyen_different_branches",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ma_phieu_dieu_chuyen} ({self.co_so_xuat.ma_co_so} -> {self.co_so_nhan.ma_co_so})"

    def clean(self):
        super().clean()
        if self.co_so_xuat_id and self.co_so_nhan_id and self.co_so_xuat_id == self.co_so_nhan_id:
            raise ValidationError("Cơ sở xuất và Cơ sở nhận phải khác nhau.")


class ChiTietPhieuDieuChuyen(models.Model):
    """Line item for Interbranch Transfer (Bảng 62 - ChiTietPhieuDieuChuyen)."""

    phieu_dieu_chuyen = models.ForeignKey(
        PhieuDieuChuyen,
        verbose_name="Phiếu điều chuyển",
        on_delete=models.CASCADE,
        related_name="lines",
    )
    bien_the = models.ForeignKey(
        "catalog.BienThe",
        verbose_name="Biến thể sản phẩm (SKU)",
        on_delete=models.PROTECT,
        related_name="transfer_lines",
    )
    so_luong_yeu_cau = models.IntegerField("Số lượng yêu cầu")
    so_luong_xuat = models.IntegerField("Số lượng thực xuất", default=0)
    so_luong_nhan = models.IntegerField("Số lượng thực nhận", default=0)
    ghi_chu = models.TextField("Ghi chú dòng hàng", blank=True, default="")

    class Meta:
        db_table = "chi_tiet_phieu_dieu_chuyen"
        verbose_name = "Chi tiết phiếu điều chuyển"
        verbose_name_plural = "Chi tiết phiếu điều chuyển"
        constraints = [
            models.CheckConstraint(
                condition=Q(so_luong_yeu_cau__gt=0) & Q(so_luong_xuat__gte=0) & Q(so_luong_nhan__gte=0),
                name="ct_dieu_chuyen_valid_quantities",
            ),
        ]

    @property
    def so_luong(self) -> int:
        """Compatibility alias returning dispatched or requested quantity."""
        return self.so_luong_xuat if self.so_luong_xuat > 0 else self.so_luong_yeu_cau

    @property
    def shortage_quantity(self) -> int:
        if self.so_luong_xuat > self.so_luong_nhan:
            return self.so_luong_xuat - self.so_luong_nhan
        return 0
