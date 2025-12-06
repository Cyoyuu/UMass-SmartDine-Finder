from django.urls import path
from django.contrib.auth import views as auth_views
from menus.views import menu_view
from .views import RegisterView, home_view, logout_then_login


urlpatterns = [
    # Home page
    path('', home_view, name='home'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', logout_then_login, name='logout'),
    path('menus/', menu_view, name='menus'),
]
