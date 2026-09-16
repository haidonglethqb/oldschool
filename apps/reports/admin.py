from django.contrib import admin
from .models import BaoCao


@admin.register(BaoCao)
class BaoCaoAdmin(admin.ModelAdmin):
    list_display = (
        "ma_bao_cao",
        "co_so",
        "bien_the",
        "tu_ngay",
        "den_ngay",
        "ton_dau_ky",
        "nhap_kho",
        "xuat_kho",
        "ton_cuoi_ky",
        "gia_tri_ton_kho",
    )
    list_filter = ("co_so", "trang_thai")
    search_fields = ("ma_bao_cao", "bien_the__ma_sku")
