from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from time import sleep

from django.contrib.auth.models import User
from django.db import IntegrityError, OperationalError, transaction

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


def replay_location(*, user: User, operation: str, key: str, payload: object) -> str | None:
    """Return a completed result before validating a retried stale form."""
    record = IdempotencyRecord.objects.filter(user=user, operation=operation, key=key).first()
    if record is None:
        return None
    if record.fingerprint != request_fingerprint(payload):
        raise IdempotencyConflictError("Mã gửi lại không khớp với dữ liệu ban đầu.")
    return record.response_location


def execute[ResultT](
    *,
    user: User,
    operation: str,
    key: str,
    payload: object,
    work: Callable[[], ResultT],
    location: Callable[[ResultT], str],
) -> IdempotencyResult[ResultT | None]:
    """Run a write exactly once for a user/key/payload combination.

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
                    .filter(user=user, operation=operation, key=key)
                    .first()
                )
                if record:
                    if record.fingerprint != fingerprint:
                        raise IdempotencyConflictError("Mã gửi lại không khớp với dữ liệu ban đầu.")
                    return IdempotencyResult(None, True)
                result = work()
                IdempotencyRecord.objects.create(
                    user=user,
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
                user=user, operation=operation, key=key
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
