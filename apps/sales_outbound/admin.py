from django.contrib import admin
from .models import (
    ChiTietPhieuXuatHangBan,
    ChiTietYeuCauXuatHang,
    PhieuXuatHangBan,
    YeuCauXuatHang,
)


class ChiTietPhieuXuatHangBanInline(admin.TabularInline):
    model = ChiTietPhieuXuatHangBan
    extra = 0


@admin.register(PhieuXuatHangBan)
class PhieuXuatHangBanAdmin(admin.ModelAdmin):
    list_display = ("ma_phieu_xuat_hang_ban", "co_so", "ngay_xuat", "tong_tien", "trang_thai", "nguoi_tao")
    list_filter = ("trang_thai", "co_so")
    search_fields = ("ma_phieu_xuat_hang_ban", "ten_khach_hang", "sdt")
    inlines = [ChiTietPhieuXuatHangBanInline]


class ChiTietYeuCauXuatHangInline(admin.TabularInline):
    model = ChiTietYeuCauXuatHang
    extra = 0


@admin.register(YeuCauXuatHang)
class YeuCauXuatHangAdmin(admin.ModelAdmin):
    list_display = ("ma_yeu_cau", "co_so", "nguoi_yeu_cau", "trang_thai", "ngay_yeu_cau")
    list_filter = ("trang_thai", "co_so")
    inlines = [ChiTietYeuCauXuatHangInline]
