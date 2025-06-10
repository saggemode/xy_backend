from rest_framework import serializers
from .models import Order, OrderItem, Payment
from product.models import Product, ProductVariant

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'product', 'product_name', 'variant', 'variant_name',
            'quantity', 'unit_price', 'total_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['total_price', 'created_at', 'updated_at']

    def validate(self, data):
        if data.get('variant') and data.get('product'):
            if data['variant'].product != data['product']:
                raise serializers.ValidationError("Variant does not belong to the selected product")
        return data

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'items', 'total_amount', 'status', 'status_display',
            'shipping_address', 'billing_address', 'payment_method',
            'tracking_number', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']

class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'order', 'order_number', 'transaction_id', 'amount',
                 'status', 'status_display', 'payment_method', 'payment_details',
                 'created_at', 'updated_at']
        read_only_fields = ['transaction_id']
