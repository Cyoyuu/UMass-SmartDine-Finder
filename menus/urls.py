# menus/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Page views
    path('', views.menu_view, name='menu'),
    
    # API endpoints
    path('api/menus/', views.api_menus_view, name='api_menus'),
    path('api/review/<int:hall_id>/', views.submit_review, name='submit_review'),
]
