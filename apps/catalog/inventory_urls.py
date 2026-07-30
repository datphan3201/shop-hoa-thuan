from django.urls import path

from apps.catalog import views

urlpatterns = [
    path("", views.inventory_list, name="inventory-list"),
    path("<int:variant_id>/adjust/", views.inventory_adjust, name="inventory-adjust"),
]
