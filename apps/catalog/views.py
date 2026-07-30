from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.forms import (
    CategoryForm,
    InventoryAdjustmentForm,
    ProductForm,
    ProductVariantForm,
    ProductVariantFormSet,
)
from apps.catalog.models import Category, InventoryMovement, Product, ProductVariant
from apps.catalog.services import (
    InsufficientStockError,
    adjust_inventory,
    process_product_image,
)
from apps.core.security import cost_price_unlock_required, is_cost_price_unlocked


@login_required
def category_list(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    categories = Category.objects.annotate(product_count=Count("products")).order_by("name")
    if query:
        categories = categories.filter(name__icontains=query)
    return render(
        request,
        "catalog/category_list.html",
        {"categories": categories, "query": query},
    )


@login_required
def category_create(request: HttpRequest) -> HttpResponse:
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"Đã thêm loại mặt hàng “{category.name}”.")
        return redirect("category-list")
    return render(
        request,
        "catalog/category_form.html",
        {"form": form, "page_title": "Thêm loại mặt hàng"},
    )


@login_required
def category_update(request: HttpRequest, category_id: int) -> HttpResponse:
    category = get_object_or_404(Category, pk=category_id)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"Đã cập nhật “{category.name}”.")
        return redirect("category-list")
    return render(
        request,
        "catalog/category_form.html",
        {"form": form, "page_title": "Sửa loại mặt hàng", "category": category},
    )


@login_required
@require_POST
def category_toggle(request: HttpRequest, category_id: int) -> HttpResponse:
    category = get_object_or_404(Category, pk=category_id)
    category.active = not category.active
    category.save(update_fields=["active", "updated_at"])
    state = "hoạt động" if category.active else "ngừng hoạt động"
    messages.success(request, f"Đã chuyển “{category.name}” sang {state}.")
    return redirect("category-list")


def _product_rows(products: list[Product]) -> list[dict[str, Any]]:
    rows = []
    for product in products:
        variants = [variant for variant in product.variants.all() if variant.active]
        prices = [variant.selling_price for variant in variants]
        in_stock = [variant for variant in variants if variant.quantity > 0]
        low_stock = [
            variant for variant in in_stock if variant.quantity <= variant.low_stock_threshold
        ]
        healthy_stock = [variant for variant in in_stock if variant not in low_stock]
        out_of_stock = [variant for variant in variants if variant.quantity == 0]
        rows.append(
            {
                "product": product,
                "min_price": min(prices) if prices else None,
                "max_price": max(prices) if prices else None,
                "total_quantity": sum(variant.quantity for variant in variants),
                "in_stock": healthy_stock,
                "low_stock": low_stock,
                "out_of_stock": out_of_stock,
            }
        )
    return rows


@login_required
def product_list(request: HttpRequest) -> HttpResponse:
    products = Product.objects.select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.order_by("size"))
    )
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    size = request.GET.get("size", "").strip()
    color = request.GET.get("color", "").strip()
    stock = request.GET.get("stock", "")
    active = request.GET.get("active", "1")

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(brand__icontains=query) | Q(variants__sku__icontains=query)
        ).distinct()
    if category_id.isdigit():
        products = products.filter(category_id=int(category_id))
    if size:
        products = products.filter(variants__size__iexact=size).distinct()
    if color:
        products = products.filter(color__icontains=color)
    if active in {"0", "1"}:
        products = products.filter(active=active == "1")
    if stock == "available":
        products = products.filter(variants__active=True, variants__quantity__gt=0).distinct()
    elif stock == "low":
        products = products.filter(
            variants__active=True,
            variants__quantity__gt=0,
            variants__quantity__lte=F("variants__low_stock_threshold"),
        ).distinct()
    elif stock == "out":
        products = products.exclude(variants__active=True, variants__quantity__gt=0)

    context = {
        "rows": _product_rows(list(products)),
        "categories": Category.objects.order_by("name"),
        "sizes": ProductVariant.objects.values_list("size", flat=True).distinct().order_by("size"),
        "filters": {
            "q": query,
            "category": category_id,
            "size": size,
            "color": color,
            "stock": stock,
            "active": active,
        },
    }
    return render(request, "catalog/product_list.html", context)


@login_required
@cost_price_unlock_required
def product_create(request: HttpRequest) -> HttpResponse:
    product = Product()
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    formset = ProductVariantFormSet(
        request.POST or None,
        instance=product,
        prefix="variants",
    )
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        uploaded_image = form.cleaned_data.get("image")
        with transaction.atomic():
            product = form.save()
            for variant_form in formset.forms:
                if not variant_form.cleaned_data:
                    continue
                variant = variant_form.save(commit=False)
                initial_quantity = variant_form.cleaned_data["initial_quantity"]
                variant.product = product
                variant.quantity = 0
                variant.full_clean()
                variant.save()
                adjust_inventory(
                    variant_id=variant.pk,
                    operation="set",
                    quantity=initial_quantity,
                    reason="Tồn kho ban đầu",
                    movement_type=InventoryMovement.MovementType.INITIAL,
                )
        process_product_image(product, uploaded_image)
        messages.success(request, f"Đã tạo sản phẩm “{product.name}”.")
        return redirect("product-detail", product_id=product.pk)
    return render(
        request,
        "catalog/product_form.html",
        {"form": form, "formset": formset, "page_title": "Thêm sản phẩm"},
    )


@login_required
def product_detail(request: HttpRequest, product_id: int) -> HttpResponse:
    unlocked = is_cost_price_unlocked(request)
    variant_queryset = ProductVariant.objects.order_by("size")
    if not unlocked:
        variant_queryset = variant_queryset.defer("cost_price")
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related(
            Prefetch("variants", queryset=variant_queryset)
        ),
        pk=product_id,
    )
    variants = list(product.variants.all())
    movements = (
        InventoryMovement.objects.filter(product_variant__product=product)
        .select_related("product_variant")
        .order_by("-created_at")[:50]
    )
    return render(
        request,
        "catalog/product_detail.html",
        {
            "product": product,
            "variants": variants,
            "movements": movements,
            "total_quantity": sum(variant.quantity for variant in variants if variant.active),
        },
    )


@login_required
def product_update(request: HttpRequest, product_id: int) -> HttpResponse:
    product = get_object_or_404(Product, pk=product_id)
    previous_image_name = product.image.name
    previous_thumbnail_name = product.thumbnail.name
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        uploaded_image = form.cleaned_data.get("image") if request.FILES else None
        product = form.save()
        if uploaded_image and product.image.name != previous_image_name:
            process_product_image(product, uploaded_image)
            if previous_image_name:
                product.image.storage.delete(previous_image_name)
            if previous_thumbnail_name:
                product.thumbnail.storage.delete(previous_thumbnail_name)
        messages.success(request, f"Đã cập nhật “{product.name}”.")
        return redirect("product-detail", product_id=product.pk)
    return render(
        request,
        "catalog/product_edit.html",
        {"form": form, "product": product, "page_title": "Sửa sản phẩm"},
    )


@login_required
@require_POST
def product_toggle(request: HttpRequest, product_id: int) -> HttpResponse:
    product = get_object_or_404(Product, pk=product_id)
    product.active = not product.active
    product.save(update_fields=["active", "updated_at"])
    messages.success(request, "Đã cập nhật trạng thái sản phẩm.")
    return redirect("product-detail", product_id=product.pk)


@login_required
@cost_price_unlock_required
def variant_create(request: HttpRequest, product_id: int) -> HttpResponse:
    product = get_object_or_404(Product, pk=product_id)
    form = ProductVariantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            variant = form.save(commit=False)
            initial_quantity = form.cleaned_data["initial_quantity"]
            variant.product = product
            variant.quantity = 0
            variant.full_clean()
            variant.save()
            adjust_inventory(
                variant_id=variant.pk,
                operation="set",
                quantity=initial_quantity,
                reason="Tồn kho ban đầu",
                movement_type=InventoryMovement.MovementType.INITIAL,
            )
        messages.success(request, f"Đã thêm size {variant.size}.")
        return redirect("product-detail", product_id=product.pk)
    return render(
        request,
        "catalog/variant_form.html",
        {"form": form, "product": product, "page_title": "Thêm size"},
    )


@login_required
@cost_price_unlock_required
def variant_update(request: HttpRequest, variant_id: int) -> HttpResponse:
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)
    form = ProductVariantForm(request.POST or None, instance=variant)
    if request.method == "POST" and form.is_valid():
        variant = form.save()
        messages.success(request, f"Đã cập nhật size {variant.size}.")
        return redirect("product-detail", product_id=variant.product_id)
    return render(
        request,
        "catalog/variant_form.html",
        {"form": form, "product": variant.product, "variant": variant, "page_title": "Sửa size"},
    )


@login_required
def inventory_list(request: HttpRequest) -> HttpResponse:
    variants = ProductVariant.objects.select_related("product", "product__category").order_by(
        "product__name", "size"
    )
    if not is_cost_price_unlocked(request):
        variants = variants.defer("cost_price")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        variants = variants.filter(Q(product__name__icontains=query) | Q(sku__icontains=query))
    if status == "available":
        variants = variants.filter(quantity__gt=F("low_stock_threshold"))
    elif status == "low":
        variants = variants.filter(quantity__gt=0, quantity__lte=F("low_stock_threshold"))
    elif status == "out":
        variants = variants.filter(quantity=0)
    return render(
        request,
        "catalog/inventory_list.html",
        {"variants": variants, "query": query, "status": status},
    )


@login_required
def inventory_adjust(request: HttpRequest, variant_id: int) -> HttpResponse:
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)
    form = InventoryAdjustmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            adjust_inventory(
                variant_id=variant.pk,
                operation=form.cleaned_data["operation"],
                quantity=form.cleaned_data["quantity"],
                reason=form.cleaned_data["reason"],
            )
        except InsufficientStockError:
            form.add_error("quantity", "Không thể trừ quá số lượng đang tồn.")
        else:
            messages.success(
                request, f"Đã cập nhật tồn kho {variant.product.name} — {variant.size}."
            )
            return redirect("inventory-list")
    return render(
        request,
        "catalog/inventory_adjust.html",
        {"form": form, "variant": variant},
    )


def require_variant_owner_product(variant: ProductVariant, product_id: int) -> None:
    if variant.product_id != product_id:
        raise Http404
