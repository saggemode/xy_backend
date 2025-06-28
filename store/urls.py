from django.urls import path, include
from django.contrib import admin
from . import views
from rest_framework.routers import DefaultRouter
from .views import (
    StoreViewSet, StoreStaffViewSet, StoreAnalyticsViewSet, ProductByStoreViewSet, DebugStoreView, SimpleStoreViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'store-staff', StoreStaffViewSet, basename='store-staff')
router.register(r'store-analytics', StoreAnalyticsViewSet, basename='store-analytics')
router.register(r'products-by-store', ProductByStoreViewSet, basename='products-by-store')

# URL patterns for store app
urlpatterns = [
    # Debug endpoint
    path('debug/store/', DebugStoreView.as_view(), name='debug-store'),
    
    # Simple test endpoint
    path('test/stores/', views.SimpleStoreViewSet.as_view({'get': 'list'}), name='test-stores'),
    
    # Main stores endpoint test
    path('stores-test/', views.StoreViewSet.as_view({'get': 'list'}), name='stores-test'),
    
    # Direct stores endpoint (bypassing router)
    # path('stores/', views.StoreViewSet.as_view({'get': 'list', 'post': 'create'}), name='stores-list'),
    path('stores/<uuid:pk>/', views.StoreViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='stores-detail'),
    
    # Include router URLs for standard CRUD operations
    path('', include(router.urls)),
    
    # Custom endpoints for specific functionality
    path('stores/my/', views.StoreViewSet.as_view({
        'get': 'my_stores'
    }), name='my-stores'),
    
    path('stores/active/', views.StoreViewSet.as_view({
        'get': 'active_stores'
    }), name='active-stores'),
    
    path('stores/verified/', views.StoreViewSet.as_view({
        'get': 'verified_stores'
    }), name='verified-stores'),
    
    path('stores/statistics/', views.StoreViewSet.as_view({
        'get': 'store_statistics'
    }), name='store-statistics'),
    
    # Bulk operations
    path('stores/bulk-actions/', views.StoreViewSet.as_view({
        'post': 'bulk_actions'
    }), name='bulk-store-actions'),
    
    # Individual store actions
    path('stores/<uuid:pk>/activate/', views.StoreViewSet.as_view({
        'patch': 'activate'
    }), name='activate-store'),
    
    path('stores/<uuid:pk>/deactivate/', views.StoreViewSet.as_view({
        'patch': 'deactivate'
    }), name='deactivate-store'),
    
    path('stores/<uuid:pk>/verify/', views.StoreViewSet.as_view({
        'patch': 'verify'
    }), name='verify-store'),
    
    path('stores/<uuid:pk>/close/', views.StoreViewSet.as_view({
        'patch': 'close'
    }), name='close-store'),
    
    path('stores/<uuid:pk>/analytics/', views.StoreViewSet.as_view({
        'get': 'analytics'
    }), name='store-analytics'),
    
    path('stores/<uuid:pk>/inventory/', views.StoreViewSet.as_view({
        'get': 'inventory'
    }), name='store-inventory'),
    
    # Store staff endpoints
    path('store-staff/by-store/', views.StoreStaffViewSet.as_view({
        'get': 'by_store'
    }), name='staff-by-store'),
    
    path('store-staff/by-role/', views.StoreStaffViewSet.as_view({
        'get': 'by_role'
    }), name='staff-by-role'),
    
    path('store-staff/bulk-actions/', views.StoreStaffViewSet.as_view({
        'post': 'bulk_actions'
    }), name='bulk-staff-actions'),
    
    # Store analytics endpoints
    path('store-analytics/<uuid:pk>/recalculate/', views.StoreAnalyticsViewSet.as_view({
        'post': 'recalculate'
    }), name='recalculate-analytics'),
    
    path('store-analytics/report/', views.StoreAnalyticsViewSet.as_view({
        'get': 'report'
    }), name='analytics-report'),
    
    # Legacy endpoints for backward compatibility
    path('stores/<int:pk>/staff/', views.StoreStaffViewSet.as_view({
        'get': 'list', 'post': 'create'
    }), name='store-staff-legacy'),
    
    path('stores/<int:pk>/staff/<int:staff_id>/', views.StoreStaffViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'delete': 'destroy'
    }), name='store-staff-detail-legacy'),
]

# Add router URLs to the main patterns
urlpatterns += router.urls