from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'orderitems', views.OrderItemViewSet, basename='orderitem')
router.register(r'payments', views.PaymentViewSet, basename='payment')

app_name = 'order'

urlpatterns = [
    # Include all router URLs
    path('', include(router.urls)),
    
    # Additional custom endpoints (if needed)
    path('orders/<int:pk>/status/', views.OrderViewSet.as_view({'patch': 'updatestatus'}), name='order-update-status'),
    path('orders/<int:pk>/cancel/', views.OrderViewSet.as_view({'post': 'cancelorder'}), name='order-cancel'),
    path('orders/my-orders/', views.OrderViewSet.as_view({'get': 'myorders'}), name='my-orders'),
    path('orders/recent/', views.OrderViewSet.as_view({'get': 'recentorders'}), name='recent-orders'),
    path('orders/stats/', views.OrderViewSet.as_view({'get': 'orderstats'}), name='order-stats'),
    
    path('order-items/by-order/', views.OrderItemViewSet.as_view({'get': 'byorder'}), name='order-items-by-order'),
    
    path('payments/<int:pk>/process/', views.PaymentViewSet.as_view({'post': 'processpayment'}), name='payment-process'),
    path('payments/<int:pk>/refund/', views.PaymentViewSet.as_view({'post': 'refundpayment'}), name='payment-refund'),
    path('payments/stats/', views.PaymentViewSet.as_view({'get': 'paymentstats'}), name='payment-stats'),
]
