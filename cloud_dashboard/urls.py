from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('dashboard.urls')),   # 👈 connect app
    path('admin/', admin.site.urls),
]