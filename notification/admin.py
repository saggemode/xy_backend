from django.contrib import admin
from .models import Notification

# Register your models here.
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'title', 'notification_type', 'level', 'isRead', 'created_at']
    list_filter = ['notification_type', 'level', 'isRead', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'recipient', 'sender', 'title', 'message')
        }),
        ('Notification Details', {
            'fields': ('notification_type', 'level', 'link', 'isRead')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
