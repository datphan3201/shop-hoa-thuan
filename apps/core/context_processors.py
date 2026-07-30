from typing import Any

from django.http import HttpRequest

from apps.core.security import is_cost_price_unlocked


def application_context(request: HttpRequest) -> dict[str, Any]:
    return {
        "application_name": "Shop Hoà Thuận",
        "cost_price_unlocked": is_cost_price_unlocked(request),
    }
