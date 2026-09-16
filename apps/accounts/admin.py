from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "full_name", "role", "branch", "is_active", "is_staff")
    list_filter = ("role", "branch", "is_active")
    search_fields = ("username", "full_name", "email")
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Thông tin nghiệp vụ Old School",
            {"fields": ("full_name", "role", "branch", "failed_login_attempts", "locked_until")},
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Thông tin nghiệp vụ Old School",
            {"fields": ("full_name", "role", "branch")},
        ),
    )
