from django.urls import path

from apps.catalog import views

urlpatterns = [
    path("", views.category_list, name="category-list"),
]
