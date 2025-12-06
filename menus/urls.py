# menus/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Page views
    path('', views.menu_view, name='menu'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    
    # Review API endpoints (AJAX only)
    path('review/<int:hall_id>/', views.submit_review, name='submit_review'),
    path('review/<int:hall_id>/delete/', views.delete_review, name='delete_review'),
    
    # Meal History API endpoints
    path('history/', views.get_meal_history, name='meal_history'),
    path('history/save/', views.save_meal_history, name='save_meal_history'),
    path('history/<str:date_str>/', views.get_meal_history_detail, name='meal_history_detail'),
]
