from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def category_list(request: HttpRequest) -> HttpResponse:
    return render(request, "shared/phase_placeholder.html", {"page_title": "Loại mặt hàng"})


@login_required
def product_list(request: HttpRequest) -> HttpResponse:
    return render(request, "shared/phase_placeholder.html", {"page_title": "Sản phẩm"})


@login_required
def product_create(request: HttpRequest) -> HttpResponse:
    return render(request, "shared/phase_placeholder.html", {"page_title": "Thêm sản phẩm"})


@login_required
def product_detail(request: HttpRequest, product_id: int) -> HttpResponse:
    return render(
        request,
        "shared/phase_placeholder.html",
        {"page_title": f"Chi tiết sản phẩm #{product_id}"},
    )


@login_required
def inventory_list(request: HttpRequest) -> HttpResponse:
    return render(request, "shared/phase_placeholder.html", {"page_title": "Tồn kho"})
