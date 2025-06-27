from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db.models import Sum, Count
from django.utils.translation import gettext_lazy as _
from .models import Order, OrderItem, Payment


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Professional admin interface for Order model.
    
    Features:
    - Comprehensive list display with all important fields
    - Advanced filtering and search capabilities
    - Organized fieldsets for better UX
    - Custom actions for order management
    - Read-only fields for audit data
    - Performance optimization
    """
    
    # List display configuration
    list_display = [
        'order_number', 'user', 'store', 'status', 'payment_status',
        'total_amount', 'item_count', 'created_at', 'is_deleted'
    ]
    
    # List display links
    list_display_links = ['order_number']
    
    # List filters for easy filtering
    list_filter = [
        'status', 'payment_status', 'payment_method', 'shipping_method',
        'is_deleted', 'created_at', 'confirmed_at', 'shipped_at', 'delivered_at'
    ]
    
    # Search fields
    search_fields = [
        'order_number', 'tracking_number', 'payment_reference',
        'user__username', 'user__email', 'store__name',
        'shipping_address__address_line1', 'shipping_address__city'
    ]
    
    # Read-only fields
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'confirmed_at', 'shipped_at',
        'delivered_at', 'cancelled_at', 'deleted_at', 'item_count',
        'absolute_url', 'can_cancel', 'can_refund', 'is_paid', 'is_shipped',
        'is_delivered', 'is_cancelled'
    ]
    
    # Ordering
    ordering = ['-created_at']
    
    # Items per page
    list_per_page = 50
    
    # Date hierarchy
    date_hierarchy = 'created_at'
    
    # Fieldsets for organized form display
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'user', 'store', 'order_number', 'customer_id'
            )
        }),
        ('Status Information', {
            'fields': (
                'status', 'payment_status', 'payment_method', 'payment_reference'
            )
        }),
        ('Financial Information', {
            'fields': (
                'subtotal', 'tax_amount', 'shipping_cost', 'discount_amount', 'total_amount',
                'currency'
            )
        }),
        ('Shipping Information', {
            'fields': (
                'shipping_address', 'billing_address', 'shipping_method',
                'tracking_number', 'estimated_delivery'
            )
        }),
        ('Order Details', {
            'fields': (
                'notes', 'special_instructions', 'language'
            )
        }),
        ('Metadata', {
            'fields': ['extra_data'],
            'classes': ('collapse',)
        }),
        ('Soft Delete', {
            'fields': (
                'is_deleted', 'deleted_at'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': (
                'created_at', 'updated_at', 'confirmed_at', 'shipped_at',
                'delivered_at', 'cancelled_at', 'absolute_url'
            ),
            'classes': ('collapse',)
        }),
        ('Computed Properties', {
            'fields': (
                'item_count', 'can_cancel', 'can_refund', 'is_paid',
                'is_shipped', 'is_delivered', 'is_cancelled'
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Custom actions
    actions = [
        'confirm_orders', 'ship_orders', 'deliver_orders', 'cancel_orders',
        'refund_orders', 'soft_delete_orders', 'restore_orders',
        'generate_tracking_numbers'
    ]
    
    # Raw ID fields for better performance with large datasets
    raw_id_fields = ['user', 'store', 'shipping_address', 'billing_address']
    
    # Autocomplete fields - removed due to CustomUser model not being registered
    # autocomplete_fields = ['user', 'store']
    
    def absolute_url(self, obj):
        """Display absolute URL as a clickable link."""
        if obj.pk:
            url = obj.get_absolute_url()
            return format_html('<a href="{}" target="_blank">View</a>', url)
        return '-'
    absolute_url.short_description = 'URL'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance."""
        return super().get_queryset(request).select_related(
            'user', 'store', 'shipping_address', 'billing_address'
        ).prefetch_related('order_items')
    
    def confirm_orders(self, request, queryset):
        """Confirm selected orders."""
        updated = 0
        for order in queryset:
            if order.status == Order.OrderStatus.PENDING:
                order.confirm_order()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully confirmed {updated} order(s).'
        )
    confirm_orders.short_description = "Confirm selected orders"
    
    def ship_orders(self, request, queryset):
        """Ship selected orders."""
        updated = 0
        for order in queryset:
            if order.status in [Order.OrderStatus.CONFIRMED, Order.OrderStatus.PROCESSING]:
                order.ship_order()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully shipped {updated} order(s).'
        )
    ship_orders.short_description = "Ship selected orders"
    
    def deliver_orders(self, request, queryset):
        """Deliver selected orders."""
        updated = 0
        for order in queryset:
            if order.status == Order.OrderStatus.SHIPPED:
                order.deliver_order()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully delivered {updated} order(s).'
        )
    deliver_orders.short_description = "Deliver selected orders"
    
    def cancel_orders(self, request, queryset):
        """Cancel selected orders."""
        updated = 0
        for order in queryset:
            if order.can_cancel:
                order.cancel_order()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully cancelled {updated} order(s).'
        )
    cancel_orders.short_description = "Cancel selected orders"
    
    def refund_orders(self, request, queryset):
        """Refund selected orders."""
        updated = 0
        for order in queryset:
            if order.can_refund:
                order.refund_order()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully refunded {updated} order(s).'
        )
    refund_orders.short_description = "Refund selected orders"
    
    def soft_delete_orders(self, request, queryset):
        """Soft delete selected orders."""
        updated = queryset.update(
            is_deleted=True,
            deleted_at=timezone.now()
        )
        self.message_user(
            request,
            f'Successfully soft deleted {updated} order(s).'
        )
    soft_delete_orders.short_description = "Soft delete selected orders"
    
    def restore_orders(self, request, queryset):
        """Restore soft-deleted orders."""
        updated = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None
        )
        self.message_user(
            request,
            f'Successfully restored {updated} order(s).'
        )
    restore_orders.short_description = "Restore soft-deleted orders"
    
    def generate_tracking_numbers(self, request, queryset):
        """Generate tracking numbers for selected orders."""
        updated = 0
        for order in queryset:
            if not order.tracking_number and order.status in [
                Order.OrderStatus.SHIPPED, Order.OrderStatus.OUT_FOR_DELIVERY
            ]:
                order.tracking_number = f"TRK-{order.id.hex[:8].upper()}"
                order.save(update_fields=['tracking_number'])
                updated += 1
        
        self.message_user(
            request,
            f'Successfully generated tracking numbers for {updated} order(s).'
        )
    generate_tracking_numbers.short_description = "Generate tracking numbers"
    
    def has_delete_permission(self, request, obj=None):
        """Only allow soft delete, not hard delete."""
        return False
    
    def has_add_permission(self, request):
        """Allow adding orders."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow changing orders."""
        return True
    
    def has_view_permission(self, request, obj=None):
        """Allow viewing orders."""
        return True


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Professional admin interface for OrderItem model.
    """
    
    list_display = [
        'id', 'order', 'product', 'variant', 'quantity', 'unit_price',
        'total_price', 'created_at'
    ]
    
    list_display_links = ['id']
    
    list_filter = [
        'product', 'variant', 'created_at'
    ]
    
    search_fields = [
        'order__order_number', 'product__name', 'variant__name'
    ]
    
    readonly_fields = [
        'id', 'created_at', 'updated_at'
    ]
    
    ordering = ['-created_at']
    
    list_per_page = 50
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'order', 'product', 'variant'
            )
        }),
        ('Item Details', {
            'fields': (
                'quantity', 'unit_price', 'total_price'
            )
        }),
        ('Additional Information', {
            'fields': (
                'notes', 'extra_data'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    raw_id_fields = ['order', 'product', 'variant']
    
    autocomplete_fields = ['product', 'variant']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'order', 'product', 'variant'
        )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Professional admin interface for Payment model.
    """
    
    list_display = [
        'transaction_id', 'order', 'amount', 'currency', 'status',
        'payment_method', 'created_at', 'processed_at'
    ]
    
    list_display_links = ['transaction_id']
    
    list_filter = [
        'status', 'payment_method', 'currency', 'created_at', 'processed_at'
    ]
    
    search_fields = [
        'transaction_id', 'order__order_number', 'error_message'
    ]
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'processed_at'
    ]
    
    ordering = ['-created_at']
    
    list_per_page = 50
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'order', 'transaction_id'
            )
        }),
        ('Payment Details', {
            'fields': (
                'amount', 'currency', 'status', 'payment_method'
            )
        }),
        ('Processing Information', {
            'fields': (
                'payment_details', 'gateway_response', 'error_message'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': (
                'created_at', 'updated_at', 'processed_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'process_payments', 'refund_payments', 'fail_payments'
    ]
    
    raw_id_fields = ['order']
    
    def process_payments(self, request, queryset):
        """Process selected payments."""
        updated = 0
        for payment in queryset:
            if payment.status == Payment.PaymentStatus.PENDING:
                payment.process_payment()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully processed {updated} payment(s).'
        )
    process_payments.short_description = "Process selected payments"
    
    def refund_payments(self, request, queryset):
        """Refund selected payments."""
        updated = 0
        for payment in queryset:
            if payment.status == Payment.PaymentStatus.PAID:
                payment.refund_payment()
                updated += 1
        
        self.message_user(
            request,
            f'Successfully refunded {updated} payment(s).'
        )
    refund_payments.short_description = "Refund selected payments"
    
    def fail_payments(self, request, queryset):
        """Mark selected payments as failed."""
        updated = 0
        for payment in queryset:
            if payment.status == Payment.PaymentStatus.PENDING:
                payment.fail_payment("Admin action: Payment marked as failed")
                updated += 1
        
        self.message_user(
            request,
            f'Successfully marked {updated} payment(s) as failed.'
        )
    fail_payments.short_description = "Mark selected payments as failed"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('order')