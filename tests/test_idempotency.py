from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import close_old_connections
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Category
from apps.core.idempotency import IdempotencyConflictError, execute
from apps.core.models import IdempotencyRecord


@pytest.mark.django_db(transaction=True)
def test_concurrent_retries_with_same_key_commit_work_once() -> None:
    user = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
    barrier = Barrier(2)

    def submit() -> bool:
        close_old_connections()
        barrier.wait(timeout=5)
        try:
            outcome = execute(
                user=user,
                operation="test.write",
                key="same-mobile-request",
                payload={"value": 1},
                work=lambda: Category.objects.create(name="Chỉ tạo một lần"),
                location=lambda category: f"/categories/{category.pk}/",
            )
            return outcome.replayed
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: submit(), range(2)))

    assert sorted(outcomes) == [False, True]
    assert Category.objects.filter(name="Chỉ tạo một lần").count() == 1
    assert IdempotencyRecord.objects.filter(operation="test.write").count() == 1


@pytest.mark.django_db
def test_same_key_with_different_payload_is_rejected() -> None:
    user = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
    execute(
        user=user,
        operation="test.write",
        key="same-key",
        payload={"value": 1},
        work=lambda: Category.objects.create(name="Lần đầu"),
        location=lambda category: f"/categories/{category.pk}/",
    )

    with pytest.raises(IdempotencyConflictError, match="không khớp"):
        execute(
            user=user,
            operation="test.write",
            key="same-key",
            payload={"value": 2},
            work=lambda: Category.objects.create(name="Không được tạo"),
            location=lambda category: f"/categories/{category.pk}/",
        )

    assert not Category.objects.filter(name="Không được tạo").exists()


@pytest.mark.django_db
def test_idempotency_cleanup_keeps_recent_records_and_removes_expired() -> None:
    user = User.objects.create_user(username="chushop", password="MatKhau-Rieng-2026!")
    expired = IdempotencyRecord.objects.create(
        user=user, operation="test", key="expired", fingerprint="a" * 64
    )
    IdempotencyRecord.objects.filter(pk=expired.pk).update(
        created_at=timezone.now() - timedelta(days=31)
    )
    recent = IdempotencyRecord.objects.create(
        user=user, operation="test", key="recent", fingerprint="b" * 64
    )

    call_command("purge_idempotency", days=30)

    assert not IdempotencyRecord.objects.filter(pk=expired.pk).exists()
    assert IdempotencyRecord.objects.filter(pk=recent.pk).exists()


@pytest.mark.django_db
def test_status_endpoint_only_returns_completed_operation_to_its_owner(client: Client) -> None:
    owner = User.objects.create_user(username="owner", password="MatKhau-Rieng-2026!")
    other = User.objects.create_user(username="other", password="MatKhau-Rieng-2026!")
    IdempotencyRecord.objects.create(
        user=owner,
        operation="sale.complete",
        key="request-1",
        fingerprint="a" * 64,
        response_location="/sales/1/",
    )
    url = reverse("idempotency-status", args=["sale.complete", "request-1"])

    assert client.get(url).status_code == 302
    client.force_login(other)
    assert client.get(url).status_code == 404
    client.force_login(owner)
    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == {"status": "completed", "location": "/sales/1/"}
