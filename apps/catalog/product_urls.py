from django.urls import path

from apps.catalog import views

urlpatterns = [
    path("", views.product_list, name="product-list"),
    path("new/", views.product_create, name="product-create"),
    path("<int:product_id>/", views.product_detail, name="product-detail"),
    path("<int:product_id>/edit/", views.product_update, name="product-update"),
    path("<int:product_id>/toggle/", views.product_toggle, name="product-toggle"),
    path("<int:product_id>/variants/new/", views.variant_create, name="variant-create"),
    path("variants/<int:variant_id>/edit/", views.variant_update, name="variant-update"),
]
