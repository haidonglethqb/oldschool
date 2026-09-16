from django.conf import settings
from django.db import models


class CoSo(models.Model):
    """Represent a physical store branch or central warehouse (Bảng 63 - CoSo)."""

    ma_co_so = models.CharField(
        "Mã cơ sở",
        max_length=30,
        unique=True,
        db_index=True,
    )
    ten_co_so = models.CharField("Tên cơ sở", max_length=150)
    dia_chi = models.CharField("Địa chỉ", max_length=255)
    sdt = models.CharField("Số điện thoại", max_length=25)
    is_central_warehouse = models.BooleanField(
        "Là kho tổng",
        default=False,
        help_text="Đánh dấu cơ sở đóng vai trò Kho tổng (CS1).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "co_so"
        verbose_name = "Cơ sở"
        verbose_name_plural = "Danh sách Cơ sở"
        ordering = ["ma_co_so"]

    def __str__(self) -> str:
        return f"{self.ten_co_so} ({self.ma_co_so})"

    @classmethod
    def get_central_warehouse(cls):
        """Return the central warehouse branch without hardcoding primary keys."""
        cw = cls.objects.filter(is_central_warehouse=True).first()
        if cw:
            return cw
        code = getattr(settings, "CENTRAL_WAREHOUSE_CODE", "CS1")
        return cls.objects.filter(ma_co_so=code).first()
