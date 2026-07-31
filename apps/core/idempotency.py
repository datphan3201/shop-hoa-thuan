from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from time import sleep
from uuid import uuid4

from django.db import IntegrityError, OperationalError, transaction
from django.http import HttpRequest

from apps.core.models import IdempotencyRecord


class IdempotencyConflictError(ValueError):
    pass


@dataclass(frozen=True)
class IdempotencyResult[ResultT]:
    result: ResultT
    replayed: bool


def request_fingerprint(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def client_key(request: HttpRequest) -> str:
    """Stable anonymous browser key; it survives cost-PIN session key rotation."""
    value = request.session.get("idempotency_client_key")
    if isinstance(value, str) and value:
        return value
    value = uuid4().hex
    request.session["idempotency_client_key"] = value
    return value


def replay_location(*, client: str, operation: str, key: str, payload: object) -> str | None:
    """Return a completed result before validating a retried stale form."""
    record = IdempotencyRecord.objects.filter(
        client_key=client, operation=operation, key=key
    ).first()
    if record is None:
        return None
    if record.fingerprint != request_fingerprint(payload):
        raise IdempotencyConflictError("Mã gửi lại không khớp với dữ liệu ban đầu.")
    return record.response_location


def execute[ResultT](
    *,
    client: str,
    operation: str,
    key: str,
    payload: object,
    work: Callable[[], ResultT],
    location: Callable[[ResultT], str],
) -> IdempotencyResult[ResultT | None]:
    """Run a write exactly once for an anonymous browser/key/payload combination.

    The record is deliberately inserted in the same transaction as ``work``.
    A competing SQLite writer can therefore only observe a committed operation;
    lock contention is retried before returning a result to the client.
    """
    fingerprint = request_fingerprint(payload)
    for attempt in range(6):
        try:
            with transaction.atomic():
                record = (
                    IdempotencyRecord.objects.select_for_update()
                    .filter(client_key=client, operation=operation, key=key)
                    .first()
                )
                if record:
                    if record.fingerprint != fingerprint:
                        raise IdempotencyConflictError("Mã gửi lại không khớp với dữ liệu ban đầu.")
                    return IdempotencyResult(None, True)
                result = work()
                IdempotencyRecord.objects.create(
                    client_key=client,
                    operation=operation,
                    key=key,
                    fingerprint=fingerprint,
                    response_location=location(result),
                )
                return IdempotencyResult(result, False)
        except IntegrityError:
            # A unique-key collision means another process committed the same
            # operation while this process was creating its record.  Re-read it
            # outside the rolled-back transaction and preserve its result.
            record = IdempotencyRecord.objects.filter(
                client_key=client, operation=operation, key=key
            ).first()
            if record is None:
                raise
            if record.fingerprint != fingerprint:
                raise IdempotencyConflictError(
                    "Mã gửi lại không khớp với dữ liệu ban đầu."
                ) from None
            return IdempotencyResult(None, True)
        except OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == 5:
                raise
            sleep(0.05 * (attempt + 1))
    raise RuntimeError("Không thể hoàn tất thao tác gửi lại.")
