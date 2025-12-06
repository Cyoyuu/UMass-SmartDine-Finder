from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # accounts app - authentication (login, register, logout, home)
    path('', include('accounts.urls')),
    
    # menus app - dining halls, menus, reviews
    path('menus/', include('menus.urls')),
]
