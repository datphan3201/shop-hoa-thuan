from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.db.models import F, Model


class ConcurrentUpdateError(ValueError):
    """The record was changed after the editor loaded it."""


def save_with_revision(
    instance: Model,
    *,
    expected_revision: int,
    update_fields: Iterable[str] | None = None,
) -> None:
    """Persist ``instance`` only when its revision is still current.

    Claiming the next revision first makes the compare-and-save atomic.  A
    second editor with the old revision cannot overwrite the first editor,
    including on SQLite where ``SELECT FOR UPDATE`` is not sufficient.
    """
    if instance.pk is None:
        raise ValueError("Không thể kiểm soát phiên bản của bản ghi chưa lưu.")
    with transaction.atomic():
        claimed = (
            type(instance)
            ._default_manager.filter(pk=instance.pk, revision=expected_revision)
            .update(revision=F("revision") + 1)
        )
        if claimed != 1:
            raise ConcurrentUpdateError(
                "Dữ liệu này đã được thay đổi trên thiết bị khác. Vui lòng tải lại rồi thử lại."
            )
        instance.revision = expected_revision + 1  # type: ignore[attr-defined]
        if update_fields is None:
            instance.save()
            return
        fields = set(update_fields)
        fields.update({"revision", "updated_at"})
        instance.save(update_fields=sorted(fields))
