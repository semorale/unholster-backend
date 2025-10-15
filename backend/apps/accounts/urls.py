"""
URL configuration for accounts app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    RegisterView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current-user'),

    # User management (router)
    path('', include(router.urls)),
]
