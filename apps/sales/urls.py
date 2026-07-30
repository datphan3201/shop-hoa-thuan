from django.urls import path

from apps.sales import views

urlpatterns = [
    path("", views.sale_list, name="sale-list"),
    path("new/", views.sale_create, name="sale-create"),
    path("<int:sale_id>/", views.sale_detail, name="sale-detail"),
]
