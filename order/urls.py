from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrderListCreateView.as_view(), name='order-list-create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<int:pk>/items/', views.OrderItemListCreateView.as_view(), name='order-item-list-create'),
    path('items/<int:pk>/', views.OrderItemDetailView.as_view(), name='order-item-detail'),
    path('<int:pk>/status/', views.OrderStatusUpdateView.as_view(), name='order-status-update'),
    path('<int:order_pk>/payment/', views.PaymentViewSet.as_view({'post': 'create', 'get': 'list'}), name='order-payment'),
    path('payment/<int:pk>/', views.PaymentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='payment-detail'),
]
