from django.urls import path, include
from django.contrib import admin
from . import views
from rest_framework.routers import DefaultRouter
from .views import (StoreViewSet, StoreStaffViewSet, StoreAnalyticsViewSet, ProductByStoreViewSet)

router = DefaultRouter()
router.register(r'stores', StoreViewSet)
router.register(r'store-staffs', StoreStaffViewSet)
router.register(r'store-analytics', StoreAnalyticsViewSet)
router.register(r'products-by-store', ProductByStoreViewSet, basename='products-by-store')

urlpatterns = [
    path('', include(router.urls)),
    path('stores/<int:pk>/staff/', views.StoreStaffViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('stores/<int:pk>/staff/<int:staff_id>/', views.StoreStaffViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
]