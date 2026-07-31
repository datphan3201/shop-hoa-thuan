from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, IntegerField, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.catalog.models import Category, ProductVariant
from apps.catalog.services import InsufficientStockError
from apps.core.security import is_cost_price_unlocked
from apps.sales.forms import SaleCancellationForm, SaleCreateForm
from apps.sales.models import Sale
from apps.sales.services import (
    SaleAlreadyCancelledError,
    SaleLineInput,
    SaleValidationError,
    cancel_sale,
    complete_sale,
)


def _available_variants(request: HttpRequest) -> Any:
    unlocked = is_cost_price_unlocked(request)
    variants = (
        ProductVariant.objects.filter(active=True, product__active=True, quantity__gt=0)
        .select_related("product", "product__category")
        .order_by("product__name", "size")
    )
    if not unlocked:
        variants = variants.defer("cost_price")

    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    if query:
        variants = variants.filter(
            Q(product__name__icontains=query)
            | Q(product__brand__icontains=query)
            | Q(sku__icontains=query)
        )
    if category_id.isdigit():
        variants = variants.filter(product__category_id=int(category_id))
    return variants[:60]


def _cart_rows(request: HttpRequest, lines: list[SaleLineInput]) -> list[dict[str, Any]]:
    if not lines:
        return []
    unlocked = is_cost_price_unlocked(request)
    variants = ProductVariant.objects.select_related("product", "product__category").filter(
        pk__in=[line.variant_id for line in lines]
    )
    if not unlocked:
        variants = variants.defer("cost_price")
    variant_map = {variant.pk: variant for variant in variants}
    rows: list[dict[str, Any]] = []
    for line in lines:
        variant = variant_map.get(line.variant_id)
        if variant is None:
            continue
        row: dict[str, Any] = {
            "variant_id": variant.pk,
            "product_name": variant.product.name,
            "category_name": variant.product.category.name,
            "size": variant.size,
            "color": variant.product.color,
            "sku": variant.sku,
            "quantity": line.quantity,
            "stock": variant.quantity,
            "listed_price": variant.selling_price,
            "actual_unit_price": line.actual_unit_price,
        }
        if unlocked:
            row["cost_price"] = variant.cost_price
        rows.append(row)
    return rows


def _parse_local_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _local_day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=ZoneInfo(settings.TIME_ZONE))


@login_required
def sale_list(request: HttpRequest) -> HttpResponse:
    sales = Sale.objects.annotate(
        item_type_count=Count("items"),
        total_quantity=Coalesce(Sum("items__quantity"), 0, output_field=IntegerField()),
    )
    query = request.GET.get("q", "").strip()
    date_from_value = request.GET.get("date_from", "")
    date_to_value = request.GET.get("date_to", "")
    payment_method = request.GET.get("payment_method", "")
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "newest")

    if query:
        sales = sales.filter(sale_code__icontains=query)
    date_from = _parse_local_date(date_from_value)
    date_to = _parse_local_date(date_to_value)
    if date_from:
        sales = sales.filter(sold_at__gte=_local_day_start(date_from))
    if date_to:
        sales = sales.filter(sold_at__lt=_local_day_start(date_to + timedelta(days=1)))
    if payment_method in Sale.PaymentMethod.values:
        sales = sales.filter(payment_method=payment_method)
    if status in Sale.Status.values:
        sales = sales.filter(status=status)
    sales = (
        sales.order_by("sold_at", "id") if sort == "oldest" else sales.order_by("-sold_at", "-id")
    )

    page = Paginator(sales, 25).get_page(request.GET.get("page"))
    query_without_page = request.GET.copy()
    query_without_page.pop("page", None)
    return render(
        request,
        "sales/sale_list.html",
        {
            "page": page,
            "payment_methods": Sale.PaymentMethod.choices,
            "statuses": Sale.Status.choices,
            "filters": {
                "q": query,
                "date_from": date_from_value,
                "date_to": date_to_value,
                "payment_method": payment_method,
                "status": status,
                "sort": sort,
            },
            "query_without_page": query_without_page.urlencode(),
        },
    )


@login_required
def sale_create(request: HttpRequest) -> HttpResponse:
    form = SaleCreateForm(request.POST or None, initial={"lines_json": "[]"})
    cart_rows: list[dict[str, Any]] = []
    if request.method == "POST" and form.is_valid():
        lines = form.get_sale_lines()
        try:
            sale = complete_sale(
                lines=lines,
                discount_amount=form.cleaned_data["discount_amount"],
                payment_method=form.cleaned_data["payment_method"],
                note=form.cleaned_data["note"],
            )
        except (SaleValidationError, InsufficientStockError) as exc:
            form.add_error(None, str(exc))
            cart_rows = _cart_rows(request, lines)
        else:
            messages.success(request, f"Đã hoàn tất giao dịch {sale.sale_code}.")
            return redirect("sale-detail", sale_id=sale.pk)
    elif request.method == "POST":
        cart_rows = _cart_rows(request, form.get_sale_lines())

    return render(
        request,
        "sales/sale_create.html",
        {
            "form": form,
            "categories": Category.objects.filter(active=True).order_by("name"),
            "variants": _available_variants(request),
            "cart_rows": cart_rows,
        },
    )


@login_required
@require_GET
def sale_variant_search(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "sales/_variant_search_results.html",
        {"variants": _available_variants(request)},
    )


@login_required
def sale_detail(request: HttpRequest, sale_id: int) -> HttpResponse:
    sale = get_object_or_404(Sale.objects.prefetch_related("items"), pk=sale_id)
    return render(
        request,
        "sales/sale_detail.html",
        {"sale": sale, "cancellation_form": SaleCancellationForm()},
    )


@login_required
def sale_receipt(request: HttpRequest, sale_id: int) -> HttpResponse:
    sale = get_object_or_404(Sale.objects.prefetch_related("items"), pk=sale_id)
    return render(request, "sales/sale_receipt.html", {"sale": sale})


@login_required
@require_POST
def sale_cancel(request: HttpRequest, sale_id: int) -> HttpResponse:
    form = SaleCancellationForm(request.POST)
    if not form.is_valid():
        sale = get_object_or_404(Sale.objects.prefetch_related("items"), pk=sale_id)
        return render(
            request,
            "sales/sale_detail.html",
            {"sale": sale, "cancellation_form": form},
            status=400,
        )
    try:
        sale = cancel_sale(sale_id=sale_id, reason=form.cleaned_data["reason"])
    except SaleAlreadyCancelledError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Đã hủy {sale.sale_code} và hoàn lại tồn kho.")
    return redirect("sale-detail", sale_id=sale_id)
