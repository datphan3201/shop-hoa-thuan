from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.views import LoginView
from django.db import connection
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.http.response import HttpResponseBase
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.catalog.models import Product, ProductVariant
from apps.core.backup import BackupError, create_backup, list_backups
from apps.core.forms import (
    OwnerAuthenticationForm,
    OwnerSetupForm,
    PinChangeForm,
    PinSetupForm,
    PinUnlockForm,
    SecurityTimeoutForm,
)
from apps.core.models import ShopSecuritySettings
from apps.core.security import (
    cost_price_unlock_required,
    is_cost_price_unlocked,
    lock_cost_price,
    verify_and_unlock_cost_price,
)

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
    variants = ProductVariant.objects.filter(active=True)
    variant_list = list(variants.only("quantity", "selling_price", "low_stock_threshold"))
    context: dict[str, object] = {
        "active_product_count": Product.objects.filter(active=True).count(),
        "variant_count": len(variant_list),
        "total_quantity": sum(variant.quantity for variant in variant_list),
        "low_stock_count": sum(
            1 for variant in variant_list if 0 < variant.quantity <= variant.low_stock_threshold
        ),
        "out_of_stock_count": sum(1 for variant in variant_list if variant.quantity == 0),
        "projected_sales_value": sum(
            variant.quantity * variant.selling_price for variant in variant_list
        ),
    }
    if is_cost_price_unlocked(request):
        sensitive_variants = list(
            ProductVariant.objects.filter(active=True).only(
                "quantity", "cost_price", "selling_price"
            )
        )
        inventory_cost = sum(
            variant.quantity * variant.cost_price for variant in sensitive_variants
        )
        projected_sales = sum(
            variant.quantity * variant.selling_price for variant in sensitive_variants
        )
        context["inventory_cost"] = inventory_cost
        context["projected_gross_profit"] = projected_sales - inventory_cost
        context["projected_margin"] = (
            (projected_sales - inventory_cost) / projected_sales * 100 if projected_sales else None
        )
        context["has_projected_margin"] = projected_sales > 0
    return render(request, "core/dashboard.html", context)


@login_required
def security_settings(request: HttpRequest) -> HttpResponse:
    security = ShopSecuritySettings.load()
    context = {
        "has_pin": bool(security.cost_price_pin_hash),
        "unlocked": is_cost_price_unlocked(request),
        "unlock_form": PinUnlockForm(),
        "setup_form": PinSetupForm(),
        "change_form": PinChangeForm(),
        "timeout_form": SecurityTimeoutForm(instance=security),
    }
    return render(request, "core/security_settings.html", context)


@login_required
@require_POST
def security_action(request: HttpRequest) -> HttpResponse:
    security = ShopSecuritySettings.load()
    action = request.POST.get("action")
    if action == "unlock":
        unlock_form = PinUnlockForm(request.POST)
        if unlock_form.is_valid() and verify_and_unlock_cost_price(
            request, unlock_form.cleaned_data["pin"]
        ):
            messages.success(request, "Đã mở khóa giá vốn.")
        else:
            messages.error(request, "Mã bảo vệ không chính xác.")
    elif action == "lock":
        lock_cost_price(request)
        messages.success(request, "Đã khóa giá vốn.")
    elif action == "setup" and not security.cost_price_pin_hash:
        setup_form = PinSetupForm(request.POST)
        if setup_form.is_valid():
            security.cost_price_pin_hash = make_password(setup_form.cleaned_data["new_pin"])
            security.save(update_fields=["cost_price_pin_hash", "updated_at"])
            verify_and_unlock_cost_price(request, setup_form.cleaned_data["new_pin"])
            messages.success(request, "Đã thiết lập mã PIN bảo vệ giá vốn.")
        else:
            messages.error(request, "Không thể thiết lập mã PIN. Vui lòng kiểm tra lại.")
    elif action == "change" and security.cost_price_pin_hash:
        change_form = PinChangeForm(request.POST)
        if change_form.is_valid() and verify_and_unlock_cost_price(
            request, change_form.cleaned_data["current_pin"]
        ):
            security.cost_price_pin_hash = make_password(change_form.cleaned_data["new_pin"])
            security.save(update_fields=["cost_price_pin_hash", "updated_at"])
            verify_and_unlock_cost_price(request, change_form.cleaned_data["new_pin"])
            messages.success(request, "Đã đổi mã PIN bảo vệ.")
        else:
            messages.error(request, "Mã bảo vệ không chính xác.")
    elif action == "timeout":
        timeout_form = SecurityTimeoutForm(request.POST, instance=security)
        if timeout_form.is_valid():
            timeout_form.save()
            lock_cost_price(request)
            messages.success(request, "Đã cập nhật thời gian tự khóa. Giá vốn đã được khóa.")
        else:
            messages.error(request, "Thời gian tự khóa không hợp lệ.")
    return redirect("security-settings")


@login_required
def device_access_settings(request: HttpRequest) -> HttpResponse:
    return render(request, "core/device_access_settings.html", {"backups": list_backups()})


@login_required
@cost_price_unlock_required
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
@cost_price_unlock_required
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
