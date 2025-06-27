from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'order-items', views.OrderItemViewSet, basename='orderitem')
router.register(r'payments', views.PaymentViewSet, basename='payment')

# URL patterns for order app
urlpatterns = [
    # Include router URLs for standard CRUD operations
    path('', include(router.urls)),
    
    # Custom endpoints for specific functionality
    path('orders/my/', views.OrderViewSet.as_view({
        'get': 'my_orders'
    }), name='my-orders'),
    
    path('orders/recent/', views.OrderViewSet.as_view({
        'get': 'recent_orders'
    }), name='recent-orders'),
    
    path('orders/pending/', views.OrderViewSet.as_view({
        'get': 'pending_orders'
    }), name='pending-orders'),
    
    path('orders/stats/', views.OrderViewSet.as_view({
        'get': 'order_stats'
    }), name='order-stats'),
    
    # Bulk operations
    path('orders/bulk-update-status/', views.OrderViewSet.as_view({
        'post': 'bulk_update_status'
    }), name='bulk-update-order-status'),
    
    # Individual order actions
    path('orders/<uuid:pk>/confirm/', views.OrderViewSet.as_view({
        'patch': 'confirm_order'
    }), name='confirm-order'),
    
    path('orders/<uuid:pk>/ship/', views.OrderViewSet.as_view({
        'patch': 'ship_order'
    }), name='ship-order'),
    
    path('orders/<uuid:pk>/deliver/', views.OrderViewSet.as_view({
        'patch': 'deliver_order'
    }), name='deliver-order'),
    
    path('orders/<uuid:pk>/cancel/', views.OrderViewSet.as_view({
        'patch': 'cancel_order'
    }), name='cancel-order'),
    
    path('orders/<uuid:pk>/refund/', views.OrderViewSet.as_view({
        'patch': 'refund_order'
    }), name='refund-order'),
    
    path('orders/<uuid:pk>/soft-delete/', views.OrderViewSet.as_view({
        'delete': 'soft_delete'
    }), name='soft-delete-order'),
    
    path('orders/<uuid:pk>/restore/', views.OrderViewSet.as_view({
        'patch': 'restore'
    }), name='restore-order'),
    
    # Order items endpoints
    path('order-items/by-order/', views.OrderItemViewSet.as_view({
        'get': 'by_order'
    }), name='order-items-by-order'),
    
    # Payment endpoints
    path('payments/<uuid:pk>/process/', views.PaymentViewSet.as_view({
        'post': 'process_payment'
    }), name='process-payment'),
    
    path('payments/<uuid:pk>/refund/', views.PaymentViewSet.as_view({
        'post': 'refund_payment'
    }), name='refund-payment'),
    
    path('payments/stats/', views.PaymentViewSet.as_view({
        'get': 'payment_stats'
    }), name='payment-stats'),
]

# Add router URLs to the main patterns
urlpatterns += router.urls