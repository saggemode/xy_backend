from django.contrib import admin
from .models import Product, ProductVariant, Category, SubCategory, ProductReview, Coupon, CouponUsage, FlashSale, FlashSaleItem, ProductDiscount
from django.utils import timezone
from django.utils.html import format_html
from django import forms
from django.contrib.admin import SimpleListFilter
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'store', 'base_price', 'current_price_display', 'variants_info', 'on_sale_badge', 'stock', 'is_deleted', 'created_at', 'updated_at')
    list_filter = ('store', 'is_deleted', 'created_at', 'has_variants')
    search_fields = ('name', 'sku')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at', 'current_price_display', 'on_sale_badge', 'variants_info')
    actions = ['soft_delete_products', 'restore_products']
    
    def current_price_display(self, obj):
        if obj.on_sale:
            return format_html(
                '<span style="color: red; text-decoration: line-through;">${}</span> <strong>${}</strong>',
                obj.original_price, obj.current_price
            )
        return format_html('<strong>${}</strong>', obj.current_price)
    current_price_display.short_description = 'Current Price'
    
    def on_sale_badge(self, obj):
        if obj.on_sale:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">ON SALE</span>'
            )
        return '-'
    on_sale_badge.short_description = 'Sale Status'
    
    def variants_info(self, obj):
        """Display variant information"""
        if not obj.has_variants:
            return '-'
        
        variant_counts = {}
        for variant in obj.variants.filter(is_active=True):
            variant_type = variant.get_variant_type_display()
            if variant_type not in variant_counts:
                variant_counts[variant_type] = 0
            variant_counts[variant_type] += 1
        
        if not variant_counts:
            return '-'
        
        info_parts = []
        for variant_type, count in variant_counts.items():
            info_parts.append(f"{variant_type}: {count}")
        
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">{}</span>',
            ', '.join(info_parts)
        )
    variants_info.short_description = 'Variants'
    
    def soft_delete_products(self, request, queryset):
        updated = 0
        for product in queryset:
            product.soft_delete(user=request.user)
            updated += 1
        self.message_user(request, f"Soft deleted {updated} product(s).")
    soft_delete_products.short_description = "Soft delete selected products"
    
    def restore_products(self, request, queryset):
        updated = 0
        for product in queryset:
            product.restore(user=request.user)
            updated += 1
        self.message_user(request, f"Restored {updated} product(s).")
    restore_products.short_description = "Restore selected products"
    
    @method_decorator(csrf_exempt)
    @method_decorator(require_http_methods(["GET"]))
    def get_variant_options(self, request):
        """AJAX endpoint to get variant options for a product"""
        product_id = request.GET.get('product_id')
        variant_type = request.GET.get('variant_type')
        
        if not product_id or not variant_type:
            return JsonResponse({'options': []})
        
        try:
            product = Product.objects.get(id=product_id)
            
            if variant_type == 'size':
                options = product.available_sizes or []
            elif variant_type == 'color':
                options = product.available_colors or []
            else:
                options = []
            
            return JsonResponse({'options': options})
        except Product.DoesNotExist:
            return JsonResponse({'options': []})

class ProductVariantForm(forms.ModelForm):
    """Custom form for ProductVariant with dynamic variant options"""
    
    class Meta:
        model = ProductVariant
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        variant_type = cleaned_data.get('variant_type')
        name = cleaned_data.get('name')
        
        if product and variant_type and name:
            # Validate that the selected name is available for the product
            if variant_type == 'size' and product.available_sizes:
                # For sizes, check if the name contains any of the available sizes
                # This handles cases where the variant name might include the product name
                available_sizes_str = [str(size) for size in product.available_sizes]
                name_matches = any(str(size) in name for size in available_sizes_str)
                
                if not name_matches:
                    raise forms.ValidationError(f"'{name}' does not contain any of the product's available sizes: {', '.join(available_sizes_str)}")
            elif variant_type == 'color' and product.available_colors:
                # For colors, check if the name contains any of the available colors
                available_colors_str = [str(color) for color in product.available_colors]
                name_matches = any(str(color) in name for color in available_colors_str)
                
                if not name_matches:
                    raise forms.ValidationError(f"'{name}' does not contain any of the product's available colors: {', '.join(available_colors_str)}")
        
        return cleaned_data

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    form = ProductVariantForm
    list_display = ('name', 'variant_type', 'product', 'pricing_mode', 'price_display', 'stock', 'is_active')
    list_filter = ('variant_type', 'pricing_mode', 'is_active', 'product__store')
    search_fields = ('name', 'sku', 'product__name')
    readonly_fields = ('created_at', 'updated_at', 'price_display')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product', 'variant_type', 'name', 'sku')
        }),
        ('Pricing', {
            'fields': ('pricing_mode', 'price_adjustment', 'individual_price', 'price_display')
        }),
        ('Inventory', {
            'fields': ('stock', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Add data attributes to product choices for JavaScript
        if 'product' in form.base_fields:
            product_field = form.base_fields['product']
            
            # Only modify choices if they exist and are properly formatted
            if hasattr(product_field, 'choices') and product_field.choices:
                try:
                    new_choices = [('', '---------')]
                    
                    # Get all products with their variant data
                    products = Product.objects.all()
                    
                    for product in products:
                        sizes = ','.join(product.available_sizes) if product.available_sizes else ''
                        colors = ','.join(product.available_colors) if product.available_colors else ''
                        
                        # Add data attributes to the choice
                        choice_text = f"{product.name} ({product.store.name}) - ${product.base_price}"
                        if sizes or colors:
                            choice_text += f" [Sizes: {sizes}] [Colors: {colors}]"
                        
                        new_choices.append((str(product.id), choice_text))
                    
                    product_field.choices = new_choices
                except Exception as e:
                    # If there's any error, keep the original choices
                    pass
        
        return form
    
    def price_display(self, obj):
        """Display the current price with formatting"""
        try:
            current_price = obj.current_price
            base_price = obj.base_price
            
            if obj.pricing_mode == 'individual':
                # Show individual price
                if obj.product.on_sale:
                    discount = obj.product.active_discount
                    discounted_price = discount.calculate_discount_price(base_price)
                    if discounted_price != base_price:
                        savings = base_price - discounted_price
                        savings_percentage = (savings / base_price) * 100
                        return format_html(
                            '<div style="line-height: 1.4;">'
                            '<div><span style="color: red; text-decoration: line-through;">${}</span></div>'
                            '<div><strong style="color: green; font-size: 14px;">${}</strong></div>'
                            '<div style="color: #666; font-size: 11px;">'
                            '<span style="color: #28a745;">↓ Save ${}</span> ({}% off)'
                            '</div>'
                            '</div>',
                            f"{base_price:,.2f}", f"{discounted_price:,.2f}", 
                            f"{savings:,.2f}", f"{savings_percentage:.1f}"
                        )
                    else:
                        return format_html('<strong>${}</strong>', f"{base_price:,.2f}")
                else:
                    return format_html('<strong>${}</strong>', f"{base_price:,.2f}")
            else:
                # Show adjustment-based pricing
                product_price = obj.product.current_price
                final_price = product_price + obj.price_adjustment
                
                if obj.price_adjustment > 0:
                    return format_html(
                        '<div>Product: ${}</div>'
                        '<div><strong>+${} = ${}</strong></div>',
                        f"{product_price:,.2f}", f"{obj.price_adjustment:,.2f}", f"{final_price:,.2f}"
                    )
                elif obj.price_adjustment < 0:
                    return format_html(
                        '<div>Product: ${}</div>'
                        '<div><strong>-${} = ${}</strong></div>',
                        f"{product_price:,.2f}", f"{abs(obj.price_adjustment):,.2f}", f"{final_price:,.2f}"
                    )
                else:
                    return format_html('<strong>${}</strong>', f"{final_price:,.2f}")
        except Exception as e:
            return f"Error: {str(e)}"
    
    price_display.short_description = 'Current Price'

@admin.register(ProductDiscount)
class ProductDiscountAdmin(admin.ModelAdmin):
    list_display = ['product', 'product_base_price', 'discount_type', 'discount_value', 'calculated_price', 'start_date', 'end_date', 'is_active', 'is_valid_badge']
    list_filter = ['discount_type', 'is_active', 'start_date', 'end_date']
    search_fields = ['product__name']
    readonly_fields = ['created_at', 'updated_at', 'product_base_price', 'calculated_price']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product', 'product_base_price')
        }),
        ('Discount Details', {
            'fields': ('discount_type', 'discount_value', 'calculated_price', 'max_discount_amount')
        }),
        ('Timing & Conditions', {
            'fields': ('start_date', 'end_date', 'is_active', 'min_quantity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_base_price(self, obj):
        """Display the product's base price"""
        if obj.product:
            return format_html('<strong>${}</strong>', f"{float(obj.product.base_price):,.2f}")
        return '-'
    product_base_price.short_description = 'Base Price'
    product_base_price.admin_order_field = 'product__base_price'
    
    def calculated_price(self, obj):
        """Display the calculated discounted price with savings info"""
        if obj.product and obj.discount_value:
            try:
                base_price = float(obj.product.base_price)
                
                # Debug information
                is_valid = obj.is_valid
                discount_type = obj.discount_type
                discount_value = float(obj.discount_value)
                
                # Calculate discount manually to debug
                if is_valid and discount_type == 'percentage':
                    discount_amount = (base_price * discount_value) / 100
                    if obj.max_discount_amount:
                        discount_amount = min(discount_amount, float(obj.max_discount_amount))
                    discounted_price = base_price - discount_amount
                else:
                    discounted_price = base_price
                
                if discounted_price != base_price:
                    # Calculate savings
                    savings = base_price - discounted_price
                    savings_percentage = (savings / base_price) * 100
                    
                    return format_html(
                        '<div style="line-height: 1.4;">'
                        '<div><span style="color: red; text-decoration: line-through;">${}</span></div>'
                        '<div><strong style="color: green; font-size: 14px;">${}</strong></div>'
                        '<div style="color: #666; font-size: 11px;">'
                        '<span style="color: #28a745;">↓ Save ${}</span> ({}% off)'
                        '</div>'
                        '<div style="color: #999; font-size: 10px;">'
                        'Valid: {}, Type: {}, Value: {}'
                        '</div>'
                        '</div>',
                        f"{base_price:,.2f}", f"{discounted_price:,.2f}", 
                        f"{savings:,.2f}", f"{savings_percentage:.1f}",
                        is_valid, discount_type, discount_value
                    )
                else:
                    return format_html(
                        '<div>'
                        '<strong>${}</strong>'
                        '<div style="color: #999; font-size: 10px;">'
                        'Valid: {}, Type: {}, Value: {}'
                        '</div>'
                        '</div>',
                        f"{base_price:,.2f}", is_valid, discount_type, discount_value
                    )
            except Exception as e:
                return format_html('<strong>Error: {}</strong>', str(e))
        return '-'
    calculated_price.short_description = 'Discounted Price & Savings'
    
    def is_valid_badge(self, obj):
        if obj.is_valid:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">ACTIVE</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">INACTIVE</span>'
            )
    is_valid_badge.short_description = 'Status'
    is_valid_badge.admin_order_field = 'is_active'

admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(ProductReview)
admin.site.register(Coupon) 
admin.site.register(CouponUsage)
admin.site.register(FlashSale)
admin.site.register(FlashSaleItem)

