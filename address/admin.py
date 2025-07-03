from django.contrib import admin
from .models import ShippingAddress
from django.utils.html import format_html
from django.utils import timezone

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'address', 'city', 'state', 'country', 'postal_code',
        'phone', 'is_default', 'created_at', 'updated_at'
    ]
    list_filter = ['user', 'city', 'state', 'country', 'is_default', 'created_at']
    search_fields = ['address', 'city', 'state', 'country', 'postal_code', 'phone', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['set_as_default']
    
    def set_as_default(self, request, queryset):
        updated = 0
        for address in queryset:
            address.is_default = True
            address.save(update_fields=['is_default'])
            updated += 1
        self.message_user(request, f"Set {updated} address(es) as default.")
    set_as_default.short_description = "Set selected addresses as default"
