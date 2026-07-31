from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core.views import OwnerLoginView, first_run_setup, health, protected_media

urlpatterns = [
    path("setup/", first_run_setup, name="first-run-setup"),
    path("login/", OwnerLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("health/", health, name="health"),
    path("media/<path:path>", protected_media, name="protected-media"),
    path("", include("apps.core.urls")),
    path("categories/", include("apps.catalog.category_urls")),
    path("products/", include("apps.catalog.product_urls")),
    path("inventory/", include("apps.catalog.inventory_urls")),
    path("sales/", include("apps.sales.urls")),
    path("reports/", include("apps.reports.urls")),
]

if settings.DEBUG:
    urlpatterns.insert(0, path("admin/", admin.site.urls))
