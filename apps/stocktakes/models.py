from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class KiemKe(models.Model):
    """Inventory Count Record (Bảng 64 - KiemKe, UC-6.1 to UC-6.10)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Chờ duyệt"
        APPROVED = "APPROVED", "Đã duyệt"
        REJECTED = "REJECTED", "Từ chối"

    ma_kiem_ke = models.CharField("Mã biên bản kiểm kê", max_length=50, unique=True, db_index=True)
    co_so = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở kiểm kê",
        on_delete=models.PROTECT,
        related_name="stocktakes",
    )
    ngay_kiem = models.DateField("Ngày kiểm kê", default=timezone.localdate, db_index=True)
    nguoi_kiem_ke = models.CharField("Nhân sự kiểm đếm thực tế", max_length=150)
    muc_dich = models.CharField("Mục đích kiểm kê", max_length=255, default="Kiểm kê định kỳ cuối ngày")
    ghi_chu = models.TextField("Ghi chú biên bản", blank=True, default="")
    trang_thai = models.CharField(
        "Trạng thái",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    tao_boi = models.ForeignKey(
        "accounts.User",
        verbose_name="Người tạo biên bản",
        on_delete=models.PROTECT,
        related_name="created_stocktakes",
    )
    duyet_boi = models.ForeignKey(
        "accounts.User",
        verbose_name="Người phê duyệt",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_stocktakes",
    )
    tu_choi_boi = models.ForeignKey(
        "accounts.User",
        verbose_name="Người từ chối",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rejected_stocktakes",
    )
    thoi_gian_tao = models.DateTimeField("Thời gian tạo", auto_now_add=True)
    thoi_gian_duyet = models.DateTimeField("Thời gian duyệt", null=True, blank=True)
    thoi_gian_tu_choi = models.DateTimeField("Thời gian từ chối", null=True, blank=True)
    ly_do_tu_choi = models.TextField("Lý do từ chối", blank=True, default="")

    class Meta:
        db_table = "kiem_ke"
        verbose_name = "Biên bản kiểm kê"
        verbose_name_plural = "Danh sách Biên bản kiểm kê"
        ordering = ["-thoi_gian_tao", "-id"]

    def __str__(self) -> str:
        return f"{self.ma_kiem_ke} ({self.co_so.ma_co_so} - {self.get_trang_thai_display()})"

    @property
    def is_editable(self) -> bool:
        return self.trang_thai in {self.Status.PENDING, self.Status.REJECTED}

    @property
    def is_deletable(self) -> bool:
        return self.trang_thai in {self.Status.PENDING, self.Status.REJECTED}

    @property
    def summary_counts(self) -> dict:
        lines = list(self.lines.all())
        match_count = sum(1 for item in lines if item.chenh_lech == 0)
        shortage_count = sum(1 for item in lines if item.chenh_lech < 0)
        excess_count = sum(1 for item in lines if item.chenh_lech > 0)
        return {
            "total": len(lines),
            "match": match_count,
            "shortage": shortage_count,
            "excess": excess_count,
        }


class ChiTietKiemKe(models.Model):
    """Inventory Count Detail Line (Bảng 65 - ChiTietKiemKe)."""

    class ReconciliationStatus(models.TextChoices):
        MATCH = "MATCH", "Khớp"
        SHORTAGE = "SHORTAGE", "Thiếu"
        EXCESS = "EXCESS", "Thừa"

    kiem_ke = models.ForeignKey(
        KiemKe,
        verbose_name="Biên bản kiểm kê",
        on_delete=models.CASCADE,
        related_name="lines",
    )
    bien_the = models.ForeignKey(
        "catalog.BienThe",
        verbose_name="Biến thể sản phẩm (SKU)",
        on_delete=models.PROTECT,
        related_name="stocktake_lines",
    )
    so_luong_he_thong = models.IntegerField("Số lượng hệ thống (Snapshot)")
    so_luong_thuc_te = models.IntegerField("Số lượng kiểm thực tế")
    chenh_lech = models.IntegerField("Chênh lệch (Thực tế - Hệ thống)")
    trang_thai_doi_chieu = models.CharField(
        "Trạng thái đối chiếu",
        max_length=20,
        choices=ReconciliationStatus.choices,
        default=ReconciliationStatus.MATCH,
    )
    don_vi_tinh = models.CharField("Đơn vị tính", max_length=50, default="Cái")
    don_gia = models.DecimalField("Đơn giá tại thời điểm kiểm kê", max_digits=14, decimal_places=0, default=Decimal("0"))
    xu_ly = models.CharField("Hướng xử lý chênh lệch", max_length=255, blank=True, default="")
    ghi_chu = models.TextField("Ghi chú", blank=True, default="")

    class Meta:
        db_table = "chi_tiet_kiem_ke"
        verbose_name = "Chi tiết biên bản kiểm kê"
        verbose_name_plural = "Chi tiết biên bản kiểm kê"
        constraints = [
            models.UniqueConstraint(
                fields=["kiem_ke", "bien_the"],
                name="uniq_stocktake_variant_line",
            ),
            models.CheckConstraint(
                condition=Q(so_luong_he_thong__gte=0) & Q(so_luong_thuc_te__gte=0),
                name="ct_kiem_ke_nonnegative_quantities",
            ),
        ]

    def clean(self):
        super().clean()
        if self.so_luong_thuc_te is not None and self.so_luong_thuc_te < 0:
            raise ValidationError({"so_luong_thuc_te": "Số lượng kiểm kê thực tế không được nhỏ hơn 0."})
        if self.so_luong_he_thong is not None and self.so_luong_thuc_te is not None:
            self.chenh_lech = self.so_luong_thuc_te - self.so_luong_he_thong
            if self.chenh_lech == 0:
                self.trang_thai_doi_chieu = self.ReconciliationStatus.MATCH
            elif self.chenh_lech < 0:
                self.trang_thai_doi_chieu = self.ReconciliationStatus.SHORTAGE
            else:
                self.trang_thai_doi_chieu = self.ReconciliationStatus.EXCESS

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)
