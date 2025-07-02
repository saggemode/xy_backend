from django.contrib import admin
from .models import Wishlist
from django.utils import timezone

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'store', 'created_at', 'updated_at')
    list_filter = ('user', 'created_at')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at', 'updated_at')
    actions = []
    
    def store(self, obj):
        return obj.product.store if obj.product and hasattr(obj.product, 'store') else None
    store.admin_order_field = 'product__store'
    store.short_description = 'Store'