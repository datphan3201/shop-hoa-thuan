from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import connection
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.http.response import HttpResponseBase
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.core.backup import BackupError, create_backup, list_backups
from apps.core.forms import OwnerAuthenticationForm, OwnerSetupForm

User = get_user_model()


class OwnerLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = OwnerAuthenticationForm
    redirect_authenticated_user = True

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponseBase:
        if not User.objects.exists():
            return redirect("first-run-setup")
        return super().dispatch(request, *args, **kwargs)


def first_run_setup(request: HttpRequest) -> HttpResponse:
    if User.objects.exists():
        return redirect("dashboard" if request.user.is_authenticated else "login")

    form = OwnerSetupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Đã tạo tài khoản chủ shop.")
        return redirect("dashboard")

    return render(request, "registration/first_run_setup.html", {"form": form})


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "core/dashboard.html")


@login_required
def security_settings(request: HttpRequest) -> HttpResponse:
    return render(request, "core/security_settings.html")


@login_required
def device_access_settings(request: HttpRequest) -> HttpResponse:
    return render(request, "core/device_access_settings.html", {"backups": list_backups()})


@login_required
@require_POST
def create_backup_view(request: HttpRequest) -> HttpResponse:
    try:
        backup = create_backup()
    except BackupError:
        messages.error(request, "Không thể tạo bản sao lưu. Vui lòng thử lại.")
    else:
        messages.success(request, f"Đã tạo bản sao lưu {backup.path.name}.")
    return redirect("device-access-settings")


@login_required
@require_GET
def download_backup(request: HttpRequest, filename: str) -> FileResponse:
    if filename != Path(filename).name:
        raise Http404
    matching_backup = next(
        (backup for backup in list_backups() if backup.path.name == filename),
        None,
    )
    if matching_backup is None:
        raise Http404
    return FileResponse(
        matching_backup.path.open("rb"),
        as_attachment=True,
        filename=matching_backup.path.name,
    )


@require_GET
@never_cache
def health(request: HttpRequest) -> JsonResponse:
    database_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        database_ok = False

    return JsonResponse(
        {"status": "ok" if database_ok else "error", "database": database_ok},
        status=200 if database_ok else 503,
    )
