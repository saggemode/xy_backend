from django.contrib import admin
from .models import Product, ProductVariant, Category, SubCategory,ProductReview,Coupon,CouponUsage,FlashSale,FlashSaleItem
from django.utils import timezone

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'store', 'base_price', 'stock', 'is_deleted', 'created_at', 'updated_at', 'created_by', 'updated_by')
    list_filter = ('store', 'is_deleted', 'created_at')
    search_fields = ('name', 'sku')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by')
    actions = ['soft_delete_products', 'restore_products']
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

admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(ProductReview)
admin.site.register(Coupon) 
admin.site.register(CouponUsage)
admin.site.register(FlashSale)
admin.site.register(FlashSaleItem)

