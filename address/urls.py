from django.urls import path, include
from django.contrib import admin
from . import views
from rest_framework.routers import DefaultRouter

from .views import (  
ShippingAddressViewSet, SimpleShippingAddressViewSet
)

router = DefaultRouter()

router.register(r'shipping-addresses', ShippingAddressViewSet, basename='shipping-address')
router.register(r'simple-shipping-addresses', SimpleShippingAddressViewSet, basename='simple-shipping-address')

urlpatterns = [
    path('', include(router.urls)),
]
