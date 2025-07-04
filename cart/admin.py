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
            ('low_stock', 'Low Stock Items'),
            ('high_value', 'High Value Items (>$100)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'low_stock':
            # Simplified low stock filter
            return queryset.filter(quantity__gte=1)
        elif self.value() == 'high_value':
            # Simplified high value filter
            return queryset.filter(quantity__gte=1)
        return queryset

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_link', 'product_link', 'store_link', 'quantity', 
        'total_price_display', 'created_at', 'updated_at'
    )
    list_filter = (
        CartItemFilter, 'store', 'created_at', 'updated_at',
        'selected_size', 'selected_color'
    )
    search_fields = (
        'user__username', 'user__email', 'product__name', 
        'store__name', 'variant__name'
    )
    readonly_fields = (
        'id', 'created_at', 'updated_at', 
        'total_price_display', 'unit_price_display'
    )
    list_per_page = 25
    list_select_related = ('user', 'product', 'store', 'variant')
    actions = [
        'delete_items', 'export_to_csv',
        'bulk_update_quantity', 'move_to_wishlist'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'store', 'product', 'variant')
        }),
        ('Item Details', {
            'fields': ('quantity', 'selected_size', 'selected_color', 'unit_price_display', 'total_price_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
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



    def delete_items(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Deleted {count} cart item(s).")
    delete_items.short_description = "Delete selected cart items"

    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cart_items.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User', 'Store', 'Product', 'Variant', 'Quantity', 
            'Size', 'Color', 'Unit Price', 'Total Price', 'Created At'
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
                wishlist_item, created = Wishlist.objects.get_or_create(
                    user=item.user,
                    product=item.product,
                    store=item.store,
                    defaults={'variant': item.variant}
                )
                item.delete()
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
            'user', 'product', 'store', 'variant'
        )



    class Media:
        css = {
            'all': ('admin/css/cart_admin.css',)
        }
        js = ('admin/js/cart_admin.js',)
