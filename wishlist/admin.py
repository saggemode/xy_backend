from django.contrib import admin
from .models import Wishlist
from django.utils import timezone

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'store', 'is_deleted', 'created_at', 'updated_at', 'created_by', 'updated_by')
    list_filter = ('user', 'is_deleted', 'created_at')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by')
    actions = ['soft_delete_items', 'restore_items']
    def soft_delete_items(self, request, queryset):
        updated = 0
        for item in queryset:
            item.soft_delete(user=request.user)
            updated += 1
        self.message_user(request, f"Soft deleted {updated} wishlist item(s).")
    soft_delete_items.short_description = "Soft delete selected wishlist items"
    def restore_items(self, request, queryset):
        updated = 0
        for item in queryset:
            item.restore(user=request.user)
            updated += 1
        self.message_user(request, f"Restored {updated} wishlist item(s).")
    restore_items.short_description = "Restore selected wishlist items"
    def store(self, obj):
        return obj.product.store if obj.product and hasattr(obj.product, 'store') else None
    store.admin_order_field = 'product__store'
    store.short_description = 'Store'