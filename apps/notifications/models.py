from django.db import models


class ThongBao(models.Model):
    """Persisted system notification and low-stock alert (Mục 7.7 & UC-5.13)."""

    class NotificationType(models.TextChoices):
        IMPORT_SUBMITTED = "IMPORT_SUBMITTED", "Phiếu nhập kho chờ duyệt"
        IMPORT_APPROVED = "IMPORT_APPROVED", "Phiếu nhập kho đã được duyệt"
        IMPORT_RETURNED = "IMPORT_RETURNED", "Phiếu nhập kho bị trả lại"
        OUTBOUND_COMPLETED = "OUTBOUND_COMPLETED", "Phiếu xuất kho đã ghi nhận"
        OUTBOUND_REQUEST = "OUTBOUND_REQUEST", "Yêu cầu xuất kho mới"
        OUTBOUND_REQUESTED = "OUTBOUND_REQUESTED", "Yêu cầu xuất kho bán hàng"
        TRANSFER_REQUESTED = "TRANSFER_REQUESTED", "Yêu cầu điều chuyển mới"
        TRANSFER_DISPATCHED = "TRANSFER_DISPATCHED", "Hàng điều chuyển đã xuất đi"
        TRANSFER_RECEIVED = "TRANSFER_RECEIVED", "Đã xác nhận nhận điều chuyển"
        STOCKTAKE_PENDING = "STOCKTAKE_PENDING", "Biên bản kiểm kê chờ duyệt"
        STOCKTAKE_SUBMITTED = "STOCKTAKE_SUBMITTED", "Biên bản kiểm kê mới gửi duyệt"
        STOCKTAKE_REVIEWED = "STOCKTAKE_REVIEWED", "Kết quả duyệt biên bản kiểm kê"
        STOCKTAKE_APPROVED = "STOCKTAKE_APPROVED", "Biên bản kiểm kê đã duyệt"
        STOCKTAKE_REJECTED = "STOCKTAKE_REJECTED", "Biên bản kiểm kê bị từ chối"
        LOW_STOCK_ALERT = "LOW_STOCK_ALERT", "Cảnh báo tồn kho thấp / hết hàng"
        SYSTEM = "SYSTEM", "Thông báo hệ thống"

    nguoi_nhan = models.ForeignKey(
        "accounts.User",
        verbose_name="Người nhận",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    co_so = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở liên quan",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    bien_the = models.ForeignKey(
        "catalog.BienThe",
        verbose_name="Biến thể liên quan",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    loai_thong_bao = models.CharField(
        "Loại thông báo",
        max_length=35,
        choices=NotificationType.choices,
        db_index=True,
    )
    tieu_de = models.CharField("Tiêu đề", max_length=200)
    noi_dung = models.TextField("Nội dung thông báo")
    related_entity_type = models.CharField("Loại thực thể", max_length=50, blank=True, default="")
    related_entity_id = models.PositiveBigIntegerField("ID thực thể", null=True, blank=True)
    target_url = models.CharField("Đường dẫn điều hướng", max_length=255, blank=True, default="")
    da_doc = models.BooleanField("Đã đọc", default=False, db_index=True)
    da_xu_ly = models.BooleanField("Đã xử lý / Đóng cảnh báo", default=False, db_index=True)
    created_at = models.DateTimeField("Thời gian tạo", auto_now_add=True, db_index=True)

    class Meta:
        db_table = "thong_bao"
        verbose_name = "Thông báo"
        verbose_name_plural = "Danh sách Thông báo"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"[{self.get_loai_thong_bao_display()}] {self.tieu_de}"
