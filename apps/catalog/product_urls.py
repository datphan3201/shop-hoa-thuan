from django.urls import path

from apps.catalog import views

urlpatterns = [
    path("", views.product_list, name="product-list"),
    path("new/", views.product_create, name="product-create"),
    path("<int:product_id>/", views.product_detail, name="product-detail"),
]
