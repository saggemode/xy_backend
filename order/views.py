from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import uuid

from .models import Order, OrderItem, Payment
from .serializers import (
    OrderSerializer, 
    OrderItemSerializer, 
    PaymentSerializer,
    OrderStatusUpdateSerializer
)


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order model with full CRUD operations.
    Supports filtering by status, date range, and user.
    """
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'payment_method', 'user', 'store']
    search_fields = ['order_number', 'tracking_number']
    ordering_fields = ['created_at', 'updated_at', 'total', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Regular users can only see their own orders.
        Staff users can see all orders.
        """
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        """Set the user to the current user when creating an order."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['patch'])
    def updatestatus(self, request, pk=None):
        """Update order status."""
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancelorder(self, request, pk=None):
        """Cancel an order."""
        order = self.get_object()
        
        if order.status in ['delivered', 'cancelled', 'refunded']:
            return Response(
                {'error': 'Cannot cancel order with current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        return Response({'message': 'Order cancelled successfully'})

    @action(detail=False, methods=['get'])
    def myorders(self, request):
        """Get current user's orders."""
        orders = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recentorders(self, request):
        """Get recent orders (last 30 days)."""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        orders = self.get_queryset().filter(created_at__gte=thirty_days_ago)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def orderstats(self, request):
        """Get order statistics."""
        queryset = self.get_queryset()
        
        stats = {
            'total_orders': queryset.count(),
            'pending_orders': queryset.filter(status='pending').count(),
            'processing_orders': queryset.filter(status='processing').count(),
            'shipped_orders': queryset.filter(status='shipped').count(),
            'delivered_orders': queryset.filter(status='delivered').count(),
            'cancelled_orders': queryset.filter(status='cancelled').count(),
            'total_revenue': sum(order.total for order in queryset if order.status != 'cancelled'),
        }
        
        return Response(stats)


class OrderItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for OrderItem model with full CRUD operations.
    """
    queryset = OrderItem.objects.all().order_by('-created_at')
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['order', 'product', 'variant']
    search_fields = ['product__name', 'variant__name']

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Regular users can only see items from their own orders.
        Staff users can see all order items.
        """
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(order__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        """Calculate total price when creating order item."""
        order_item = serializer.save()
        order_item.total_price = order_item.quantity * order_item.unit_price
        order_item.save()
        
        # Recalculate order totals
        order_item.order.calculate_totals()

    def perform_update(self, serializer):
        """Recalculate totals when updating order item."""
        order_item = serializer.save()
        order_item.total_price = order_item.quantity * order_item.unit_price
        order_item.save()
        
        # Recalculate order totals
        order_item.order.calculate_totals()

    @action(detail=False, methods=['get'])
    def byorder(self, request):
        """Get order items for a specific order."""
        order_id = request.query_params.get('order_id')
        if not order_id:
            return Response(
                {'error': 'order_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        items = self.get_queryset().filter(order_id=order_id)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Payment model with full CRUD operations.
    """
    queryset = Payment.objects.all().order_by('-created_at')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['order', 'status', 'payment_method']
    search_fields = ['transaction_id', 'order__order_number']

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Regular users can only see payments for their own orders.
        Staff users can see all payments.
        """
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(order__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        """Generate transaction ID when creating payment."""
        if not serializer.validated_data.get('transaction_id'):
            serializer.save(transaction_id=f"TXN-{uuid.uuid4().hex[:16].upper()}")

    @action(detail=True, methods=['post'])
    def processpayment(self, request, pk=None):
        """Process a payment."""
        payment = self.get_object()
        
        # Simulate payment processing
        if payment.status == 'pending':
            payment.status = 'completed'
            payment.order.payment_status = 'paid'
            payment.order.save()
            payment.save()
            
            return Response({'message': 'Payment processed successfully'})
        
        return Response(
            {'error': 'Payment cannot be processed with current status'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def refundpayment(self, request, pk=None):
        """Refund a payment."""
        payment = self.get_object()
        
        if payment.status == 'completed':
            payment.status = 'refunded'
            payment.order.payment_status = 'refunded'
            payment.order.status = 'refunded'
            payment.order.save()
            payment.save()
            
            return Response({'message': 'Payment refunded successfully'})
        
        return Response(
            {'error': 'Payment cannot be refunded with current status'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def paymentstats(self, request):
        """Get payment statistics."""
        queryset = self.get_queryset()
        
        stats = {
            'total_payments': queryset.count(),
            'completed_payments': queryset.filter(status='completed').count(),
            'pending_payments': queryset.filter(status='pending').count(),
            'failed_payments': queryset.filter(status='failed').count(),
            'refunded_payments': queryset.filter(status='refunded').count(),
            'total_amount': sum(payment.amount for payment in queryset.filter(status='completed')),
        }
        
        return Response(stats)
