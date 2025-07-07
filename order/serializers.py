from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Order, OrderItem, Payment
from product.models import Product, ProductVariant
from store.models import Store
from address.models import ShippingAddress
from notification.models import Notification

User = get_user_model()


class SimpleUserSerializer(serializers.ModelSerializer):
    """Simplified user serializer for nested user data."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class SimpleStoreSerializer(serializers.ModelSerializer):
    """Simplified store serializer for nested store data."""
    
    class Meta:
        model = Store
        fields = ['id', 'name', 'slug', 'description']
        read_only_fields = ['id']


class SimpleProductSerializer(serializers.ModelSerializer):
    """Simplified product serializer for nested product data."""
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'base_price', 'current_price', 'on_sale', 
                 'discount_percentage', 'original_price', 'sku', 'status']
        read_only_fields = ['id']


class SimpleProductVariantSerializer(serializers.ModelSerializer):
    """Simplified product variant serializer for nested variant data."""
    
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'sku', 'base_price', 'current_price', 'pricing_mode',
                 'price_adjustment', 'individual_price', 'variant_type']
        read_only_fields = ['id']


class SimpleShippingAddressSerializer(serializers.ModelSerializer):
    """Simplified shipping address serializer for nested address data."""
    
    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'phone_number'
        ]
        read_only_fields = ['id']


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for OrderItem model.
    
    Features:
    - Full model field coverage
    - Nested product and variant data
    - Computed display fields
    - Validation for product-variant relationship
    - Auto-calculation of total price
    """
    
    # Computed fields for better UX
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    variant_sku = serializers.CharField(source='variant.sku', read_only=True)
    
    # Nested serializers for related objects
    product_details = SimpleProductSerializer(source='product', read_only=True)
    variant_details = SimpleProductVariantSerializer(source='variant', read_only=True)
    
    # URL fields
    absolute_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'product', 'product_name', 'product_slug', 'product_details',
            'variant', 'variant_name', 'variant_sku', 'variant_details',
            'quantity', 'unit_price', 'total_price', 'original_price', 'discount_amount',
            'discount_percentage', 'was_on_sale', 'notes', 'extra_data',
            'created_at', 'updated_at', 'absolute_url'
        ]
        read_only_fields = [
            'id', 'total_price', 'original_price', 'discount_amount', 'discount_percentage',
            'was_on_sale', 'created_at', 'updated_at', 'absolute_url'
        ]

    def get_absolute_url(self, obj):
        """Get the absolute URL for the order item."""
        return obj.get_absolute_url()

    def validate(self, data):
        """Custom validation for order item data."""
        # Validate variant belongs to product
        variant = data.get('variant')
        product = data.get('product')
        
        if variant and product and variant.product != product:
            raise serializers.ValidationError({
                'variant': 'Variant does not belong to the selected product.'
            })
        
        # Validate quantity
        quantity = data.get('quantity', 1)
        if quantity < 1:
            raise serializers.ValidationError({
                'quantity': 'Quantity must be at least 1.'
            })
        
        # Validate unit price
        unit_price = data.get('unit_price')
        if unit_price and unit_price <= 0:
            raise serializers.ValidationError({
                'unit_price': 'Unit price must be greater than 0.'
            })
        
        return data

    def create(self, validated_data):
        """Create order item with auto-calculation of total price."""
        # Auto-calculate total price
        quantity = validated_data.get('quantity', 1)
        unit_price = validated_data.get('unit_price')
        
        if unit_price:
            validated_data['total_price'] = quantity * unit_price
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update order item with auto-calculation of total price."""
        # Auto-calculate total price if quantity or unit_price changed
        quantity = validated_data.get('quantity', instance.quantity)
        unit_price = validated_data.get('unit_price', instance.unit_price)
        
        validated_data['total_price'] = quantity * unit_price
        
        return super().update(instance, validated_data)


class OrderItemListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for listing order items.
    
    Includes essential fields for list views with minimal data transfer.
    """
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    product_details = SimpleProductSerializer(source='product', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'product', 'product_name', 'product_details',
            'variant', 'variant_name', 'quantity', 'unit_price', 'total_price',
            'original_price', 'discount_amount', 'discount_percentage', 'was_on_sale',
            'created_at'
        ]
        read_only_fields = ['id', 'total_price', 'original_price', 'discount_amount', 
                           'discount_percentage', 'was_on_sale', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for Order model.
    
    Features:
    - Full model field coverage
    - Nested user, store, and address data
    - Computed display fields
    - Read-only audit fields
    - Proper validation
    - Business logic integration
    """
    
    # Computed fields for better UX
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    shipping_method_display = serializers.CharField(source='get_shipping_method_display', read_only=True)
    
    # Nested serializers for related objects
    user_details = SimpleUserSerializer(source='user', read_only=True)
    store_details = SimpleStoreSerializer(source='store', read_only=True)
    shipping_address_details = SimpleShippingAddressSerializer(source='shipping_address', read_only=True)
    billing_address_details = SimpleShippingAddressSerializer(source='billing_address', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    
    # Computed properties
    can_cancel = serializers.BooleanField(read_only=True)
    can_refund = serializers.BooleanField(read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    is_shipped = serializers.BooleanField(read_only=True)
    is_delivered = serializers.BooleanField(read_only=True)
    is_cancelled = serializers.BooleanField(read_only=True)
    
    # URL fields
    absolute_url = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            # Primary key
            'id',
            
            # User and store relationships
            'user', 'user_username', 'user_email', 'user_details',
            'store', 'store_name', 'store_details',
            
            # Order information
            'order_number', 'customer_id',
            
            # Status fields
            'status', 'status_display', 'payment_status', 'payment_status_display',
            
            # Payment information
            'payment_method', 'payment_method_display', 'payment_reference',
            
            # Financial information
            'subtotal', 'tax_amount', 'shipping_cost', 'discount_amount', 'total_amount',
            'currency',
            
            # Shipping information
            'shipping_address', 'shipping_address_details',
            'billing_address', 'billing_address_details',
            'shipping_method', 'shipping_method_display',
            'tracking_number', 'estimated_delivery',
            
            # Order details
            'notes', 'special_instructions', 'language',
            
            # Metadata
            'extra_data',
            
            # Audit fields
            'created_at', 'updated_at', 'confirmed_at', 'shipped_at',
            'delivered_at', 'cancelled_at',
            
            # Related objects
            'items',
            
            # Computed properties
            'can_cancel', 'can_refund', 'is_paid', 'is_shipped',
            'is_delivered', 'is_cancelled',
            
            # URL fields
            'absolute_url',
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at', 'confirmed_at',
            'shipped_at', 'delivered_at', 'cancelled_at',
            'can_cancel', 'can_refund', 'is_paid', 'is_shipped',
            'is_delivered', 'is_cancelled', 'absolute_url'
        ]

    def get_absolute_url(self, obj):
        """Get the absolute URL for the order."""
        return obj.get_absolute_url()

    def validate(self, data):
        """Custom validation for order data."""
        # Validate total amount calculation
        if 'subtotal' in data or 'tax_amount' in data or 'shipping_cost' in data or 'discount_amount' in data:
            subtotal = data.get('subtotal', getattr(self.instance, 'subtotal', 0))
            tax_amount = data.get('tax_amount', getattr(self.instance, 'tax_amount', 0))
            shipping_cost = data.get('shipping_cost', getattr(self.instance, 'shipping_cost', 0))
            discount_amount = data.get('discount_amount', getattr(self.instance, 'discount_amount', 0))
            
            calculated_total = subtotal + tax_amount + shipping_cost - discount_amount
            total_amount = data.get('total_amount', getattr(self.instance, 'total_amount', 0))
            
            if abs(calculated_total - total_amount) > 0.01:  # Allow for rounding differences
                raise serializers.ValidationError({
                    'total_amount': f'Total amount should be {calculated_total}, not {total_amount}'
                })
        
        # Validate billing address
        billing_address = data.get('billing_address')
        shipping_address = data.get('shipping_address')
        
        if billing_address and shipping_address and billing_address == shipping_address:
            data['billing_address'] = None
        
        return data


class OrderListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for listing orders.
    
    Includes essential fields for list views with minimal data transfer.
    """
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    # Nested data for list view
    user_details = SimpleUserSerializer(source='user', read_only=True)
    store_details = SimpleStoreSerializer(source='store', read_only=True)
    
    # Computed properties
    can_cancel = serializers.BooleanField(read_only=True)
    can_refund = serializers.BooleanField(read_only=True)
    is_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'user_username', 'user_details',
            'store', 'store_name', 'store_details', 'status', 'status_display',
            'payment_status', 'payment_status_display', 'total_amount',
            'tracking_number', 'created_at', 'can_cancel', 'can_refund', 'is_paid'
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'can_cancel', 'can_refund', 'is_paid'
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new orders with business logic.
    
    Features:
    - Auto-generate order number
    - Auto-calculate totals
    - Validate order items
    - Create notifications
    - Comprehensive validation
    """
    
    items = OrderItemSerializer(many=True, required=False)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    shipping_method = serializers.ChoiceField(choices=Order.ShippingMethod.choices)
    currency = serializers.CharField(max_length=3, default='USD')
    language = serializers.CharField(max_length=10, default='en')

    class Meta:
        model = Order
        fields = [
            'store', 'customer_id', 'payment_method', 'payment_reference',
            'shipping_address', 'billing_address', 'shipping_method',
            'notes', 'special_instructions', 'currency', 'language',
            'extra_data', 'items'
        ]

    def validate(self, data):
        """Custom validation for order creation."""
        # Validate that items are provided
        items = data.get('items', [])
        if not items:
            raise serializers.ValidationError({
                'items': 'At least one item is required to create an order.'
            })
        
        # Validate items have required fields
        for item in items:
            if not item.get('product'):
                raise serializers.ValidationError({
                    'items': 'Product is required for each item.'
                })
            if not item.get('quantity') or item['quantity'] < 1:
                raise serializers.ValidationError({
                    'items': 'Quantity must be at least 1 for each item.'
                })
        
        return data

    def create(self, validated_data):
        """Create order with items and business logic."""
        items_data = validated_data.pop('items', [])
        
        with transaction.atomic():
            # Create order
            order = Order.objects.create(**validated_data)
            
            # Create order items
            for item_data in items_data:
                OrderItem.objects.create(order=order, **item_data)
            
            # Update order totals
            order.update_totals()
            
            # Create notification
            self.create_order_notification(order)
            
            return order

    def create_order_notification(self, order):
        """Create notification for new order."""
        try:
            product_list = ", ".join([item.product.name for item in order.items.all()])
            address_details = order.shipping_address.full_address if order.shipping_address else "No address specified"
            
            message_content = (
                f"Your order {order.order_number} has been successfully placed.\n"
                f"Total: ${order.total_amount}\n"
                f"Products: {product_list}\n"
                f"Shipping to: {address_details}"
            )

            Notification.objects.create(
                recipient=order.user,
                title=f"Order Confirmed: {order.order_number}",
                message=message_content,
                notification_type=Notification.NotificationType.NEW_ORDER,
                level=Notification.NotificationLevel.SUCCESS,
                orderId=order,
                link=f'/orders/{order.id}/'
            )
        except Exception as e:
            # Log error but don't fail order creation
            print(f"Error creating notification: {e}")


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order fields."""
    
    class Meta:
        model = Order
        fields = [
            'status', 'payment_status', 'payment_reference', 'tracking_number',
            'estimated_delivery', 'notes', 'special_instructions', 'extra_data'
        ]
        
    def validate(self, data):
        """Validate update data."""
        # Validate status transitions
        if 'status' in data:
            current_status = self.instance.status
            new_status = data['status']
            
            # Define valid status transitions
            valid_transitions = {
                Order.OrderStatus.PENDING: [Order.OrderStatus.CONFIRMED, Order.OrderStatus.CANCELLED],
                Order.OrderStatus.CONFIRMED: [Order.OrderStatus.PROCESSING, Order.OrderStatus.CANCELLED],
                Order.OrderStatus.PROCESSING: [Order.OrderStatus.SHIPPED, Order.OrderStatus.CANCELLED],
                Order.OrderStatus.SHIPPED: [Order.OrderStatus.OUT_FOR_DELIVERY, Order.OrderStatus.DELIVERED],
                Order.OrderStatus.OUT_FOR_DELIVERY: [Order.OrderStatus.DELIVERED],
            }
            
            if current_status in valid_transitions and new_status not in valid_transitions[current_status]:
                raise serializers.ValidationError({
                    'status': f'Cannot transition from {current_status} to {new_status}'
                })
        
        return data


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status."""
    
    class Meta:
        model = Order
        fields = ['status']
        
    def validate_status(self, value):
        """Validate status change."""
        current_status = self.instance.status
        
        # Define valid status transitions
        valid_transitions = {
            Order.OrderStatus.PENDING: [Order.OrderStatus.CONFIRMED, Order.OrderStatus.CANCELLED],
            Order.OrderStatus.CONFIRMED: [Order.OrderStatus.PROCESSING, Order.OrderStatus.CANCELLED],
            Order.OrderStatus.PROCESSING: [Order.OrderStatus.SHIPPED, Order.OrderStatus.CANCELLED],
            Order.OrderStatus.SHIPPED: [Order.OrderStatus.OUT_FOR_DELIVERY, Order.OrderStatus.DELIVERED],
            Order.OrderStatus.OUT_FOR_DELIVERY: [Order.OrderStatus.DELIVERED],
        }
        
        if current_status in valid_transitions and value not in valid_transitions[current_status]:
            raise serializers.ValidationError(
                f'Cannot transition from {current_status} to {value}'
            )
        
        return value


class OrderBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating orders."""
    
    order_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of order IDs to update"
    )
    status = serializers.ChoiceField(
        choices=Order.OrderStatus.choices,
        help_text="Set all orders to this status"
    )

    def validate_order_ids(self, value):
        """Validate that all order IDs exist and belong to the user."""
        request = self.context.get('request')
        if request and request.user:
            user_orders = Order.objects.filter(
                id__in=value,
                user=request.user
            )
            if len(user_orders) != len(value):
                raise serializers.ValidationError(
                    "Some order IDs are invalid or don't belong to you."
                )
        return value


class PaymentSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for Payment model.
    
    Features:
    - Full model field coverage
    - Nested order data
    - Computed display fields
    - Validation and business logic
    """
    
    # Computed fields for better UX
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    # Nested serializers for related objects
    order_details = OrderSerializer(source='order', read_only=True)
    
    # Computed properties
    is_successful = serializers.BooleanField(read_only=True)
    is_failed = serializers.BooleanField(read_only=True)
    is_refunded = serializers.BooleanField(read_only=True)
    
    # URL fields
    absolute_url = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'order_details',
            'transaction_id', 'amount', 'currency', 'status', 'status_display',
            'payment_method', 'payment_method_display', 'payment_details',
            'gateway_response', 'error_message', 'created_at', 'updated_at',
            'processed_at', 'is_successful', 'is_failed', 'is_refunded',
            'absolute_url'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'created_at', 'updated_at', 'processed_at',
            'is_successful', 'is_failed', 'is_refunded', 'absolute_url'
        ]

    def get_absolute_url(self, obj):
        """Get the absolute URL for the payment."""
        return obj.get_absolute_url()

    def validate(self, data):
        """Custom validation for payment data."""
        # Validate amount matches order total
        order = data.get('order')
        amount = data.get('amount')
        
        if order and amount and amount != order.total_amount:
            raise serializers.ValidationError({
                'amount': f'Payment amount should match order total: {order.total_amount}'
            })
        
        return data


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new payments."""
    
    class Meta:
        model = Payment
        fields = [
            'order', 'amount', 'currency', 'payment_method',
            'payment_details', 'gateway_response'
        ]

    def validate(self, data):
        """Custom validation for payment creation."""
        order = data.get('order')
        amount = data.get('amount')
        
        if order and amount and amount != order.total_amount:
            raise serializers.ValidationError({
                'amount': f'Payment amount should match order total: {order.total_amount}'
            })
        
        return data

    def create(self, validated_data):
        """Create payment with auto-generated transaction ID."""
        # Generate transaction ID if not provided
        if not validated_data.get('transaction_id'):
            validated_data['transaction_id'] = f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{validated_data['order'].id.hex[:8].upper()}"
        
        return super().create(validated_data)


class OrderStatsSerializer(serializers.Serializer):
    """Serializer for order statistics."""
    
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    processing_orders = serializers.IntegerField()
    shipped_orders = serializers.IntegerField()
    delivered_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    refunded_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    original_total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_savings = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders_with_discounts = serializers.IntegerField()
    average_discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    orders_by_status = serializers.DictField()
    orders_by_month = serializers.DictField()
    recent_orders = serializers.ListField(child=serializers.DictField())


class PaymentStatsSerializer(serializers.Serializer):
    """Serializer for payment statistics."""
    
    total_payments = serializers.IntegerField()
    completed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    refunded_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_payment_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payments_by_status = serializers.DictField()
    payments_by_method = serializers.DictField()
    recent_payments = serializers.ListField(child=serializers.DictField())
