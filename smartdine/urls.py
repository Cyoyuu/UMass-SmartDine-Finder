from django.contrib import admin
from django.urls import path, include
from menus.views import recommendations_view

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # accounts app - authentication (login, register, logout, home)
    path('', include('accounts.urls')),
    
    # Recommendations page (main landing page after login)
    path('recommendations/', recommendations_view, name='recommendations'),
    
    # menus app - dining halls, menus, reviews
    path('menus/', include('menus.urls')),
]
