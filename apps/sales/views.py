from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def sale_list(request: HttpRequest) -> HttpResponse:
    return render(request, "shared/phase_placeholder.html", {"page_title": "Lịch sử bán hàng"})


@login_required
def sale_create(request: HttpRequest) -> HttpResponse:
    return render(request, "shared/phase_placeholder.html", {"page_title": "Tạo giao dịch"})


@login_required
def sale_detail(request: HttpRequest, sale_id: int) -> HttpResponse:
    return render(
        request,
        "shared/phase_placeholder.html",
        {"page_title": f"Chi tiết giao dịch #{sale_id}"},
    )
