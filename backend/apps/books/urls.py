"""
URL configuration for books app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookViewSet

router = DefaultRouter()
router.register(r'', BookViewSet, basename='book')

urlpatterns = [
    path('', include(router.urls)),
]
