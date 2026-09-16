from django.contrib import admin
from .models import ChiTietPhieuNhapKho, NhaCungCap, PhieuNhapKho


class ChiTietPhieuNhapKhoInline(admin.TabularInline):
    model = ChiTietPhieuNhapKho
    extra = 0


@admin.register(NhaCungCap)
class NhaCungCapAdmin(admin.ModelAdmin):
    list_display = ("ma_nha_cung_cap", "ten_nha_cung_cap", "sdt", "dia_chi")
    search_fields = ("ma_nha_cung_cap", "ten_nha_cung_cap", "sdt")


@admin.register(PhieuNhapKho)
class PhieuNhapKhoAdmin(admin.ModelAdmin):
    list_display = ("ma_phieu_nhap_kho", "nha_cung_cap", "co_so_nhan", "ngay_nhap", "tong_tien", "trang_thai", "nguoi_tao")
    list_filter = ("trang_thai", "co_so_nhan", "nha_cung_cap")
    search_fields = ("ma_phieu_nhap_kho", "nha_cung_cap__ten_nha_cung_cap")
    inlines = [ChiTietPhieuNhapKhoInline]
