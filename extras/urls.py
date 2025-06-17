from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AddressViewSet, UserVerificationViewSet
 
)

router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'verifications', UserVerificationViewSet, basename='verification')

urlpatterns = [
    path('', include(router.urls)),
]
