from django.urls import path
from django.contrib.auth import views as auth_views
from .views import RegisterView, menu_view, home_view, logout_then_login, api_menus_view, RecommendView, UserPreferenceView

from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', home_view, name='home'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html',
            redirect_authenticated_user=True
        ),
        name='login'
    ),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', logout_then_login, name='logout'),
    path('menu/', menu_view, name='menu'),
    path('api/menus/', api_menus_view, name='api_menus'),
    path("recommend/", RecommendView.as_view(), name="recommend"),
    path("preferences/", UserPreferenceView.as_view(), name="preferences"),
]
