# menus/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("api/menus/", views.menus_view, name="menus_view"),
    path("dining/<int:hall_id>/", views.dining_hall_detail, name="dining_hall_detail"),
    path("dining/<int:hall_id>/review/", views.writeReview, name="write_review"),
]
