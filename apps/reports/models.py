from decimal import Decimal
from django.db import models
from django.utils import timezone


class BaoCao(models.Model):
    """Saved Report Snapshot entity (Bảng 66 - BaoCao, extended with branch & period scope)."""

    ma_bao_cao = models.CharField("Mã báo cáo", max_length=60, unique=True, db_index=True)
    co_so = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Phạm vi cơ sở",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="saved_reports",
        help_text="Để trống nếu báo cáo toàn hệ thống.",
    )
    bien_the = models.ForeignKey(
        "catalog.BienThe",
        verbose_name="Biến thể sản phẩm (SKU)",
        on_delete=models.PROTECT,
        related_name="saved_reports",
    )
    tu_ngay = models.DateField("Từ ngày", default=timezone.localdate)
    den_ngay = models.DateField("Đến ngày", default=timezone.localdate)
    ton_dau_ky = models.IntegerField("Tồn đầu kỳ", default=0)
    nhap_kho = models.IntegerField("Tổng nhập trong kỳ", default=0)
    xuat_kho = models.IntegerField("Tổng xuất trong kỳ", default=0)
    ton_cuoi_ky = models.IntegerField("Tồn cuối kỳ", default=0)
    gia_von = models.DecimalField("Giá vốn tham chiếu", max_digits=14, decimal_places=0, default=Decimal("0"))
    gia_tri_ton_kho = models.DecimalField("Giá trị tồn kho cuối kỳ", max_digits=16, decimal_places=0, default=Decimal("0"))
    trang_thai = models.CharField("Trạng thái tồn", max_length=30, blank=True, default="Còn hàng")
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")
    nguoi_tao = models.ForeignKey(
        "accounts.User",
        verbose_name="Người xuất/lưu báo cáo",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="saved_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bao_cao"
        verbose_name = "Báo cáo tồn kho"
        verbose_name_plural = "Danh sách Báo cáo tồn kho"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        scope = self.co_so.ma_co_so if self.co_so else "ALL"
        return f"{self.ma_bao_cao} [{scope}] {self.bien_the.ma_sku}"
