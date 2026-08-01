from __future__ import annotations

from unittest.mock import patch

import pytest
from django.conf import settings
from django.db import connection
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_health_check_reports_database_ready(client: Client) -> None:
    response = client.get(reverse("health"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] is True
    assert isinstance(payload["version"], str)
    assert payload["server_time_utc"].endswith("+00:00")
    assert payload["schema"] is True


@pytest.mark.django_db
def test_health_reports_schema_incompatible_without_details(client: Client) -> None:
    with patch("apps.core.views.schema_is_compatible", return_value=False):
        response = client.get(reverse("health"))
    assert response.status_code == 503
    assert response.json()["status"] == "schema_incompatible"


@pytest.mark.django_db
def test_health_reports_database_unavailable_without_exception_details(client: Client) -> None:
    with patch("apps.core.views.connection.cursor", side_effect=RuntimeError("/secret/path")):
        response = client.get(reverse("health"))
    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert "/secret/path" not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route_name",
    [
        "dashboard",
        "category-list",
        "product-list",
        "inventory-list",
        "sale-list",
        "sale-create",
        "report-overview",
        "security-settings",
        "device-access-settings",
    ],
)
def test_management_pages_are_available_without_an_account(client: Client, route_name: str) -> None:
    response = client.get(reverse(route_name))

    assert response.status_code == 200


@pytest.mark.django_db
def test_any_lan_browser_can_open_all_phase_one_routes(client: Client) -> None:
    route_names = (
        "dashboard",
        "category-list",
        "product-list",
        "inventory-list",
        "sale-list",
        "sale-create",
        "report-overview",
        "security-settings",
        "device-access-settings",
    )

    for route_name in route_names:
        response = client.get(reverse(route_name))
        assert response.status_code == 200, route_name


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/login/", "/logout/", "/setup/", "/admin/"])
def test_legacy_account_and_admin_routes_are_not_exposed(client: Client, path: str) -> None:
    assert client.get(path).status_code == 404


@pytest.mark.django_db
def test_application_exposes_no_account_routes_or_idempotency_user_column() -> None:
    assert "django.contrib.auth" not in settings.INSTALLED_APPS
    columns = connection.introspection.get_table_description(
        connection.cursor(), "core_idempotencyrecord"
    )
    assert "user_id" not in {column.name for column in columns}
