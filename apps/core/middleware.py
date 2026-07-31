from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.operations import MAINTENANCE_MESSAGE, OperationBusyError, begin_write

_MAINTENANCE_ENTRYPOINTS = {
    "/settings/device-access/backup/create/",
}


class WriteOperationMiddleware:
    """Track ordinary HTTP writes so operational maintenance can drain safely."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if (
            request.method not in {"POST", "PUT", "PATCH", "DELETE"}
            or request.path in _MAINTENANCE_ENTRYPOINTS
        ):
            return self.get_response(request)
        try:
            write = begin_write(request.path)
        except OperationBusyError:
            return HttpResponse(
                MAINTENANCE_MESSAGE, status=503, content_type="text/plain; charset=utf-8"
            )
        try:
            return self.get_response(request)
        finally:
            write.close()
