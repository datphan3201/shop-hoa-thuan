from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import groupby
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, QuerySet, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone

from apps.sales.models import Sale, SaleItem

SHOP_TIMEZONE = ZoneInfo(settings.TIME_ZONE)


@dataclass(frozen=True)
class ReportPeriod:
    start: datetime
    end: datetime
    label: str
    key: str

    @property
    def date_from(self) -> date:
        return self.start.astimezone(SHOP_TIMEZONE).date()

    @property
    def date_to(self) -> date:
        return (self.end.astimezone(SHOP_TIMEZONE) - timedelta(microseconds=1)).date()


@dataclass(frozen=True)
class ReportSummary:
    revenue: int
    completed_sale_count: int
    sold_quantity: int
    average_order_value: int | None
    total_discount: int
    cost_of_goods_sold: int | None = None
    gross_profit: int | None = None
    gross_margin: float | None = None


@dataclass(frozen=True)
class BreakdownRow:
    label: str
    revenue: int
    quantity: int


@dataclass(frozen=True)
class ReportData:
    period: ReportPeriod
    summary: ReportSummary
    category_revenue: list[BreakdownRow]
    product_revenue: list[BreakdownRow]
    size_revenue: list[BreakdownRow]
    payment_revenue: list[BreakdownRow]
    best_products: list[BreakdownRow]
    best_variants: list[BreakdownRow]


@dataclass(frozen=True)
class AllocatedItem:
    item: SaleItem
    actual_revenue: int
    allocated_discount: int


def _local_midnight(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=SHOP_TIMEZONE)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _safe_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def resolve_report_period(
    params: Mapping[str, str],
    *,
    now: datetime | None = None,
) -> ReportPeriod:
    local_now = timezone.localtime(now or timezone.now(), SHOP_TIMEZONE)
    today = local_now.date()
    key = params.get("period", "this_month")

    if key == "today":
        start_date, end_date, label = today, today + timedelta(days=1), "Hôm nay"
    elif key == "yesterday":
        start_date = today - timedelta(days=1)
        end_date, label = today, "Hôm qua"
    elif key == "last_7_days":
        start_date, end_date, label = (
            today - timedelta(days=6),
            today + timedelta(days=1),
            ("7 ngày gần nhất"),
        )
    elif key == "last_30_days":
        start_date, end_date, label = (
            today - timedelta(days=29),
            today + timedelta(days=1),
            ("30 ngày gần nhất"),
        )
    elif key == "last_month":
        current_month = date(today.year, today.month, 1)
        end_date = current_month
        if current_month.month == 1:
            start_date = date(current_month.year - 1, 12, 1)
        else:
            start_date = date(current_month.year, current_month.month - 1, 1)
        label = "Tháng trước"
    elif key == "this_year":
        start_date = date(today.year, 1, 1)
        end_date, label = date(today.year + 1, 1, 1), "Năm nay"
    elif key == "custom":
        custom_from = _safe_date(params.get("date_from", ""))
        custom_to = _safe_date(params.get("date_to", ""))
        if custom_from and custom_to and custom_from <= custom_to:
            start_date = custom_from
            end_date = custom_to + timedelta(days=1)
            label = f"{custom_from:%d/%m/%Y} đến {custom_to:%d/%m/%Y}"
        else:
            key = "this_month"
            start_date = date(today.year, today.month, 1)
            end_date = _next_month(start_date)
            label = "Tháng này"
    else:
        key = "this_month"
        start_date = date(today.year, today.month, 1)
        end_date = _next_month(start_date)
        label = "Tháng này"

    return ReportPeriod(
        start=_local_midnight(start_date),
        end=_local_midnight(end_date),
        label=label,
        key=key,
    )


def completed_sales(period: ReportPeriod) -> QuerySet[Sale]:
    return Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        sold_at__gte=period.start,
        sold_at__lt=period.end,
    )


def sale_items_for_period(
    period: ReportPeriod,
    *,
    include_cost: bool,
) -> QuerySet[SaleItem]:
    items = (
        SaleItem.objects.filter(
            sale__status=Sale.Status.COMPLETED,
            sale__sold_at__gte=period.start,
            sale__sold_at__lt=period.end,
        )
        .select_related("sale")
        .order_by("sale_id", "id")
    )
    if not include_cost:
        items = items.defer("unit_cost_snapshot")
    return items


def _allocate_group(items: list[SaleItem]) -> list[AllocatedItem]:
    if not items:
        return []
    sale = items[0].sale
    if sale.subtotal <= 0 or sale.final_total <= 0:
        return [
            AllocatedItem(
                item=item,
                actual_revenue=0,
                allocated_discount=item.line_total,
            )
            for item in items
        ]

    base_revenues = [item.line_total * sale.final_total // sale.subtotal for item in items]
    remaining = sale.final_total - sum(base_revenues)
    remainder_order = sorted(
        range(len(items)),
        key=lambda index: (
            (items[index].line_total * sale.final_total) % sale.subtotal,
            -items[index].id,
        ),
        reverse=True,
    )
    for index in remainder_order[:remaining]:
        base_revenues[index] += 1
    return [
        AllocatedItem(
            item=item,
            actual_revenue=revenue,
            allocated_discount=item.line_total - revenue,
        )
        for item, revenue in zip(items, base_revenues, strict=True)
    ]


def iter_allocated_items(items: Iterable[SaleItem]) -> Iterator[AllocatedItem]:
    for _, sale_group in groupby(items, key=lambda item: item.sale_id):
        yield from _allocate_group(list(sale_group))


def _breakdown_rows(values: Mapping[str, tuple[int, int]]) -> list[BreakdownRow]:
    rows = [
        BreakdownRow(label=label or "Không xác định", revenue=revenue, quantity=quantity)
        for label, (revenue, quantity) in values.items()
    ]
    return sorted(rows, key=lambda row: (-row.revenue, -row.quantity, row.label.casefold()))


def build_report(period: ReportPeriod, *, include_cost: bool) -> ReportData:
    sales = completed_sales(period)
    sales_totals = sales.aggregate(
        revenue=Sum("final_total"),
        total_discount=Sum("discount_amount"),
        completed_sale_count=Count("id"),
    )
    revenue = int(sales_totals["revenue"] or 0)
    completed_sale_count = int(sales_totals["completed_sale_count"] or 0)
    total_discount = int(sales_totals["total_discount"] or 0)

    category_values: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    product_values: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    size_values: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    payment_values: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    variant_values: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    sold_quantity = 0
    cost_of_goods_sold = 0

    for allocated in iter_allocated_items(
        sale_items_for_period(period, include_cost=include_cost).iterator(chunk_size=500)
    ):
        item = allocated.item
        quantity = item.quantity
        sold_quantity += quantity
        keys = (
            (category_values, item.category_name_snapshot),
            (product_values, item.product_name_snapshot),
            (size_values, item.size_snapshot),
            (payment_values, item.sale.get_payment_method_display()),
            (
                variant_values,
                f"{item.product_name_snapshot} — {item.size_snapshot}"
                + (f" — {item.color_snapshot}" if item.color_snapshot else ""),
            ),
        )
        for target, key in keys:
            target[key][0] += allocated.actual_revenue
            target[key][1] += quantity
        if include_cost:
            cost_of_goods_sold += quantity * item.unit_cost_snapshot

    def freeze(values: Mapping[str, list[int]]) -> dict[str, tuple[int, int]]:
        return {key: (value[0], value[1]) for key, value in values.items()}

    product_rows = _breakdown_rows(freeze(product_values))
    variant_rows = _breakdown_rows(freeze(variant_values))
    summary = ReportSummary(
        revenue=revenue,
        completed_sale_count=completed_sale_count,
        sold_quantity=sold_quantity,
        average_order_value=(revenue // completed_sale_count if completed_sale_count else None),
        total_discount=total_discount,
        cost_of_goods_sold=cost_of_goods_sold if include_cost else None,
        gross_profit=(revenue - cost_of_goods_sold if include_cost else None),
        gross_margin=(
            (revenue - cost_of_goods_sold) / revenue * 100 if include_cost and revenue else None
        ),
    )
    return ReportData(
        period=period,
        summary=summary,
        category_revenue=_breakdown_rows(freeze(category_values)),
        product_revenue=product_rows,
        size_revenue=_breakdown_rows(freeze(size_values)),
        payment_revenue=_breakdown_rows(freeze(payment_values)),
        best_products=sorted(
            product_rows,
            key=lambda row: (-row.quantity, -row.revenue, row.label.casefold()),
        )[:10],
        best_variants=sorted(
            variant_rows,
            key=lambda row: (-row.quantity, -row.revenue, row.label.casefold()),
        )[:10],
    )


def daily_sales_series(period: ReportPeriod) -> list[dict[str, int | str]]:
    revenue_values = {
        row["day"].date(): int(row["revenue"] or 0)
        for row in completed_sales(period)
        .annotate(day=TruncDay("sold_at", tzinfo=SHOP_TIMEZONE))
        .values("day")
        .annotate(revenue=Sum("final_total"))
        .order_by("day")
    }
    quantity_values = {
        row["day"].date(): int(row["quantity"] or 0)
        for row in SaleItem.objects.filter(
            sale__status=Sale.Status.COMPLETED,
            sale__sold_at__gte=period.start,
            sale__sold_at__lt=period.end,
        )
        .annotate(day=TruncDay("sale__sold_at", tzinfo=SHOP_TIMEZONE))
        .values("day")
        .annotate(quantity=Sum("quantity"))
        .order_by("day")
    }
    result: list[dict[str, int | str]] = []
    current = period.date_from
    while current <= period.date_to:
        result.append(
            {
                "label": current.strftime("%d/%m"),
                "revenue": revenue_values.get(current, 0),
                "quantity": quantity_values.get(current, 0),
            }
        )
        current += timedelta(days=1)
    return result


def monthly_sales_series(year: int) -> list[dict[str, int | str]]:
    period = ReportPeriod(
        start=_local_midnight(date(year, 1, 1)),
        end=_local_midnight(date(year + 1, 1, 1)),
        label=str(year),
        key="year",
    )
    values = {
        row["month"].month: int(row["revenue"] or 0)
        for row in completed_sales(period)
        .annotate(month=TruncMonth("sold_at", tzinfo=SHOP_TIMEZONE))
        .values("month")
        .annotate(revenue=Sum("final_total"))
        .order_by("month")
    }
    return [{"label": f"Tháng {month}", "revenue": values.get(month, 0)} for month in range(1, 13)]
