from pathlib import Path
from typing import cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.views import LoginView
from django.db import connection
from django.db.models import Count, F, IntegerField, Sum
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.http.response import HttpResponseBase
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from PIL import Image, UnidentifiedImageError

from apps.catalog.models import Product, ProductVariant
from apps.core.backup import BackupError, create_backup, list_backups
from apps.core.concurrency import ConcurrentUpdateError, save_with_revision
from apps.core.forms import (
    OwnerAuthenticationForm,
    OwnerSetupForm,
    PinChangeForm,
    PinSetupForm,
    PinUnlockForm,
    SecurityTimeoutForm,
)
from apps.core.idempotency import IdempotencyConflictError, request_fingerprint
from apps.core.models import IdempotencyRecord, ShopSecuritySettings
from apps.core.operations import maintenance_operation, maintenance_state
from apps.core.security import (
    cost_price_unlock_required,
    is_cost_price_unlocked,
    lock_cost_price,
    verify_and_unlock_cost_price,
)
from apps.reports.services import (
    build_report,
    daily_sales_series,
    monthly_sales_series,
    resolve_report_period,
)
from apps.sales.models import Sale
from shop_hoa_thuan.runner import schema_is_compatible
from shop_hoa_thuan.version import application_version

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
    variants = ProductVariant.objects.select_related("product")
    variant_list = list(
        variants.only(
            "quantity",
            "selling_price",
            "low_stock_threshold",
            "active",
            "product__active",
        )
    )
    alert_variants = [
        variant for variant in variant_list if variant.active and variant.product.active
    ]
    today_period = resolve_report_period({"period": "today"})
    month_period = resolve_report_period({"period": "this_month"})
    year_period = resolve_report_period({"period": "this_year"})
    today_report = build_report(today_period, include_cost=False)
    month_report = build_report(month_period, include_cost=False)
    year_report = build_report(year_period, include_cost=False)
    recent_sales = Sale.objects.annotate(
        total_quantity=Coalesce(Sum("items__quantity"), 0, output_field=IntegerField()),
        item_type_count=Count("items"),
    ).order_by("-sold_at", "-id")[:6]
    low_stock_variants = (
        ProductVariant.objects.filter(
            active=True,
            product__active=True,
            quantity__gt=0,
            quantity__lte=F("low_stock_threshold"),
        )
        .select_related("product")
        .order_by("quantity")[:8]
    )
    out_of_stock_variants = (
        ProductVariant.objects.filter(active=True, product__active=True, quantity=0)
        .select_related("product")
        .order_by("-updated_at")[:8]
    )
    projected_sales_value = sum(
        variant.quantity * variant.selling_price for variant in variant_list
    )
    context: dict[str, object] = {
        "active_product_count": Product.objects.filter(active=True).count(),
        "variant_count": len(variant_list),
        "total_quantity": sum(variant.quantity for variant in variant_list),
        "low_stock_count": sum(
            1 for variant in alert_variants if 0 < variant.quantity <= variant.low_stock_threshold
        ),
        "out_of_stock_count": sum(1 for variant in alert_variants if variant.quantity == 0),
        "projected_sales_value": projected_sales_value,
        "today_summary": today_report.summary,
        "month_summary": month_report.summary,
        "year_summary": year_report.summary,
        "daily_series": daily_sales_series(month_period),
        "monthly_series": monthly_sales_series(year_period.date_from.year),
        "recent_sales": recent_sales,
        "best_products": month_report.best_products[:6],
        "best_sizes": sorted(
            month_report.size_revenue,
            key=lambda row: (-row.quantity, -row.revenue, row.label.casefold()),
        )[:6],
        "category_revenue": month_report.category_revenue[:6],
        "payment_revenue": month_report.payment_revenue,
        "low_stock_variants": low_stock_variants,
        "out_of_stock_variants": out_of_stock_variants,
        "recent_products": Product.objects.select_related("category").order_by(
            "-updated_at", "-id"
        )[:6],
    }
    if is_cost_price_unlocked(request):
        sensitive_variants = list(ProductVariant.objects.only("quantity", "cost_price"))
        inventory_cost = sum(
            variant.quantity * variant.cost_price for variant in sensitive_variants
        )
        projected_sales = projected_sales_value
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
            try:
                save_with_revision(
                    security,
                    expected_revision=security.revision,
                    update_fields=["cost_price_pin_hash"],
                )
            except ConcurrentUpdateError:
                messages.error(request, "Thiết lập đã thay đổi. Vui lòng thử lại.")
            else:
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
            try:
                save_with_revision(
                    security,
                    expected_revision=security.revision,
                    update_fields=["cost_price_pin_hash"],
                )
            except ConcurrentUpdateError:
                messages.error(request, "Thiết lập đã thay đổi. Vui lòng thử lại.")
            else:
                verify_and_unlock_cost_price(request, change_form.cleaned_data["new_pin"])
                messages.success(request, "Đã đổi mã PIN bảo vệ.")
        else:
            messages.error(request, "Mã bảo vệ không chính xác.")
    elif action == "timeout":
        timeout_form = SecurityTimeoutForm(request.POST, instance=security)
        if timeout_form.is_valid():
            try:
                security = timeout_form.save(commit=False)
                save_with_revision(
                    security, expected_revision=timeout_form.cleaned_data["revision"]
                )
            except ConcurrentUpdateError:
                messages.error(request, "Thiết lập đã thay đổi. Vui lòng tải lại rồi thử lại.")
            else:
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
        key = request.headers.get("Idempotency-Key") or request.POST.get("idempotency_key", "")
        if key:
            owner = cast(DjangoUser, request.user)
            fingerprint = request_fingerprint({"requested": "backup"})
            with maintenance_operation("backup"):
                record = IdempotencyRecord.objects.filter(
                    user=owner, operation="backup.create", key=key[:128]
                ).first()
                if record:
                    if record.fingerprint != fingerprint:
                        raise IdempotencyConflictError("Mã gửi lại không khớp với dữ liệu ban đầu.")
                    return redirect(record.response_location)
                backup = create_backup()
                IdempotencyRecord.objects.create(
                    user=owner,
                    operation="backup.create",
                    key=key[:128],
                    fingerprint=fingerprint,
                    response_location=reverse("device-access-settings"),
                )
        else:
            with maintenance_operation("backup"):
                backup = create_backup()
    except (BackupError, IdempotencyConflictError, RuntimeError):
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


@login_required
@require_GET
def protected_media(request: HttpRequest, path: str) -> FileResponse:
    """Serve product media privately without exposing runtime filesystem paths."""
    media_root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (media_root / path).resolve()
    if media_root not in candidate.parents or not candidate.is_file():
        raise Http404
    try:
        with Image.open(candidate) as image:
            content_type = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
            }.get(image.format or "")
            image.verify()
    except (OSError, UnidentifiedImageError):
        raise Http404 from None
    if content_type is None:
        raise Http404
    response = FileResponse(candidate.open("rb"), content_type=content_type)
    response.headers["Cache-Control"] = "private, max-age=86400"
    return response


@login_required
@require_GET
def idempotency_status(request: HttpRequest, operation: str, key: str) -> JsonResponse:
    """Return only the replay location for the owner of a completed write."""
    if len(operation) > 64 or len(key) > 128:
        raise Http404
    record = IdempotencyRecord.objects.filter(
        user=cast(DjangoUser, request.user), operation=operation, key=key
    ).first()
    if record is None:
        raise Http404
    return JsonResponse({"status": "completed", "location": record.response_location})


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

    schema_ok = False
    if database_ok:
        try:
            schema_ok = schema_is_compatible()
        except Exception:
            database_ok = False
    maintenance = maintenance_state()
    status = "maintenance" if maintenance else ("ok" if schema_ok else "schema_incompatible")
    if not database_ok:
        status = "error"
    return JsonResponse(
        {
            "status": status,
            "database": database_ok,
            "schema": schema_ok,
            "version": application_version(),
            "server_time_utc": timezone.now().isoformat(),
            "maintenance": maintenance,
        },
        status=200 if status == "ok" else 503,
    )
