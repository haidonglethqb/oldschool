from django.contrib import admin
from .models import CoSo


@admin.register(CoSo)
class CoSoAdmin(admin.ModelAdmin):
    list_display = ("ma_co_so", "ten_co_so", "sdt", "dia_chi", "is_central_warehouse")
    search_fields = ("ma_co_so", "ten_co_so", "sdt")
    list_filter = ("is_central_warehouse",)
