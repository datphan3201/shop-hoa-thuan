from django.urls import path

from apps.reports import views

urlpatterns = [
    path("", views.report_overview, name="report-overview"),
    path("export.csv", views.export_sales_csv, name="report-export-csv"),
    path(
        "export-sensitive.csv",
        views.export_sales_sensitive_csv,
        name="report-export-sensitive-csv",
    ),
]
