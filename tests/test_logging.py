from __future__ import annotations

import logging
from typing import cast

from django.conf import settings

from apps.core.logging import SensitiveDataFilter


def test_sensitive_logging_filter_redacts_credentials_and_costs() -> None:
    record = logging.LogRecord(
        "shop.operations",
        logging.ERROR,
        __file__,
        1,
        "pin:2468 cost_price=100000",
        (),
        None,
    )
    assert SensitiveDataFilter().filter(record) is True
    assert record.getMessage() == "pin=[REDACTED] cost_price=[REDACTED]"


def test_logging_configuration_uses_imported_redaction_filter() -> None:
    filters = cast(dict[str, dict[str, type[SensitiveDataFilter]]], settings.LOGGING["filters"])
    assert filters["redact"]["()"] is SensitiveDataFilter
