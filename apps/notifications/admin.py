from django.contrib import admin
from .models import ThongBao


@admin.register(ThongBao)
class ThongBaoAdmin(admin.ModelAdmin):
    list_display = ("created_at", "loai_thong_bao", "tieu_de", "nguoi_nhan", "co_so", "da_doc", "da_xu_ly")
    list_filter = ("loai_thong_bao", "da_doc", "da_xu_ly", "co_so")
    search_fields = ("tieu_de", "noi_dung")
