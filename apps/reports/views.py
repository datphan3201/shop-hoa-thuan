from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
def report_overview(request: HttpRequest) -> HttpResponse:
    return render(request, "shared/phase_placeholder.html", {"page_title": "Báo cáo"})
