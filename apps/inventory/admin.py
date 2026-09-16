from django.contrib import admin
from .models import StockMovement, TonKho


@admin.register(TonKho)
class TonKhoAdmin(admin.ModelAdmin):
    list_display = ("co_so", "bien_the", "so_luong", "muc_ton_toi_thieu", "updated_at")
    list_filter = ("co_so",)
    search_fields = ("bien_the__ma_sku", "bien_the__san_pham__ten_hang_hoa", "bien_the__san_pham__ma_san_pham")
    readonly_fields = ("so_luong", "updated_at")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "effective_at",
        "co_so",
        "bien_the",
        "movement_type",
        "quantity_delta",
        "balance_after",
        "source_doc_code",
        "actor",
    )
    list_filter = ("co_so", "movement_type")
    search_fields = ("bien_the__ma_sku", "source_doc_code", "idempotency_key")
    readonly_fields = [f.name for f in StockMovement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
