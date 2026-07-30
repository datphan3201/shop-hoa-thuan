from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.http import HttpRequest
from django.http.response import HttpResponseBase
from django.shortcuts import redirect

from apps.core.models import ShopSecuritySettings

UNLOCKED_UNTIL_KEY = "cost_price_unlocked_until"
FAILED_ATTEMPTS_KEY = "cost_price_failed_attempts"
BLOCKED_UNTIL_KEY = "cost_price_blocked_until"
MAX_FAILED_ATTEMPTS = 5
BLOCK_SECONDS = 5 * 60


def is_cost_price_unlocked(request: HttpRequest) -> bool:
    if not request.user.is_authenticated:
        return False
    unlocked_until = request.session.get(UNLOCKED_UNTIL_KEY)
    if not isinstance(unlocked_until, (int, float)) or unlocked_until <= time.time():
        request.session.pop(UNLOCKED_UNTIL_KEY, None)
        return False
    return True


def verify_and_unlock_cost_price(request: HttpRequest, pin: str) -> bool:
    now = time.time()
    blocked_until = request.session.get(BLOCKED_UNTIL_KEY, 0)
    if isinstance(blocked_until, (int, float)) and blocked_until > now:
        return False

    security_settings = ShopSecuritySettings.load()
    if not security_settings.cost_price_pin_hash:
        return False

    if not check_password(pin, security_settings.cost_price_pin_hash):
        attempts = int(request.session.get(FAILED_ATTEMPTS_KEY, 0)) + 1
        request.session[FAILED_ATTEMPTS_KEY] = attempts
        if attempts >= MAX_FAILED_ATTEMPTS:
            request.session[BLOCKED_UNTIL_KEY] = now + BLOCK_SECONDS
            request.session[FAILED_ATTEMPTS_KEY] = 0
        return False

    request.session.cycle_key()
    request.session[UNLOCKED_UNTIL_KEY] = (
        now + security_settings.cost_price_lock_timeout_minutes * 60
    )
    request.session.pop(FAILED_ATTEMPTS_KEY, None)
    request.session.pop(BLOCKED_UNTIL_KEY, None)
    return True


def lock_cost_price(request: HttpRequest) -> None:
    request.session.pop(UNLOCKED_UNTIL_KEY, None)


def cost_price_unlock_required(
    view: Callable[..., HttpResponseBase],
) -> Callable[..., HttpResponseBase]:
    @wraps(view)
    def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not is_cost_price_unlocked(request):
            messages.warning(request, "Mở khóa giá vốn để xem hoặc chỉnh sửa.")
            return redirect("security-settings")
        return view(request, *args, **kwargs)

    return wrapped
