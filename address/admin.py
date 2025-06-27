from django.contrib import admin
from .models import ShippingAddress
from django.utils.html import format_html
from django.utils import timezone

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'address', 'city', 'state', 'country', 'postal_code',
        'phone', 'is_default', 'is_deleted', 'created_at', 'updated_at', 'created_by', 'updated_by'
    ]
    list_filter = ['user', 'city', 'state', 'country', 'is_default', 'is_deleted', 'created_at']
    search_fields = ['address', 'city', 'state', 'country', 'postal_code', 'phone', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by']
    actions = ['soft_delete_addresses', 'restore_addresses', 'set_as_default']
    def soft_delete_addresses(self, request, queryset):
        updated = 0
        for address in queryset:
            address.soft_delete(user=request.user)
            updated += 1
        self.message_user(request, f"Soft deleted {updated} address(es).")
    soft_delete_addresses.short_description = "Soft delete selected addresses"
    def restore_addresses(self, request, queryset):
        updated = 0
        for address in queryset:
            address.restore(user=request.user)
            updated += 1
        self.message_user(request, f"Restored {updated} address(es).")
    restore_addresses.short_description = "Restore selected addresses"
    def set_as_default(self, request, queryset):
        updated = 0
        for address in queryset:
            address.is_default = True
            address.save(update_fields=['is_default'])
            updated += 1
        self.message_user(request, f"Set {updated} address(es) as default.")
    set_as_default.short_description = "Set selected addresses as default"
