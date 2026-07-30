from __future__ import annotations

import time

import pytest
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Category, Product, ProductVariant
from apps.core.models import ShopSecuritySettings
from apps.core.security import BLOCKED_UNTIL_KEY, UNLOCKED_UNTIL_KEY


@pytest.fixture
def authenticated_client(db: None, client: Client) -> Client:
    owner = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
    client.force_login(owner)
    return client


@pytest.mark.django_db
def test_cost_price_is_locked_by_default(authenticated_client: Client) -> None:
    response = authenticated_client.get(reverse("security-settings"))

    assert response.status_code == 200
    assert UNLOCKED_UNTIL_KEY not in authenticated_client.session
    assert "Đang khóa" in response.content.decode()


@pytest.mark.django_db
def test_pin_setup_stores_hash_and_unlocks(authenticated_client: Client) -> None:
    response = authenticated_client.post(
        reverse("security-action"),
        {"action": "setup", "new_pin": "2468", "confirm_pin": "2468"},
    )

    security = ShopSecuritySettings.objects.get(pk=1)
    assert response.status_code == 302
    assert security.cost_price_pin_hash != "2468"
    assert security.cost_price_pin_hash.startswith("pbkdf2_")
    assert authenticated_client.session[UNLOCKED_UNTIL_KEY] > time.time()


@pytest.mark.django_db
def test_wrong_pin_does_not_unlock_and_uses_generic_message(
    authenticated_client: Client,
) -> None:
    ShopSecuritySettings.objects.create(cost_price_pin_hash=make_password("2468"))

    response = authenticated_client.post(
        reverse("security-action"),
        {"action": "unlock", "pin": "0000"},
        follow=True,
    )

    assert UNLOCKED_UNTIL_KEY not in authenticated_client.session
    assert "Mã bảo vệ không chính xác." in response.content.decode()


@pytest.mark.django_db
def test_correct_pin_unlocks_and_manual_lock_removes_session(
    authenticated_client: Client,
) -> None:
    ShopSecuritySettings.objects.create(
        cost_price_pin_hash=make_password("2468"),
        cost_price_lock_timeout_minutes=10,
    )

    authenticated_client.post(
        reverse("security-action"),
        {"action": "unlock", "pin": "2468"},
    )
    assert authenticated_client.session[UNLOCKED_UNTIL_KEY] > time.time()

    authenticated_client.post(reverse("security-action"), {"action": "lock"})
    assert UNLOCKED_UNTIL_KEY not in authenticated_client.session


@pytest.mark.django_db
def test_five_wrong_attempts_temporarily_block_correct_pin(
    authenticated_client: Client,
) -> None:
    ShopSecuritySettings.objects.create(cost_price_pin_hash=make_password("2468"))

    for _ in range(5):
        authenticated_client.post(
            reverse("security-action"),
            {"action": "unlock", "pin": "0000"},
        )
    assert authenticated_client.session[BLOCKED_UNTIL_KEY] > time.time()

    authenticated_client.post(
        reverse("security-action"),
        {"action": "unlock", "pin": "2468"},
    )
    assert UNLOCKED_UNTIL_KEY not in authenticated_client.session


@pytest.mark.django_db
def test_expired_unlock_is_removed_and_cost_edit_redirects(
    authenticated_client: Client,
) -> None:
    category = Category.objects.create(name="Áo thun")
    product = Product.objects.create(category=category, name="Áo thun")
    variant = ProductVariant.objects.create(product=product, size="M")
    session = authenticated_client.session
    session[UNLOCKED_UNTIL_KEY] = time.time() - 1
    session.save()

    response = authenticated_client.get(reverse("variant-update", args=[variant.pk]))

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("security-settings")
    assert UNLOCKED_UNTIL_KEY not in authenticated_client.session


@pytest.mark.django_db
def test_logout_flushes_cost_unlock(authenticated_client: Client) -> None:
    session = authenticated_client.session
    session[UNLOCKED_UNTIL_KEY] = time.time() + 600
    session.save()

    authenticated_client.post(reverse("logout"))

    assert UNLOCKED_UNTIL_KEY not in authenticated_client.session


@pytest.mark.django_db
def test_dashboard_does_not_render_sensitive_numbers_while_locked(
    authenticated_client: Client,
) -> None:
    category = Category.objects.create(name="Áo thun")
    product = Product.objects.create(category=category, name="Áo thun")
    ProductVariant.objects.create(
        product=product,
        size="M",
        cost_price=123_456,
        selling_price=200_000,
        quantity=2,
    )

    response = authenticated_client.get(reverse("dashboard"))
    html = response.content.decode()

    assert "123.456 ₫" not in html
    assert "•••••• ₫" in html


@pytest.mark.django_db
def test_dashboard_renders_inventory_cost_and_profit_only_when_unlocked(
    authenticated_client: Client,
) -> None:
    category = Category.objects.create(name="Áo thun")
    product = Product.objects.create(category=category, name="Áo thun")
    ProductVariant.objects.create(
        product=product,
        size="M",
        cost_price=100_000,
        selling_price=180_000,
        quantity=2,
    )
    session = authenticated_client.session
    session[UNLOCKED_UNTIL_KEY] = time.time() + 600
    session.save()

    response = authenticated_client.get(reverse("dashboard"))
    html = response.content.decode()

    assert "200.000 ₫" in html
    assert "160.000 ₫" in html
    assert "44,4%" in html
