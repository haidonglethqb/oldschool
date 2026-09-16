from django.urls import path
from apps.stocktakes import views

app_name = "stocktakes"

urlpatterns = [
    path("", views.stocktake_list_view, name="stocktake_list"),
    path("create/", views.stocktake_create_view, name="stocktake_create"),
    path("<int:stocktake_id>/", views.stocktake_detail_view, name="stocktake_detail"),
    path("<int:stocktake_id>/edit/", views.stocktake_update_view, name="stocktake_update"),
    path("<int:stocktake_id>/delete/", views.stocktake_delete_view, name="stocktake_delete"),
    path("<int:stocktake_id>/approve/", views.stocktake_approve_view, name="stocktake_approve"),
    path("<int:stocktake_id>/reject/", views.stocktake_reject_view, name="stocktake_reject"),
]
