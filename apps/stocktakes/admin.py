from django.contrib import admin
from .models import ChiTietKiemKe, KiemKe


class ChiTietKiemKeInline(admin.TabularInline):
    model = ChiTietKiemKe
    extra = 0


@admin.register(KiemKe)
class KiemKeAdmin(admin.ModelAdmin):
    list_display = ("ma_kiem_ke", "co_so", "ngay_kiem", "nguoi_kiem_ke", "trang_thai", "tao_boi", "duyet_boi")
    list_filter = ("trang_thai", "co_so")
    search_fields = ("ma_kiem_ke", "muc_dich", "nguoi_kiem_ke")
    inlines = [ChiTietKiemKeInline]
