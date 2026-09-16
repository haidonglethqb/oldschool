from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Custom business user model supporting ADMIN, MANAGER, and STAFF roles."""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Chủ (Admin)"
        MANAGER = "MANAGER", "Quản lý cơ sở"
        STAFF = "STAFF", "Nhân viên bán hàng"

    full_name = models.CharField("Họ và tên", max_length=150, blank=True)
    role = models.CharField(
        "Vai trò",
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
        db_index=True,
    )
    branch = models.ForeignKey(
        "branches.CoSo",
        verbose_name="Cơ sở phụ trách",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField("Khóa tạm thời đến", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nguoi_dung"
        verbose_name = "Người dùng"
        verbose_name_plural = "Danh sách Người dùng"
        ordering = ["username"]

    def __str__(self) -> str:
        name = self.display_name
        return f"{name} ({self.get_role_display()})"

    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        full = f"{self.last_name} {self.first_name}".strip()
        return full or self.username

    @property
    def initials(self) -> str:
        parts = [p for p in self.display_name.split() if p]
        if len(parts) >= 2:
            return (parts[-2][0] + parts[-1][0]).upper()
        if parts:
            return parts[0][:2].upper()
        return "OS"

    @property
    def is_business_admin(self) -> bool:
        return self.is_active and self.role == self.Role.ADMIN

    @property
    def is_branch_manager(self) -> bool:
        return self.is_active and self.role == self.Role.MANAGER

    @property
    def is_sales_staff(self) -> bool:
        return self.is_active and self.role == self.Role.STAFF

    @property
    def role_badge_label(self) -> str:
        if self.role == self.Role.ADMIN:
            return "Chủ (Admin)"
        if self.role == self.Role.MANAGER and self.branch:
            return f"Quản lý {self.branch.ma_co_so}"
        if self.role == self.Role.STAFF and self.branch:
            return f"Nhân viên {self.branch.ma_co_so}"
        return self.get_role_display()

    def is_temporarily_locked(self) -> bool:
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def clean(self):
        super().clean()
        if self.role in {self.Role.MANAGER, self.Role.STAFF} and not self.branch_id:
            raise ValidationError(
                {"branch": "Quản lý cơ sở và Nhân viên bán hàng bắt buộc phải được gán cơ sở phụ trách."}
            )
