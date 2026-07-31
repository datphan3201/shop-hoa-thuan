from __future__ import annotations

import logging
import re


class SensitiveDataFilter(logging.Filter):
    """Remove credentials and cost fields from operational logs."""

    _pattern = re.compile(
        r"(?i)(password|pin|secret|csrf|session|authorization|cost_price)\s*[=:]\s*[^\s,;]+"
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        record.msg = self._pattern.sub(r"\1=[REDACTED]", message)
        record.args = ()
        return True
