from django.urls import path
from apps.sales_outbound import views

app_name = "sales_outbound"

urlpatterns = [
    path("", views.outbound_list_view, name="outbound_list"),
    path("create/", views.outbound_create_view, name="outbound_create"),
    path("<int:receipt_id>/", views.outbound_detail_view, name="outbound_detail"),
    path("<int:receipt_id>/edit/", views.outbound_update_view, name="outbound_update"),
    path("<int:receipt_id>/finalize/", views.outbound_finalize_view, name="outbound_finalize"),
    path("<int:receipt_id>/delete/", views.outbound_delete_view, name="outbound_delete"),
    path("<int:receipt_id>/print/", views.outbound_print_view, name="outbound_print"),
    path("requests/", views.request_list_create_view, name="request_list"),
    path("requests/<int:request_id>/reject/", views.request_reject_view, name="request_reject"),
]
