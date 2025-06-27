from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Professional admin interface for Notification model.
    
    Features:
    - Comprehensive list display with all important fields
    - Advanced filtering and search capabilities
    - Organized fieldsets for better UX
    - Custom actions for bulk operations
    - Read-only fields for audit data
    - Custom list filters and search fields
    """
    
    # List display configuration
    list_display = [
        'id', 'recipient', 'notification_type', 'level', 'status', 
        'isRead', 'priority', 'title', 'created_at', 'is_deleted'
    ]
    
    # List display links
    list_display_links = ['id', 'title']
    
    # List filters for easy filtering
    list_filter = [
        'notification_type', 'level', 'status', 'isRead', 'is_deleted',
        'priority', 'created_at', 'read_at', 'deleted_at'
    ]
    
    # Search fields
    search_fields = [
        'title', 'message', 'action_text', 'source',
        'recipient__username', 'sender__username', 'user__username',
        'orderId__id'
    ]
    
    # Read-only fields
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'read_at', 'deleted_at',
        'is_actionable', 'age_in_hours', 'is_urgent', 'absolute_url'
    ]
    
    # Ordering
    ordering = ['-created_at']
    
    # Items per page
    list_per_page = 50
    
    # Date hierarchy
    date_hierarchy = 'created_at'
    
    # Fieldsets for organized form display
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'recipient', 'sender', 'user', 'orderId',
                'title', 'message'
            )
        }),
        ('Notification Details', {
            'fields': (
                'notification_type', 'level', 'status',
                'priority', 'source'
            )
        }),
        ('Read Status', {
            'fields': (
                'isRead', 'read_at'
            )
        }),
        ('Actionable Content', {
            'fields': (
                'action_text', 'action_url', 'link'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'extra_data', 'is_actionable', 'age_in_hours', 'is_urgent'
            ),
            'classes': ('collapse',)
        }),
        ('Soft Delete', {
            'fields': (
                'is_deleted', 'deleted_at'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': (
                'created_at', 'updated_at', 'absolute_url'
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Custom actions
    actions = [
        'mark_as_read', 'mark_as_unread', 'soft_delete_notifications',
        'restore_notifications', 'set_high_priority', 'set_low_priority'
    ]
    
    # Filter horizontal for many-to-many relationships (if any)
    # filter_horizontal = []
    
    # Raw ID fields for better performance with large datasets
    raw_id_fields = ['recipient', 'sender', 'user', 'orderId']
    
    # Autocomplete fields
    autocomplete_fields = ['recipient', 'sender', 'user']
    
    def absolute_url(self, obj):
        """Display absolute URL as a clickable link."""
        if obj.pk:
            url = obj.get_absolute_url()
            return format_html('<a href="{}" target="_blank">View</a>', url)
        return '-'
    absolute_url.short_description = 'URL'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance."""
        return super().get_queryset(request).select_related(
            'recipient', 'sender', 'user', 'orderId'
        )
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read."""
        updated = queryset.update(
            isRead=True,
            read_at=timezone.now(),
            status=Notification.NotificationStatus.READ
        )
        self.message_user(
            request,
            f'Successfully marked {updated} notification(s) as read.'
        )
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread."""
        updated = queryset.update(
            isRead=False,
            read_at=None,
            status=Notification.NotificationStatus.DELIVERED
        )
        self.message_user(
            request,
            f'Successfully marked {updated} notification(s) as unread.'
        )
    mark_as_unread.short_description = "Mark selected notifications as unread"
    
    def soft_delete_notifications(self, request, queryset):
        """Soft delete selected notifications."""
        updated = queryset.update(
            is_deleted=True,
            deleted_at=timezone.now()
        )
        self.message_user(
            request,
            f'Successfully soft deleted {updated} notification(s).'
        )
    soft_delete_notifications.short_description = "Soft delete selected notifications"
    
    def restore_notifications(self, request, queryset):
        """Restore soft-deleted notifications."""
        updated = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None
        )
        self.message_user(
            request,
            f'Successfully restored {updated} notification(s).'
        )
    restore_notifications.short_description = "Restore soft-deleted notifications"
    
    def set_high_priority(self, request, queryset):
        """Set high priority for selected notifications."""
        updated = queryset.update(priority=8)
        self.message_user(
            request,
            f'Successfully set high priority for {updated} notification(s).'
        )
    set_high_priority.short_description = "Set high priority (8)"
    
    def set_low_priority(self, request, queryset):
        """Set low priority for selected notifications."""
        updated = queryset.update(priority=2)
        self.message_user(
            request,
            f'Successfully set low priority for {updated} notification(s).'
        )
    set_low_priority.short_description = "Set low priority (2)"
    
    def has_delete_permission(self, request, obj=None):
        """Only allow soft delete, not hard delete."""
        return False
    
    def has_add_permission(self, request):
        """Allow adding notifications."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow changing notifications."""
        return True
    
    def has_view_permission(self, request, obj=None):
        """Allow viewing notifications."""
        return True

