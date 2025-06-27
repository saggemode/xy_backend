from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Avg, Min, Max, Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from datetime import datetime
import random
import uuid
from decimal import Decimal, ROUND_HALF_UP
from store.models import Store
from product.models import Product, ProductVariant
from address.models import ShippingAddress


class Order(models.Model):
    """
    Professional Order model for multi-vendor e-commerce platform.
    
    Features:
    - Comprehensive status tracking
    - Payment integration
    - Shipping and tracking
    - Audit trail
    - Business logic validation
    - Soft delete functionality
    """
    
    class OrderStatus(models.TextChoices):
        """Order processing status."""
        PENDING = 'pending', _('Pending')
        CONFIRMED = 'confirmed', _('Confirmed')
        PROCESSING = 'processing', _('Processing')
        SHIPPED = 'shipped', _('Shipped')
        OUT_FOR_DELIVERY = 'out_for_delivery', _('Out for Delivery')
        DELIVERED = 'delivered', _('Delivered')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED = 'refunded', _('Refunded')
        RETURNED = 'returned', _('Returned')
        PARTIALLY_REFUNDED = 'partially_refunded', _('Partially Refunded')

    class PaymentStatus(models.TextChoices):
        """Payment processing status."""
        PENDING = 'pending', _('Pending')
        AUTHORIZED = 'authorized', _('Authorized')
        PAID = 'paid', _('Paid')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')
        PARTIALLY_REFUNDED = 'partially_refunded', _('Partially Refunded')
        CANCELLED = 'cancelled', _('Cancelled')

    class PaymentMethod(models.TextChoices):
        """Available payment methods."""
        CREDIT_CARD = 'credit_card', _('Credit Card')
        DEBIT_CARD = 'debit_card', _('Debit Card')
        PAYPAL = 'paypal', _('PayPal')
        BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
        CASH_ON_DELIVERY = 'cash_on_delivery', _('Cash on Delivery')
        DIGITAL_WALLET = 'digital_wallet', _('Digital Wallet')
        CRYPTOCURRENCY = 'cryptocurrency', _('Cryptocurrency')

    class ShippingMethod(models.TextChoices):
        """Available shipping methods."""
        STANDARD = 'standard', _('Standard Shipping')
        EXPRESS = 'express', _('Express Shipping')
        OVERNIGHT = 'overnight', _('Overnight Shipping')
        PICKUP = 'pickup', _('Store Pickup')
        INTERNATIONAL = 'international', _('International Shipping')

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID'),
        help_text=_('Unique identifier for the order')
    )

    # User and Store Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name=_('Customer'),
        help_text=_('The customer who placed this order'),
        db_index=True
    )
    
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name=_('Store'),
        help_text=_('The store where this order was placed'),
        db_index=True
    )

    # Order Information
    order_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_('Order Number'),
        help_text=_('Human-readable order identifier'),
        db_index=True
    )
    
    customer_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_('Customer ID'),
        help_text=_('External customer identifier')
    )

    # Status Fields
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name=_('Order Status'),
        help_text=_('Current status of the order'),
        db_index=True
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_('Payment Status'),
        help_text=_('Current payment status'),
        db_index=True
    )

    # Payment Information
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name=_('Payment Method'),
        help_text=_('Method used for payment')
    )
    
    payment_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Payment Reference'),
        help_text=_('External payment reference or transaction ID')
    )

    # Financial Information
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Subtotal'),
        help_text=_('Order subtotal before tax and shipping'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Tax Amount'),
        help_text=_('Total tax amount'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    shipping_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Shipping Cost'),
        help_text=_('Shipping and handling cost'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount Amount'),
        help_text=_('Total discount amount'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Total Amount'),
        help_text=_('Final order total'),
        validators=[MinValueValidator(Decimal('0.00'))],
        db_index=True
    )

    # Shipping Information
    shipping_address = models.ForeignKey(
        ShippingAddress,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name=_('Shipping Address'),
        help_text=_('Delivery address for this order')
    )
    
    billing_address = models.ForeignKey(
        ShippingAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_orders',
        verbose_name=_('Billing Address'),
        help_text=_('Billing address (if different from shipping)')
    )
    
    shipping_method = models.CharField(
        max_length=20,
        choices=ShippingMethod.choices,
        default=ShippingMethod.STANDARD,
        verbose_name=_('Shipping Method'),
        help_text=_('Selected shipping method')
    )
    
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Tracking Number'),
        help_text=_('Shipping carrier tracking number'),
        db_index=True
    )
    
    estimated_delivery = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Estimated Delivery'),
        help_text=_('Estimated delivery date')
    )

    # Order Details
    notes = models.TextField(
        blank=True,
        verbose_name=_('Order Notes'),
        help_text=_('Additional notes for this order')
    )
    
    special_instructions = models.TextField(
        blank=True,
        verbose_name=_('Special Instructions'),
        help_text=_('Special delivery or handling instructions')
    )

    # Metadata
    currency = models.CharField(
        max_length=3,
        default='USD',
        verbose_name=_('Currency'),
        help_text=_('Order currency code')
    )
    
    language = models.CharField(
        max_length=10,
        default='en',
        verbose_name=_('Language'),
        help_text=_('Order language code')
    )
    
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Extra Data'),
        help_text=_('Additional order metadata')
    )

    # Soft Delete
    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_('Is Deleted'),
        help_text=_('Whether this order has been soft deleted'),
        db_index=True
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Deleted At'),
        help_text=_('Timestamp when the order was soft deleted')
    )

    # Audit Fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
        help_text=_('Timestamp when the order was created'),
        db_index=True
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
        help_text=_('Timestamp when the order was last updated')
    )
    
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Confirmed At'),
        help_text=_('Timestamp when the order was confirmed')
    )
    
    shipped_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Shipped At'),
        help_text=_('Timestamp when the order was shipped')
    )
    
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Delivered At'),
        help_text=_('Timestamp when the order was delivered')
    )
    
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Cancelled At'),
        help_text=_('Timestamp when the order was cancelled')
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='created_orders',
        verbose_name=_('Created By'),
        help_text=_('User who created this order')
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='updated_orders',
        verbose_name=_('Updated By'),
        help_text=_('User who last updated this order')
    )

    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['store', 'status']),
            models.Index(fields=['payment_status', 'created_at']),
            models.Index(fields=['is_deleted', 'created_at']),
            models.Index(fields=['order_number']),
            models.Index(fields=['tracking_number']),
        ]
        permissions = [
            ("view_all_orders", "Can view all orders"),
            ("manage_orders", "Can manage orders"),
            ("cancel_orders", "Can cancel orders"),
            ("refund_orders", "Can refund orders"),
        ]

    def __str__(self):
        """String representation of the order."""
        return f"Order {self.order_number} - {self.user.email}"

    def clean(self):
        """Validate the order data."""
        super().clean()
        
        # Validate total amount
        calculated_total = self.calculate_total()
        if self.total_amount != calculated_total:
            raise ValidationError({
                'total_amount': f'Total amount should be {calculated_total}, not {self.total_amount}'
            })
        
        # Validate that billing address is provided if different from shipping
        if self.billing_address and self.billing_address == self.shipping_address:
            self.billing_address = None

    def save(self, *args, **kwargs):
        """Override save to ensure data consistency."""
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Auto-calculate totals if not set
        if not self.total_amount:
            self.total_amount = self.calculate_total()
        
        self.full_clean()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate a unique order number."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_num = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        return f"ORD-{timestamp}-{random_num}"

    def calculate_subtotal(self):
        """Calculate order subtotal from items."""
        return sum(item.total_price for item in self.order_items.all())

    def calculate_tax(self):
        """Calculate tax amount (10% rate)."""
        return self.subtotal * Decimal('0.10')

    def calculate_shipping(self):
        """Calculate shipping cost based on method."""
        shipping_costs = {
            self.ShippingMethod.STANDARD: Decimal('10.00'),
            self.ShippingMethod.EXPRESS: Decimal('25.00'),
            self.ShippingMethod.OVERNIGHT: Decimal('50.00'),
            self.ShippingMethod.PICKUP: Decimal('0.00'),
            self.ShippingMethod.INTERNATIONAL: Decimal('75.00'),
        }
        return shipping_costs.get(self.shipping_method, Decimal('10.00'))

    def calculate_total(self):
        """Calculate total order amount."""
        self.subtotal = self.calculate_subtotal()
        self.tax_amount = self.calculate_tax()
        self.shipping_cost = self.calculate_shipping()
        
        total = self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def update_totals(self):
        """Update all order totals."""
        self.total_amount = self.calculate_total()
        self.save(update_fields=['subtotal', 'tax_amount', 'shipping_cost', 'total_amount'])

    def confirm_order(self):
        """Confirm the order."""
        if self.status == self.OrderStatus.PENDING:
            self.status = self.OrderStatus.CONFIRMED
            self.confirmed_at = timezone.now()
            self.save(update_fields=['status', 'confirmed_at'])

    def ship_order(self):
        """Mark order as shipped."""
        if self.status in [self.OrderStatus.CONFIRMED, self.OrderStatus.PROCESSING]:
            self.status = self.OrderStatus.SHIPPED
            self.shipped_at = timezone.now()
            self.save(update_fields=['status', 'shipped_at'])

    def deliver_order(self):
        """Mark order as delivered."""
        if self.status == self.OrderStatus.SHIPPED:
            self.status = self.OrderStatus.DELIVERED
            self.delivered_at = timezone.now()
            self.save(update_fields=['status', 'delivered_at'])

    def cancel_order(self):
        """Cancel the order."""
        if self.status not in [self.OrderStatus.DELIVERED, self.OrderStatus.CANCELLED, self.OrderStatus.REFUNDED]:
            self.status = self.OrderStatus.CANCELLED
            self.cancelled_at = timezone.now()
            self.save(update_fields=['status', 'cancelled_at'])

    def refund_order(self):
        """Refund the order."""
        if self.status in [self.OrderStatus.DELIVERED, self.OrderStatus.SHIPPED]:
            self.status = self.OrderStatus.REFUNDED
            self.payment_status = self.PaymentStatus.REFUNDED
            self.save(update_fields=['status', 'payment_status'])

    def soft_delete(self):
        """Soft delete the order."""
        if not self.is_deleted:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """Restore a soft-deleted order."""
        if self.is_deleted:
            self.is_deleted = False
            self.deleted_at = None
            self.save(update_fields=['is_deleted', 'deleted_at'])

    @property
    def items(self):
        """Get order items."""
        return self.order_items.all()

    @property
    def item_count(self):
        """Get total number of items in order."""
        return sum(item.quantity for item in self.items)

    @property
    def can_cancel(self):
        """Check if order can be cancelled."""
        return self.status not in [
            self.OrderStatus.DELIVERED,
            self.OrderStatus.CANCELLED,
            self.OrderStatus.REFUNDED
        ]

    @property
    def can_refund(self):
        """Check if order can be refunded."""
        return self.status in [
            self.OrderStatus.DELIVERED,
            self.OrderStatus.SHIPPED
        ] and self.payment_status == self.PaymentStatus.PAID

    @property
    def is_paid(self):
        """Check if order is paid."""
        return self.payment_status == self.PaymentStatus.PAID

    @property
    def is_shipped(self):
        """Check if order is shipped."""
        return self.status in [
            self.OrderStatus.SHIPPED,
            self.OrderStatus.OUT_FOR_DELIVERY,
            self.OrderStatus.DELIVERED
        ]

    @property
    def is_delivered(self):
        """Check if order is delivered."""
        return self.status == self.OrderStatus.DELIVERED

    @property
    def is_cancelled(self):
        """Check if order is cancelled."""
        return self.status == self.OrderStatus.CANCELLED

    def get_absolute_url(self):
        """Get the absolute URL for this order."""
        from django.urls import reverse
        return reverse('order-detail', kwargs={'pk': self.pk})


class OrderItem(models.Model):
    """
    Order item model representing individual products in an order.
    
    Features:
    - Product and variant tracking
    - Price history preservation
    - Quantity validation
    - Total calculation
    """
    
    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID'),
        help_text=_('Unique identifier for the order item')
    )
    
    # Relationships
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name=_('Order'),
        help_text=_('The order this item belongs to'),
        db_index=True
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name=_('Product'),
        help_text=_('The product in this order item')
    )
    
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('Product Variant'),
        help_text=_('The specific variant of the product')
    )

    # Item Details
    quantity = models.PositiveIntegerField(
        verbose_name=_('Quantity'),
        help_text=_('Number of items ordered'),
        validators=[MinValueValidator(1)]
    )
    
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Unit Price'),
        help_text=_('Price per unit at time of order'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Total Price'),
        help_text=_('Total price for this item (quantity × unit price)'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        verbose_name=_('Item Notes'),
        help_text=_('Additional notes for this item')
    )
    
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Extra Data'),
        help_text=_('Additional item metadata')
    )

    # Audit Fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
        help_text=_('Timestamp when the order item was created')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
        help_text=_('Timestamp when the order item was last updated')
    )

    class Meta:
        verbose_name = _('Order Item')
        verbose_name_plural = _('Order Items')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order', 'product']),
            models.Index(fields=['product', 'created_at']),
        ]

    def __str__(self):
        """String representation of the order item."""
        variant_info = f" ({self.variant.name})" if self.variant else ""
        return f"{self.quantity}x {self.product.name}{variant_info} - Order {self.order.order_number}"

    def clean(self):
        """Validate the order item data."""
        super().clean()
        
        # Validate variant belongs to product
        if self.variant and self.variant.product != self.product:
            raise ValidationError({
                'variant': 'Variant does not belong to the selected product.'
            })
        
        # Validate total price calculation
        calculated_total = self.quantity * self.unit_price
        if self.total_price != calculated_total:
            raise ValidationError({
                'total_price': f'Total price should be {calculated_total}, not {self.total_price}'
            })

    def save(self, *args, **kwargs):
        """Override save to ensure data consistency."""
        # Auto-calculate total price if not set
        if not self.total_price:
            self.total_price = self.quantity * self.unit_price
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Update order totals
        self.order.update_totals()

    def get_absolute_url(self):
        """Get the absolute URL for this order item."""
        from django.urls import reverse
        return reverse('orderitem-detail', kwargs={'pk': self.pk})


class Payment(models.Model):
    """
    Payment model for tracking payment transactions.
    
    Features:
    - Transaction tracking
    - Payment method support
    - Status management
    - Audit trail
    """
    
    class PaymentStatus(models.TextChoices):
        """Payment processing status."""
        PENDING = 'pending', _('Pending')
        AUTHORIZED = 'authorized', _('Authorized')
        PAID = 'paid', _('Paid')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')
        PARTIALLY_REFUNDED = 'partially_refunded', _('Partially Refunded')
        CANCELLED = 'cancelled', _('Cancelled')

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID'),
        help_text=_('Unique identifier for the payment')
    )

    # Relationships
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name=_('Order'),
        help_text=_('The order this payment is for')
    )

    # Payment Information
    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Transaction ID'),
        help_text=_('External payment processor transaction ID'),
        db_index=True
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Amount'),
        help_text=_('Payment amount'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    currency = models.CharField(
        max_length=3,
        default='USD',
        verbose_name=_('Currency'),
        help_text=_('Payment currency code')
    )
    
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_('Status'),
        help_text=_('Current payment status'),
        db_index=True
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=Order.PaymentMethod.choices,
        verbose_name=_('Payment Method'),
        help_text=_('Method used for payment')
    )

    # Payment Details
    payment_details = models.JSONField(
        default=dict,
        verbose_name=_('Payment Details'),
        help_text=_('Additional payment information from processor')
    )
    
    gateway_response = models.JSONField(
        default=dict,
        verbose_name=_('Gateway Response'),
        help_text=_('Response from payment gateway')
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name=_('Error Message'),
        help_text=_('Error message if payment failed')
    )

    # Audit Fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
        help_text=_('Timestamp when the payment was created'),
        db_index=True
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
        help_text=_('Timestamp when the payment was last updated')
    )
    
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Processed At'),
        help_text=_('Timestamp when the payment was processed')
    )

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        """String representation of the payment."""
        return f"Payment {self.transaction_id} - {self.order.order_number}"

    def clean(self):
        """Validate the payment data."""
        super().clean()
        
        # Validate amount matches order total
        if self.amount != self.order.total_amount:
            raise ValidationError({
                'amount': f'Payment amount should match order total: {self.order.total_amount}'
            })

    def save(self, *args, **kwargs):
        """Override save to ensure data consistency."""
        self.full_clean()
        super().save(*args, **kwargs)

    def process_payment(self):
        """Process the payment."""
        if self.status == self.PaymentStatus.PENDING:
            # Simulate payment processing
            self.status = self.PaymentStatus.PAID
            self.processed_at = timezone.now()
            self.order.payment_status = Order.PaymentStatus.PAID
            self.order.save(update_fields=['payment_status'])
            self.save(update_fields=['status', 'processed_at'])

    def refund_payment(self, amount=None):
        """Refund the payment."""
        if self.status == self.PaymentStatus.PAID:
            refund_amount = amount or self.amount
            if refund_amount == self.amount:
                self.status = self.PaymentStatus.REFUNDED
                self.order.payment_status = Order.PaymentStatus.REFUNDED
                self.order.status = Order.OrderStatus.REFUNDED
            else:
                self.status = self.PaymentStatus.PARTIALLY_REFUNDED
                self.order.payment_status = Order.PaymentStatus.PARTIALLY_REFUNDED
            
            self.order.save(update_fields=['payment_status', 'status'])
            self.save(update_fields=['status'])

    def fail_payment(self, error_message=""):
        """Mark payment as failed."""
        self.status = self.PaymentStatus.FAILED
        self.error_message = error_message
        self.order.payment_status = Order.PaymentStatus.FAILED
        self.order.save(update_fields=['payment_status'])
        self.save(update_fields=['status', 'error_message'])

    @property
    def is_successful(self):
        """Check if payment was successful."""
        return self.status == self.PaymentStatus.PAID

    @property
    def is_failed(self):
        """Check if payment failed."""
        return self.status == self.PaymentStatus.FAILED

    @property
    def is_refunded(self):
        """Check if payment was refunded."""
        return self.status in [
            self.PaymentStatus.REFUNDED,
            self.PaymentStatus.PARTIALLY_REFUNDED
        ]

    def get_absolute_url(self):
        """Get the absolute URL for this payment."""
        from django.urls import reverse
        return reverse('payment-detail', kwargs={'pk': self.pk})