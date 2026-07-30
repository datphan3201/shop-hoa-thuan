from django.urls import path

from apps.catalog import views

urlpatterns = [
    path("", views.category_list, name="category-list"),
    path("new/", views.category_create, name="category-create"),
    path("<int:category_id>/edit/", views.category_update, name="category-update"),
    path("<int:category_id>/toggle/", views.category_toggle, name="category-toggle"),
]
