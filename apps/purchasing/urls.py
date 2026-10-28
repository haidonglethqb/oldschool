from django.urls import path
from apps.purchasing import views

app_name = "purchasing"

urlpatterns = [
    path("", views.import_list_view, name="import_list"),
    path("create/", views.import_create_view, name="import_create"),
    path("<int:receipt_id>/", views.import_detail_view, name="import_detail"),
    path("<int:receipt_id>/edit/", views.import_update_view, name="import_update"),
    path("<int:receipt_id>/delete/", views.import_delete_view, name="import_delete"),
    path("<int:receipt_id>/approve/", views.import_approve_view, name="import_approve"),
    path("<int:receipt_id>/return/", views.import_return_view, name="import_return"),
    path("<int:receipt_id>/propose-return/", views.import_propose_return_view, name="import_propose_return"),
    path("<int:receipt_id>/confirm-supplier-return/", views.import_confirm_supplier_return_view, name="import_confirm_supplier_return"),
    path("<int:receipt_id>/export-excel/", views.import_export_excel_view, name="import_export_excel"),
    path("export-report/", views.import_report_export_view, name="import_report_export"),
    path("suppliers/", views.supplier_list_create_view, name="supplier_list"),
]
