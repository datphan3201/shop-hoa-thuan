from __future__ import annotations

import csv
import io
import time
from datetime import UTC, datetime

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.catalog.models import Category, Product, ProductVariant
from apps.core.security import UNLOCKED_UNTIL_KEY
from apps.reports.services import (
    ReportPeriod,
    build_report,
    daily_sales_series,
    resolve_report_period,
)
from apps.sales.models import Sale
from apps.sales.services import SaleLineInput, cancel_sale, complete_sale


@pytest.fixture
def report_owner_client(db: None, client: Client) -> Client:
    return client


@pytest.fixture
def report_variants(db: None) -> tuple[ProductVariant, ProductVariant]:
    category = Category.objects.create(name="Áo thun")
    first_product = Product.objects.create(
        category=category,
        name="Áo Basic",
        color="Trắng",
    )
    second_product = Product.objects.create(
        category=category,
        name="Áo Premium",
        color="Đen",
    )
    first = ProductVariant.objects.create(
        product=first_product,
        size="M",
        sku="BASIC-M",
        cost_price=100_000,
        selling_price=200_000,
        quantity=20,
    )
    second = ProductVariant.objects.create(
        product=second_product,
        size="L",
        sku="PREMIUM-L",
        cost_price=80_000,
        selling_price=150_000,
        quantity=20,
    )
    return first, second


def _fixed_month_period() -> ReportPeriod:
    return resolve_report_period(
        {"period": "this_month"},
        now=datetime(2026, 7, 15, 4, 0, tzinfo=UTC),
    )


@pytest.mark.django_db
def test_report_uses_final_total_and_allocates_discount_exactly(
    report_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    first, second = report_variants
    sale = complete_sale(
        lines=[
            SaleLineInput(first.pk, 2, 180_000),
            SaleLineInput(second.pk, 1, 140_000),
        ],
        discount_amount=50_000,
        payment_method=Sale.PaymentMethod.CASH,
        sold_at=datetime(2026, 7, 10, 3, 0, tzinfo=UTC),
    )

    report = build_report(_fixed_month_period(), include_cost=True)

    assert sale.subtotal == 500_000
    assert sale.final_total == 450_000
    assert report.summary.revenue == 450_000
    assert report.summary.completed_sale_count == 1
    assert report.summary.sold_quantity == 3
    assert report.summary.average_order_value == 450_000
    assert report.summary.total_discount == 50_000
    assert report.summary.cost_of_goods_sold == 280_000
    assert report.summary.gross_profit == 170_000
    assert report.summary.gross_margin == pytest.approx(37.7777777)
    assert [(row.label, row.revenue) for row in report.product_revenue] == [
        ("Áo Basic", 324_000),
        ("Áo Premium", 126_000),
    ]
    assert report.category_revenue[0].revenue == 450_000


@pytest.mark.django_db
def test_cancelled_sales_are_excluded_from_reports(
    report_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    first, second = report_variants
    completed = complete_sale(
        lines=[SaleLineInput(first.pk, 1, 180_000)],
        discount_amount=0,
        payment_method=Sale.PaymentMethod.CASH,
        sold_at=datetime(2026, 7, 10, 3, 0, tzinfo=UTC),
    )
    cancelled = complete_sale(
        lines=[SaleLineInput(second.pk, 2, 140_000)],
        discount_amount=0,
        payment_method=Sale.PaymentMethod.BANK_TRANSFER,
        sold_at=datetime(2026, 7, 11, 3, 0, tzinfo=UTC),
    )
    cancel_sale(sale_id=cancelled.pk, reason="Khách trả lại")

    report = build_report(_fixed_month_period(), include_cost=False)

    assert report.summary.revenue == completed.final_total
    assert report.summary.completed_sale_count == 1
    assert report.summary.sold_quantity == 1
    assert all(row.label != "Chuyển khoản" for row in report.payment_revenue)


@pytest.mark.django_db
def test_empty_report_does_not_divide_by_zero() -> None:
    report = build_report(_fixed_month_period(), include_cost=True)

    assert report.summary.revenue == 0
    assert report.summary.average_order_value is None
    assert report.summary.cost_of_goods_sold == 0
    assert report.summary.gross_profit == 0
    assert report.summary.gross_margin is None


@pytest.mark.django_db
def test_report_day_boundary_uses_ho_chi_minh_timezone(
    report_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    first, _ = report_variants
    local_july_31 = complete_sale(
        lines=[SaleLineInput(first.pk, 1, 180_000)],
        discount_amount=0,
        payment_method=Sale.PaymentMethod.CASH,
        sold_at=datetime(2026, 7, 30, 17, 30, tzinfo=UTC),
    )
    complete_sale(
        lines=[SaleLineInput(first.pk, 1, 180_000)],
        discount_amount=0,
        payment_method=Sale.PaymentMethod.CASH,
        sold_at=datetime(2026, 7, 31, 17, 30, tzinfo=UTC),
    )
    period = resolve_report_period(
        {"period": "today"},
        now=datetime(2026, 7, 31, 5, 0, tzinfo=UTC),
    )

    report = build_report(period, include_cost=False)

    assert report.summary.revenue == local_july_31.final_total
    assert report.summary.completed_sale_count == 1


@pytest.mark.django_db
def test_daily_series_does_not_duplicate_sale_revenue_for_multiple_items(
    report_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    first, second = report_variants
    sale = complete_sale(
        lines=[
            SaleLineInput(first.pk, 1, 180_000),
            SaleLineInput(second.pk, 1, 140_000),
        ],
        discount_amount=20_000,
        payment_method=Sale.PaymentMethod.CASH,
        sold_at=datetime(2026, 7, 10, 3, 0, tzinfo=UTC),
    )

    series = daily_sales_series(_fixed_month_period())
    july_10 = next(row for row in series if row["label"] == "10/07")

    assert july_10["revenue"] == sale.final_total
    assert july_10["quantity"] == 2


@pytest.mark.django_db
def test_locked_report_does_not_query_or_render_cost(
    report_owner_client: Client,
    report_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    first, _ = report_variants
    complete_sale(
        lines=[SaleLineInput(first.pk, 1, 180_000)],
        discount_amount=0,
        payment_method=Sale.PaymentMethod.CASH,
    )

    with CaptureQueriesContext(connection) as queries:
        response = report_owner_client.get(reverse("report-overview"), {"period": "this_year"})
    content = response.content.decode()

    assert response.status_code == 200
    assert "Giá vốn hàng đã bán" not in content
    assert "100.000 ₫" not in content
    assert not any("unit_cost_snapshot" in query["sql"] for query in queries.captured_queries)


@pytest.mark.django_db
def test_unlocked_report_renders_cost_and_actual_profit(
    report_owner_client: Client,
    report_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    first, _ = report_variants
    complete_sale(
        lines=[SaleLineInput(first.pk, 1, 180_000)],
        discount_amount=10_000,
        payment_method=Sale.PaymentMethod.CASH,
    )
    session = report_owner_client.session
    session[UNLOCKED_UNTIL_KEY] = time.time() + 600
    session.save()

    response = report_owner_client.get(reverse("report-overview"), {"period": "this_year"})
    content = response.content.decode()

    assert "Giá vốn hàng đã bán" in content
    assert "100.000 ₫" in content
    assert "70.000 ₫" in content


@pytest.mark.django_db
def test_default_csv_has_no_cost_and_sensitive_csv_requires_unlock(
    report_owner_client: Client,
    report_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    first, _ = report_variants
    complete_sale(
        lines=[SaleLineInput(first.pk, 1, 180_000)],
        discount_amount=10_000,
        payment_method=Sale.PaymentMethod.CASH,
    )

    default_response = report_owner_client.get(
        reverse("report-export-csv"),
        {"period": "this_year"},
    )
    default_content = default_response.content.decode("utf-8-sig")
    locked_sensitive_response = report_owner_client.get(
        reverse("report-export-sensitive-csv"),
        {"period": "this_year"},
    )

    assert default_response.status_code == 200
    assert "Giá vốn" not in default_content
    assert "Lợi nhuận" not in default_content
    assert "100000" not in default_content
    assert locked_sensitive_response.status_code == 302
    assert locked_sensitive_response.headers["Location"] == reverse("security-settings")

    session = report_owner_client.session
    session[UNLOCKED_UNTIL_KEY] = time.time() + 600
    session.save()
    sensitive_response = report_owner_client.get(
        reverse("report-export-sensitive-csv"),
        {"period": "this_year"},
    )
    sensitive_content = sensitive_response.content.decode("utf-8-sig")

    assert sensitive_response.status_code == 200
    assert "Giá vốn đơn vị" in sensitive_content
    assert "100000" in sensitive_content
    assert "70000" in sensitive_content


@pytest.mark.django_db
def test_csv_allocated_revenue_sums_to_sale_final_total(
    report_owner_client: Client,
    report_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    first, second = report_variants
    sale = complete_sale(
        lines=[
            SaleLineInput(first.pk, 1, 101),
            SaleLineInput(second.pk, 1, 100),
        ],
        discount_amount=1,
        payment_method=Sale.PaymentMethod.CASH,
    )

    response = report_owner_client.get(reverse("report-export-csv"), {"period": "this_year"})
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))

    assert sum(int(row["Doanh thu thực tế"]) for row in rows) == sale.final_total
    assert sum(int(row["Giảm giá phân bổ"]) for row in rows) == sale.discount_amount


@pytest.mark.django_db
def test_dashboard_inventory_totals_include_inactive_product_stock(
    report_owner_client: Client,
    report_variants: tuple[ProductVariant, ProductVariant],
) -> None:
    first, second = report_variants
    first.product.active = False
    first.product.save(update_fields=["active", "updated_at"])

    response = report_owner_client.get(reverse("dashboard"))
    content = response.content.decode()

    assert response.status_code == 200
    assert str(first.quantity + second.quantity) in content
