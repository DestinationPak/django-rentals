"""rentals URL Configuration (throwaway dev project - not part of the published package)"""
from django.conf.urls import include
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('django_rentals.urls')),
]
