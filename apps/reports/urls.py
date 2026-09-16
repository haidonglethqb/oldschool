from django.urls import path
from apps.reports import views

app_name = "reports"

urlpatterns = [
    path("", views.report_dashboard_view, name="report_dashboard"),
    path("variant/<int:variant_id>/", views.report_variant_detail_view, name="report_variant_detail"),
    path("save-snapshot/", views.report_save_snapshot_view, name="report_save_snapshot"),
]
