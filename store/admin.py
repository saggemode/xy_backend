from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Store, StoreAnalytics, StoreStaff, CustomerLifetimeValue

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'is_verified', 'is_deleted', 'created_at', 'updated_at', 'created_by', 'updated_by')
    list_filter = ('is_active', 'is_verified', 'is_deleted', 'created_at')
    search_fields = ('name', 'owner__username', 'description')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by')
    actions = ['soft_delete_stores', 'restore_stores']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'location', 'owner')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'phone_number', 'website_url')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('logo', 'cover_image'),
            'classes': ('collapse',)
        }),
        ('Status & Verification', {
            'fields': ('status', 'is_active', 'is_verified', 'verified_at', 'verified_by')
        }),
        ('Business Settings', {
            'fields': ('commission_rate', 'auto_approve_products'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_products', 'active_products', 'total_staff', 'is_operational'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 25

    def owner_username(self, obj):
        return obj.owner.username if obj.owner else '-'
    owner_username.short_description = 'Owner'
    owner_username.admin_order_field = 'owner__username'

    def total_products_display(self, obj):
        count = obj.total_products
        color = 'green' if count > 0 else 'red'
        return format_html('<span style="color: {};">{}</span>', color, count)
    total_products_display.short_description = 'Products'

    def total_staff_display(self, obj):
        count = obj.total_staff
        color = 'green' if count > 0 else 'orange'
        return format_html('<span style="color: {};">{}</span>', color, count)
    total_staff_display.short_description = 'Staff'

    def revenue_display(self, obj):
        try:
            analytics = obj.analytics
            revenue = analytics.revenue if analytics else 0
            return f"${revenue:,.2f}"
        except:
            return "$0.00"
    revenue_display.short_description = 'Revenue'

    def last_updated(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    last_updated.short_description = 'Last Updated'

    def soft_delete_stores(self, request, queryset):
        updated = 0
        for store in queryset:
            store.soft_delete(user=request.user)
            updated += 1
        self.message_user(request, f"Soft deleted {updated} store(s).")
    soft_delete_stores.short_description = "Soft delete selected stores"

    def restore_stores(self, request, queryset):
        updated = 0
        for store in queryset:
            store.restore(user=request.user)
            updated += 1
        self.message_user(request, f"Restored {updated} store(s).")
    restore_stores.short_description = "Restore selected stores"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'analytics')

@admin.register(StoreStaff)
class StoreStaffAdmin(admin.ModelAdmin):
    list_display = [
        'user_username', 'store_name', 'role_display', 'is_active', 
        'permissions_display', 'joined_at', 'last_active_display'
    ]
    list_filter = [
        'role', 'is_active', 'joined_at', 'can_manage_products', 
        'can_manage_orders', 'can_manage_staff', 'can_view_analytics',
        ('store', admin.RelatedOnlyFieldListFilter),
        ('user', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'store__name'
    ]
    readonly_fields = [
        'id', 'joined_at', 'last_active', 'created_by', 'updated_by', 'deleted_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'store', 'user', 'role')
        }),
        ('Status & Permissions', {
            'fields': ('is_active', 'can_manage_products', 'can_manage_orders', 
                      'can_manage_staff', 'can_view_analytics')
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'last_active'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'updated_by', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    actions = [
        'activate_staff', 'deactivate_staff', 'bulk_assign_role',
        'bulk_update_permissions'
    ]
    date_hierarchy = 'joined_at'
    ordering = ['-joined_at']
    list_per_page = 25

    def user_username(self, obj):
        return obj.user.username if obj.user else '-'
    user_username.short_description = 'User'
    user_username.admin_order_field = 'user__username'

    def store_name(self, obj):
        return obj.store.name if obj.store else '-'
    store_name.short_description = 'Store'
    store_name.admin_order_field = 'store__name'

    def role_display(self, obj):
        return obj.get_role_display()
    role_display.short_description = 'Role'
    role_display.admin_order_field = 'role'

    def permissions_display(self, obj):
        permissions = []
        if obj.can_manage_products:
            permissions.append('Products')
        if obj.can_manage_orders:
            permissions.append('Orders')
        if obj.can_manage_staff:
            permissions.append('Staff')
        if obj.can_view_analytics:
            permissions.append('Analytics')
        return ', '.join(permissions) if permissions else 'None'
    permissions_display.short_description = 'Permissions'

    def last_active_display(self, obj):
        if obj.last_active:
            return obj.last_active.strftime('%Y-%m-%d %H:%M')
        return 'Never'
    last_active_display.short_description = 'Last Active'

    def activate_staff(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} staff members have been activated.')
    activate_staff.short_description = "Activate selected staff"

    def deactivate_staff(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} staff members have been deactivated.')
    deactivate_staff.short_description = "Deactivate selected staff"

    def bulk_assign_role(self, request, queryset):
        return HttpResponseRedirect('/admin/store/staff-bulk-role/')
    bulk_assign_role.short_description = "Bulk assign role"

    def bulk_update_permissions(self, request, queryset):
        return HttpResponseRedirect('/admin/store/staff-bulk-permissions/')
    bulk_update_permissions.short_description = "Bulk update permissions"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'store')

@admin.register(StoreAnalytics)
class StoreAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'store_name', 'total_views', 'unique_visitors', 'total_orders', 
        'revenue_display', 'conversion_rate_display', 'last_updated'
    ]
    list_filter = [
        'last_updated', 'calculated_at',
        ('store', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ['store__name']
    readonly_fields = [
        'id', 'last_updated', 'calculated_at', 'top_selling_products'
    ]
    fieldsets = (
        ('Store Information', {
            'fields': ('id', 'store')
        }),
        ('View Metrics', {
            'fields': ('total_views', 'unique_visitors', 'page_views')
        }),
        ('Sales Metrics', {
            'fields': ('total_sales', 'revenue', 'total_orders', 'average_order_value')
        }),
        ('Conversion Metrics', {
            'fields': ('conversion_rate', 'bounce_rate')
        }),
        ('Product Metrics', {
            'fields': ('total_products', 'active_products', 'top_selling_products')
        }),
        ('Customer Metrics', {
            'fields': ('total_customers', 'repeat_customers', 'customer_retention_rate')
        }),
        ('Timestamps', {
            'fields': ('last_updated', 'calculated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['recalculate_analytics', 'export_analytics']
    date_hierarchy = 'last_updated'
    ordering = ['-last_updated']
    list_per_page = 25

    def store_name(self, obj):
        return obj.store.name if obj.store else '-'
    store_name.short_description = 'Store'
    store_name.admin_order_field = 'store__name'

    def revenue_display(self, obj):
        return f"${obj.revenue:,.2f}"
    revenue_display.short_description = 'Revenue'
    revenue_display.admin_order_field = 'revenue'

    def conversion_rate_display(self, obj):
        return f"{obj.conversion_rate:.2f}%"
    conversion_rate_display.short_description = 'Conversion Rate'
    conversion_rate_display.admin_order_field = 'conversion_rate'

    def recalculate_analytics(self, request, queryset):
        for analytics in queryset:
            try:
                analytics.calculate_analytics()
            except Exception as e:
                self.message_user(request, f'Error calculating analytics for {analytics.store.name}: {str(e)}', level=messages.ERROR)
        self.message_user(request, f'Analytics recalculated for {queryset.count()} stores.')
    recalculate_analytics.short_description = "Recalculate analytics"

    def export_analytics(self, request, queryset):
        return HttpResponseRedirect('/admin/store/analytics-export/')
    export_analytics.short_description = "Export analytics data"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('store')

@admin.register(CustomerLifetimeValue)
class CustomerLifetimeValueAdmin(admin.ModelAdmin):
    list_display = [
        'user_username', 'total_spent_display', 'total_orders', 
        'average_order_value_display', 'purchase_frequency_display',
        'customer_since', 'last_purchase_date'
    ]
    list_filter = [
        'customer_since', 'last_purchase_date', 'last_updated',
        ('user', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'user__username', 'user__email', 'user__first_name', 'user__last_name'
    ]
    readonly_fields = [
        'id', 'customer_since', 'last_updated', 'average_order_value', 'purchase_frequency'
    ]
    fieldsets = (
        ('Customer Information', {
            'fields': ('id', 'user')
        }),
        ('Financial Metrics', {
            'fields': ('total_spent', 'total_orders', 'average_order_value')
        }),
        ('Purchase History', {
            'fields': ('first_purchase_date', 'last_purchase_date', 'purchase_frequency')
        }),
        ('Timestamps', {
            'fields': ('customer_since', 'last_updated'),
            'classes': ('collapse',)
        }),
    )
    actions = ['recalculate_cltv', 'export_cltv_data']
    date_hierarchy = 'customer_since'
    ordering = ['-total_spent']
    list_per_page = 25

    def user_username(self, obj):
        return obj.user.username if obj.user else '-'
    user_username.short_description = 'Customer'
    user_username.admin_order_field = 'user__username'

    def total_spent_display(self, obj):
        return f"${obj.total_spent:,.2f}"
    total_spent_display.short_description = 'Total Spent'
    total_spent_display.admin_order_field = 'total_spent'

    def average_order_value_display(self, obj):
        return f"${obj.average_order_value:,.2f}"
    average_order_value_display.short_description = 'Avg Order Value'
    average_order_value_display.admin_order_field = 'average_order_value'

    def purchase_frequency_display(self, obj):
        return f"{obj.purchase_frequency:.2f}/month"
    purchase_frequency_display.short_description = 'Purchase Frequency'
    purchase_frequency_display.admin_order_field = 'purchase_frequency'

    def recalculate_cltv(self, request, queryset):
        for cltv in queryset:
            try:
                cltv.calculate_cltv()
            except Exception as e:
                self.message_user(request, f'Error calculating CLTV for {cltv.user.username}: {str(e)}', level=messages.ERROR)
        self.message_user(request, f'CLTV recalculated for {queryset.count()} customers.')
    recalculate_cltv.short_description = "Recalculate CLTV"

    def export_cltv_data(self, request, queryset):
        return HttpResponseRedirect('/admin/store/cltv-export/')
    export_cltv_data.short_description = "Export CLTV data"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

# Custom admin site configuration
admin.site.site_header = "Store Management System"
admin.site.site_title = "Store Admin"
admin.site.index_title = "Store Management Dashboard" 