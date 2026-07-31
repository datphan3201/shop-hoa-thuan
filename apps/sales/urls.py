from django.urls import path

from apps.sales import views

urlpatterns = [
    path("", views.sale_list, name="sale-list"),
    path("new/", views.sale_create, name="sale-create"),
    path("new/search/", views.sale_variant_search, name="sale-variant-search"),
    path("<int:sale_id>/", views.sale_detail, name="sale-detail"),
    path("<int:sale_id>/receipt/", views.sale_receipt, name="sale-receipt"),
    path("<int:sale_id>/cancel/", views.sale_cancel, name="sale-cancel"),
]
