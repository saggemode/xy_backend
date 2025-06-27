from django.contrib import admin
from .models import Cart
from django.utils import timezone

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'total_price', 'is_deleted', 'created_at', 'updated_at', 'created_by', 'updated_by')
    list_filter = ('user', 'created_at', 'is_deleted')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by')
    actions = ['soft_delete_items', 'restore_items']
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