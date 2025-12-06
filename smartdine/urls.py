from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),  # register/login/logout/menu
]

# UMASS-SMARTDINE-FINDER/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Include the menus app URLs
    path("", include("menus.urls")),
]
