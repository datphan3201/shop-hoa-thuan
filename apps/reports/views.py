from __future__ import annotations

import csv

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.core.security import cost_price_unlock_required, is_cost_price_unlocked
from apps.reports.services import (
    build_report,
    daily_sales_series,
    iter_allocated_items,
    resolve_report_period,
    sale_items_for_period,
)


def _period_params(request: HttpRequest) -> dict[str, str]:
    return {
        "period": request.GET.get("period", "this_month"),
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
    }


def report_overview(request: HttpRequest) -> HttpResponse:
    period = resolve_report_period(_period_params(request))
    include_cost = is_cost_price_unlocked(request)
    report = build_report(period, include_cost=include_cost)
    return render(
        request,
        "reports/overview.html",
        {
            "report": report,
            "period": period,
            "daily_series": daily_sales_series(period),
            "filters": _period_params(request),
        },
    )


def _csv_response(request: HttpRequest, *, include_cost: bool) -> HttpResponse:
    period = resolve_report_period(_period_params(request))
    filename = f"giao-dich-{period.date_from:%Y%m%d}-{period.date_to:%Y%m%d}" + (
        "-co-gia-von.csv" if include_cost else ".csv"
    )
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    headers = [
        "Mã giao dịch",
        "Ngày giờ",
        "Tên sản phẩm",
        "Loại mặt hàng",
        "Size",
        "Màu sắc",
        "SKU",
        "Số lượng",
        "Giá bán niêm yết",
        "Giá bán thực tế",
        "Giảm giá phân bổ",
        "Doanh thu thực tế",
        "Phương thức thanh toán",
        "Trạng thái",
    ]
    if include_cost:
        headers.extend(["Giá vốn đơn vị", "Giá vốn hàng bán", "Lợi nhuận gộp"])
    writer.writerow(headers)

    items = sale_items_for_period(period, include_cost=include_cost).iterator(chunk_size=500)
    for allocated in iter_allocated_items(items):
        item = allocated.item
        sold_at = timezone.localtime(item.sale.sold_at)
        row: list[str | int] = [
            item.sale.sale_code,
            sold_at.strftime("%d/%m/%Y %H:%M"),
            item.product_name_snapshot,
            item.category_name_snapshot,
            item.size_snapshot,
            item.color_snapshot,
            item.sku_snapshot,
            item.quantity,
            item.listed_price,
            item.actual_unit_price,
            allocated.allocated_discount,
            allocated.actual_revenue,
            item.sale.get_payment_method_display(),
            item.sale.get_status_display(),
        ]
        if include_cost:
            cost_total = item.quantity * item.unit_cost_snapshot
            row.extend(
                [
                    item.unit_cost_snapshot,
                    cost_total,
                    allocated.actual_revenue - cost_total,
                ]
            )
        writer.writerow(row)
    return response


@require_GET
def export_sales_csv(request: HttpRequest) -> HttpResponse:
    return _csv_response(request, include_cost=False)


@cost_price_unlock_required
@require_GET
def export_sales_sensitive_csv(request: HttpRequest) -> HttpResponse:
    return _csv_response(request, include_cost=True)
