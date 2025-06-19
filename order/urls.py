from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'order-items', views.OrderItemViewSet, basename='orderitem')
router.register(r'payments', views.PaymentViewSet, basename='payment')

app_name = 'order'

urlpatterns = [
    # Include all router URLs
    path('', include(router.urls)),
    
    # Additional custom endpoints (if needed)
    path('api/orders/<int:pk>/status/', views.OrderViewSet.as_view({'patch': 'update_status'}), name='order-update-status'),
    path('api/orders/<int:pk>/cancel/', views.OrderViewSet.as_view({'post': 'cancel_order'}), name='order-cancel'),
    path('api/orders/my-orders/', views.OrderViewSet.as_view({'get': 'my_orders'}), name='my-orders'),
    path('api/orders/recent/', views.OrderViewSet.as_view({'get': 'recent_orders'}), name='recent-orders'),
    path('api/orders/stats/', views.OrderViewSet.as_view({'get': 'order_stats'}), name='order-stats'),
    
    path('api/order-items/by-order/', views.OrderItemViewSet.as_view({'get': 'by_order'}), name='order-items-by-order'),
    
    path('api/payments/<int:pk>/process/', views.PaymentViewSet.as_view({'post': 'process_payment'}), name='payment-process'),
    path('api/payments/<int:pk>/refund/', views.PaymentViewSet.as_view({'post': 'refund_payment'}), name='payment-refund'),
    path('api/payments/stats/', views.PaymentViewSet.as_view({'get': 'payment_stats'}), name='payment-stats'),
]
