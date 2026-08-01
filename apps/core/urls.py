from django.urls import path
from django.views.generic import RedirectView

from apps.core import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("settings/security/", views.security_settings, name="security-settings"),
    path("settings/security/action/", views.security_action, name="security-action"),
    path(
        "operations/idempotency/<str:operation>/<str:key>/",
        views.idempotency_status,
        name="idempotency-status",
    ),
    path(
        "settings/device-access/",
        views.device_access_settings,
        name="device-access-settings",
    ),
    path(
        "settings/device-access/backup/create/",
        views.create_backup_view,
        name="backup-create",
    ),
    path(
        "settings/device-access/backup/restore/",
        views.restore_backup_view,
        name="backup-restore",
    ),
    path(
        "settings/device-access/backup/<str:filename>/",
        views.download_backup,
        name="backup-download",
    ),
]
