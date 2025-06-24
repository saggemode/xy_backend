from django.urls import path, include
from django.contrib import admin
from . import views
from rest_framework.routers import DefaultRouter

from .views import ShippingAddressViewSet

router = DefaultRouter()
router.register(r'shipping-addresses', ShippingAddressViewSet, basename='shipping-address')

urlpatterns = [
    path('', include(router.urls)),
]
