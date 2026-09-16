"""Root URL configuration for Old School Inventory Management System."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("catalog:product_list")
    return redirect("accounts:login")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", root_redirect, name="home"),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("catalog/", include("apps.catalog.urls", namespace="catalog")),
    path("inventory/", include("apps.inventory.urls", namespace="inventory")),
    path("purchasing/", include("apps.purchasing.urls", namespace="purchasing")),
    path("outbound/", include("apps.sales_outbound.urls", namespace="sales_outbound")),
    path("transfers/", include("apps.transfers.urls", namespace="transfers")),
    path("stocktakes/", include("apps.stocktakes.urls", namespace="stocktakes")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
]

handler403 = "apps.accounts.views.custom_permission_denied_view"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
