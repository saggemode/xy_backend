from django.urls import path, include
from django.contrib import admin
from . import views
from rest_framework.routers import DefaultRouter

from .views import (  
ShippingAddressViewSet, 
SimpleShippingAddressViewSet,
Test1ViewSet,
Test2ViewSet,
Test3ViewSet,
Test4ViewSet,
Test5ViewSet,
Test6ViewSet,
Test7ViewSet,
Test8ViewSet
)

router = DefaultRouter()

router.register(r'shipping-addresses', ShippingAddressViewSet, basename='shipping-address')
router.register(r'simple-shipping-addresses', SimpleShippingAddressViewSet, basename='simple-shipping-address')
router.register(r'test1-shipping-addresses', Test1ViewSet, basename='test1-shipping-address')
router.register(r'test2-shipping-addresses', Test2ViewSet, basename='test2-shipping-address')
router.register(r'test3-shipping-addresses', Test3ViewSet, basename='test3-shipping-address')
router.register(r'test4-shipping-addresses', Test4ViewSet, basename='test4-shipping-address')
router.register(r'test5-shipping-addresses', Test5ViewSet, basename='test5-shipping-address')
router.register(r'test6-shipping-addresses', Test6ViewSet, basename='test6-shipping-address')
router.register(r'test7-shipping-addresses', Test7ViewSet, basename='test7-shipping-address')
router.register(r'test8-shipping-addresses', Test8ViewSet, basename='test8-shipping-address')

urlpatterns = [
    path('', include(router.urls)),
]
