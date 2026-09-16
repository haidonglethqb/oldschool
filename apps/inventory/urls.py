from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("api/variant-stock/", views.api_variant_stock_view, name="api_variant_stock"),
    path("templates/<str:template_type>/", views.download_excel_template_view, name="download_template"),
]
