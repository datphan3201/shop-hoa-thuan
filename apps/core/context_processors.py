from typing import Any

from django.http import HttpRequest


def application_context(request: HttpRequest) -> dict[str, Any]:
    return {
        "application_name": "Shop Hoà Thuận",
        "cost_price_unlocked": bool(request.session.get("cost_price_unlocked_until")),
    }
