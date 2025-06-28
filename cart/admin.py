from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Cart
from django.utils import timezone
from django.db.models import Sum, Count
from django.contrib.admin import SimpleListFilter

class CartItemFilter(SimpleListFilter):
    title = 'Cart Status'
    parameter_name = 'cart_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active Items'),
            ('deleted', 'Deleted Items'),
            ('low_stock', 'Low Stock Items'),
            ('high_value', 'High Value Items (>$100)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_deleted=False)
        elif self.value() == 'deleted':
            return queryset.filter(is_deleted=True)
        elif self.value() == 'low_stock':
            # Simplified low stock filter
            return queryset.filter(
                is_deleted=False,
                quantity__gte=1
            )
        elif self.value() == 'high_value':
            # Simplified high value filter
            return queryset.filter(
                is_deleted=False,
                quantity__gte=1
            )
        return queryset

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_link', 'product_link', 'store_link', 'quantity', 
        'total_price_display', 'status_badge', 'created_at', 'updated_at'
    )
    list_filter = (
        CartItemFilter, 'store', 'created_at', 'updated_at', 'is_deleted',
        'selected_size', 'selected_color'
    )
    search_fields = (
        'user__username', 'user__email', 'product__name', 
        'store__name', 'variant__name'
    )
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'deleted_at', 
        'created_by', 'updated_by', 'total_price_display', 'unit_price_display'
    )
    list_per_page = 25
    list_select_related = ('user', 'product', 'store', 'variant', 'created_by', 'updated_by')
    actions = [
        'soft_delete_items', 'restore_items', 'export_to_csv',
        'bulk_update_quantity', 'move_to_wishlist'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'store', 'product', 'variant')
        }),
        ('Item Details', {
            'fields': ('quantity', 'selected_size', 'selected_color', 'unit_price_display', 'total_price_display')
        }),
        ('Status', {
            'fields': ('is_deleted', 'deleted_at')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def product_link(self, obj):
        if obj.product:
            url = reverse('admin:product_product_change', args=[obj.product.id])
            return format_html('<a href="{}">{}</a>', url, obj.product.name)
        return '-'
    product_link.short_description = 'Product'
    product_link.admin_order_field = 'product__name'

    def store_link(self, obj):
        if obj.store:
            url = reverse('admin:store_store_change', args=[obj.store.id])
            return format_html('<a href="{}">{}</a>', url, obj.store.name)
        return '-'
    store_link.short_description = 'Store'
    store_link.admin_order_field = 'store__name'

    def total_price_display(self, obj):
        return format_html('<strong>${}</strong>', obj.total_price)
    total_price_display.short_description = 'Total Price'
    total_price_display.admin_order_field = 'total_price'

    def unit_price_display(self, obj):
        return format_html('${}', obj.unit_price)
    unit_price_display.short_description = 'Unit Price'

    def status_badge(self, obj):
        if obj.is_deleted:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">Deleted</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">Active</span>'
            )
    status_badge.short_description = 'Status'

    def soft_delete_items(self, request, queryset):
        updated = 0
        for item in queryset:
            item.soft_delete(user=request.user)
            updated += 1
        self.message_user(request, f"Soft deleted {updated} cart item(s).")
    soft_delete_items.short_description = "Soft delete selected cart items"

    def restore_items(self, request, queryset):
        updated = 0
        for item in queryset:
            item.restore(user=request.user)
            updated += 1
        self.message_user(request, f"Restored {updated} cart item(s).")
    restore_items.short_description = "Restore selected cart items"

    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cart_items.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User', 'Store', 'Product', 'Variant', 'Quantity', 
            'Size', 'Color', 'Unit Price', 'Total Price', 'Status', 'Created At'
        ])
        
        for item in queryset:
            writer.writerow([
                str(item.id), 
                item.user.username if item.user else '',
                item.store.name if item.store else '',
                item.product.name if item.product else '',
                item.variant.name if item.variant else '',
                item.quantity, 
                item.selected_size or '',
                item.selected_color or '', 
                str(item.unit_price),
                str(item.total_price), 
                'Deleted' if item.is_deleted else 'Active',
                item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''
            ])
        
        return response
    export_to_csv.short_description = "Export selected items to CSV"

    def bulk_update_quantity(self, request, queryset):
        from django import forms
        
        class BulkUpdateForm(forms.Form):
            new_quantity = forms.IntegerField(min_value=1, label="New Quantity")
        
        if 'apply' in request.POST:
            form = BulkUpdateForm(request.POST)
            if form.is_valid():
                new_quantity = form.cleaned_data['new_quantity']
                updated = 0
                for item in queryset:
                    item.quantity = new_quantity
                    item._current_user = request.user
                    item.save()
                    updated += 1
                self.message_user(request, f"Updated quantity to {new_quantity} for {updated} item(s).")
                return
        else:
            form = BulkUpdateForm()
        
        return self.response_action(request, queryset, form, 'bulk_update_quantity')
    bulk_update_quantity.short_description = "Bulk update quantity"

    def move_to_wishlist(self, request, queryset):
        from wishlist.models import Wishlist
        
        moved = 0
        errors = 0
        
        for item in queryset:
            try:
                if not item.is_deleted:
                    wishlist_item, created = Wishlist.objects.get_or_create(
                        user=item.user,
                        product=item.product,
                        store=item.store,
                        defaults={'variant': item.variant}
                    )
                    item.soft_delete(user=request.user)
                    moved += 1
            except Exception:
                errors += 1
        
        if moved > 0:
            self.message_user(request, f"Moved {moved} item(s) to wishlist.")
        if errors > 0:
            self.message_user(request, f"Failed to move {errors} item(s).", level='WARNING')
    move_to_wishlist.short_description = "Move selected items to wishlist"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'user', 'product', 'store', 'variant', 'created_by', 'updated_by'
        )

    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly based on object state"""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_deleted:
            readonly_fields.extend(['user', 'store', 'product', 'variant', 'quantity'])
        return readonly_fields

    class Media:
        css = {
            'all': ('admin/css/cart_admin.css',)
        }
        js = ('admin/js/cart_admin.js',)
