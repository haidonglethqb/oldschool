from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.product_list_view, name="product_list"),
    path("create/", views.product_create_view, name="product_create"),
    path("<int:pk>/", views.product_detail_view, name="product_detail"),
    path("<int:pk>/edit/", views.product_edit_view, name="product_edit"),
    path("<int:pk>/delete/", views.product_delete_view, name="product_delete"),
    path("<int:pk>/toggle-status/", views.product_toggle_status_view, name="product_toggle_status"),
]
