from django.urls import path

from apps.reports import views

urlpatterns = [
    path("", views.report_overview, name="report-overview"),
]
