from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


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
        "product-create",
        "inventory-list",
        "sale-list",
        "sale-create",
        "report-overview",
        "security-settings",
        "device-access-settings",
    ],
)
def test_management_pages_require_login(client: Client, route_name: str) -> None:
    response = client.get(reverse(route_name))

    assert response.status_code == 302
    assert response.headers["Location"].startswith(reverse("login"))


@pytest.mark.django_db
def test_first_run_setup_creates_only_owner_account(client: Client) -> None:
    response = client.post(
        reverse("first-run-setup"),
        {
            "username": "chushop",
            "password1": "MatKhau-Rieng-2026!",
            "password2": "MatKhau-Rieng-2026!",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("dashboard")
    owner = User.objects.get(username="chushop")
    assert owner.is_superuser is True
    assert owner.is_staff is True
    assert owner.check_password("MatKhau-Rieng-2026!")
    assert client.session.get("_auth_user_id") == str(owner.pk)


@pytest.mark.django_db
def test_login_redirects_to_setup_when_owner_does_not_exist(client: Client) -> None:
    response = client.get(reverse("login"))

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("first-run-setup")


@pytest.mark.django_db
def test_first_run_setup_closes_after_owner_exists(client: Client) -> None:
    User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")

    response = client.get(reverse("first-run-setup"))

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("login")


@pytest.mark.django_db
def test_authenticated_owner_can_open_all_phase_one_routes(client: Client) -> None:
    owner = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
    client.force_login(owner)

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
