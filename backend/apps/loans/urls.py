"""
URL configuration for loans app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LoanTransferViewSet, LoanViewSet, ReservationViewSet

router = DefaultRouter()
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'transfers', LoanTransferViewSet, basename='transfer')

urlpatterns = [
    path('', include(router.urls)),
]
