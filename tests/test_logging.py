from __future__ import annotations

import logging

from apps.core.logging import SensitiveDataFilter


def test_sensitive_logging_filter_redacts_credentials_and_costs() -> None:
    record = logging.LogRecord(
        "shop.operations",
        logging.ERROR,
        __file__,
        1,
        "password=abc pin:2468 cost_price=100000",
        (),
        None,
    )
    assert SensitiveDataFilter().filter(record) is True
    assert record.getMessage() == "password=[REDACTED] pin=[REDACTED] cost_price=[REDACTED]"
