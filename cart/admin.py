from django.contrib import admin

# Register your models here.
from .models import Cart

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'total_price', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at', 'updated_at')