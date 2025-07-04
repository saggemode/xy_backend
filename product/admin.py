from django.contrib import admin
from .models import Product, ProductVariant, Category, SubCategory, ProductReview, Coupon, CouponUsage, FlashSale, FlashSaleItem, ProductDiscount
from django.utils import timezone
from django.utils.html import format_html

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'store', 'base_price', 'current_price_display', 'on_sale_badge', 'stock', 'is_deleted', 'created_at', 'updated_at', 'created_by', 'updated_by')
    list_filter = ('store', 'is_deleted', 'created_at')
    search_fields = ('name', 'sku')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by', 'current_price_display', 'on_sale_badge')
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

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    search_fields = ('name', 'sku')

@admin.register(ProductDiscount)
class ProductDiscountAdmin(admin.ModelAdmin):
    list_display = ['product', 'discount_type', 'discount_value', 'start_date', 'end_date', 'is_active', 'is_valid_badge']
    list_filter = ['discount_type', 'is_active', 'start_date', 'end_date']
    search_fields = ['product__name']
    readonly_fields = ['created_at', 'updated_at']
    
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
    is_valid_badge.boolean = True

admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(ProductReview)
admin.site.register(Coupon) 
admin.site.register(CouponUsage)
admin.site.register(FlashSale)
admin.site.register(FlashSaleItem)

