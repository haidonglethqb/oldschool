from django.urls import path
from apps.transfers import views

app_name = "transfers"

urlpatterns = [
    path("", views.transfer_list_view, name="transfer_list"),
    path("create/", views.transfer_create_view, name="transfer_create"),
    path("<int:transfer_id>/", views.transfer_detail_view, name="transfer_detail"),
    path("<int:transfer_id>/accept/", views.transfer_accept_view, name="transfer_accept"),
    path("<int:transfer_id>/reject/", views.transfer_reject_view, name="transfer_reject"),
    path("<int:transfer_id>/dispatch/", views.transfer_dispatch_view, name="transfer_dispatch"),
    path("<int:transfer_id>/receive/", views.transfer_receive_view, name="transfer_receive"),
]
