from django.contrib import admin
from .models import BienThe, SanPham


class BienTheInline(admin.TabularInline):
    model = BienThe
    extra = 1


@admin.register(SanPham)
class SanPhamAdmin(admin.ModelAdmin):
    list_display = ("ma_san_pham", "ten_hang_hoa", "nhom_hang", "don_vi_tinh", "don_gia_niem_yet", "trang_thai")
    search_fields = ("ma_san_pham", "ten_hang_hoa", "nhom_hang")
    list_filter = ("nhom_hang", "trang_thai")
    inlines = [BienTheInline]


@admin.register(BienThe)
class BienTheAdmin(admin.ModelAdmin):
    list_display = ("ma_sku", "san_pham", "mau_sac", "kich_co", "don_gia", "trang_thai")
    search_fields = ("ma_sku", "san_pham__ma_san_pham", "san_pham__ten_hang_hoa")
    list_filter = ("mau_sac", "kich_co", "trang_thai")
