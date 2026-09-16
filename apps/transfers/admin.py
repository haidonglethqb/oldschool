from django.contrib import admin
from .models import ChiTietPhieuDieuChuyen, PhieuDieuChuyen


class ChiTietPhieuDieuChuyenInline(admin.TabularInline):
    model = ChiTietPhieuDieuChuyen
    extra = 0


@admin.register(PhieuDieuChuyen)
class PhieuDieuChuyenAdmin(admin.ModelAdmin):
    list_display = (
        "ma_phieu_dieu_chuyen",
        "co_so_xuat",
        "co_so_nhan",
        "ngay_dieu_chuyen",
        "trang_thai",
        "nguoi_tao",
    )
    list_filter = ("trang_thai", "co_so_xuat", "co_so_nhan")
    search_fields = ("ma_phieu_dieu_chuyen", "ly_do")
    inlines = [ChiTietPhieuDieuChuyenInline]
