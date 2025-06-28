import uuid
from django.db import models
from order.models import Order
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models import JSONField
from django.core.exceptions import ValidationError
from django.utils import timezone

class Notification(models.Model):
    """
    Professional notification system for multi-vendor e-commerce platform.
    
    Supports various notification types, priority levels, read status tracking,
    soft delete functionality, and actionable notifications with rich metadata.
    
    Features:
    - Multiple notification types (orders, promotions, system alerts, etc.)
    - Priority-based notification ranking
    - Read/unread status with timestamp tracking
    - Soft delete for audit trail
    - Actionable notifications with custom buttons/links
    - Rich metadata storage via JSONField
    - Multi-tenant support (user-specific notifications)
    - Comprehensive audit fields
    """
    
    class NotificationType(models.TextChoices):
        """Notification categories for different business events."""
        NEW_ORDER = 'new_order', _('New Order')
        ORDER_STATUS_UPDATE = 'order_status_update', _('Order Status Update')
        ORDER_CANCELLED = 'order_cancelled', _('Order Cancelled')
        ORDER_DELIVERED = 'order_delivered', _('Order Delivered')
        PAYMENT_SUCCESS = 'payment_success', _('Payment Successful')
        PAYMENT_FAILED = 'payment_failed', _('Payment Failed')
        PASSWORD_RESET = 'password_reset', _('Password Reset')
        EMAIL_VERIFICATION = 'email_verification', _('Email Verification')
        PROMOTION = 'promotion', _('Promotion')
        FLASH_SALE = 'flash_sale', _('Flash Sale')
        NEW_MESSAGE = 'new_message', _('New Message')
        SYSTEM_ALERT = 'system_alert', _('System Alert')
        WISHLIST_UPDATE = 'wishlist_update', _('Wishlist Update')
        REVIEW_REMINDER = 'review_reminder', _('Review Reminder')
        STOCK_ALERT = 'stock_alert', _('Stock Alert')
        PRICE_DROP = 'price_drop', _('Price Drop')
        SHIPPING_UPDATE = 'shipping_update', _('Shipping Update')
        REFUND_PROCESSED = 'refund_processed', _('Refund Processed')
        ACCOUNT_UPDATE = 'account_update', _('Account Update')
        SECURITY_ALERT = 'security_alert', _('Security Alert')
        OTHER = 'other', _('Other')

    class NotificationLevel(models.TextChoices):
        """Priority levels for notification importance."""
        LOW = 'low', _('Low')
        INFO = 'info', _('Info')
        SUCCESS = 'success', _('Success')
        WARNING = 'warning', _('Warning')
        ERROR = 'error', _('Error')
        CRITICAL = 'critical', _('Critical')

    class NotificationStatus(models.TextChoices):
        """Notification processing status."""
        PENDING = 'pending', _('Pending')
        SENT = 'sent', _('Sent')
        DELIVERED = 'delivered', _('Delivered')
        READ = 'read', _('Read')
        FAILED = 'failed', _('Failed')

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID'),
        help_text=_('Unique identifier for the notification')
    )

    # User Relationships
    recipient = models.ForeignKey(
       settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Recipient'),
        help_text=_('The user who receives this notification'),
        db_index=True
    )
    
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name=_('Sender'),
        help_text=_('The user or system sending the notification')
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_notifications',
        verbose_name=_('User'),
        help_text=_('The user associated with this notification'),
        null=True,
        blank=True
    )

    # Related Objects
    orderId = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Order'),
        help_text=_('The order associated with this notification, if applicable'),
        null=True,
        blank=True,
        db_index=True
    )

    # Core Content
    title = models.CharField(
        max_length=255,
        verbose_name=_('Title'),
        help_text=_('The title of the notification'),
        db_index=True
    )
    
    message = models.TextField(
        verbose_name=_('Message'),
        help_text=_('The main content of the notification')
    )
    
    # Notification Metadata
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.OTHER,
        verbose_name=_('Notification Type'),
        help_text=_('The category of the notification'),
        db_index=True
    )
    
    level = models.CharField(
        max_length=10,
        choices=NotificationLevel.choices,
        default=NotificationLevel.INFO,
        verbose_name=_('Level'),
        help_text=_('The importance level of the notification'),
        db_index=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        verbose_name=_('Status'),
        help_text=_('Current status of the notification')
    )

    # Read Status
    isRead = models.BooleanField(
        default=False,
        verbose_name=_('Is Read'),
        help_text=_('Whether the user has read the notification'),
        db_index=True
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Read At'),
        help_text=_('Timestamp when the notification was read')
    )

    # Actionable Notifications
    action_text = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_('Action Text'),
        help_text=_('Text for the action button')
    )
    
    action_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Action URL'),
        help_text=_('URL for the action button')
    )
    
    link = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Link'),
        help_text=_('An optional URL to direct the user to')
    )

    # Priority and Metadata
    priority = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Priority'),
        help_text=_('Priority of the notification (higher = more important)'),
        db_index=True
    )
    
    source = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_('Source'),
        help_text=_('Source app or module that generated this notification')
    )
    
    extra_data = JSONField(
        blank=True,
        null=True,
        verbose_name=_('Extra Data'),
        help_text=_('Additional data for this notification (JSON format)')
    )

    # Soft Delete
    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_('Is Deleted'),
        help_text=_('Whether this notification has been soft deleted'),
        db_index=True
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Deleted At'),
        help_text=_('Timestamp when the notification was soft deleted')
    )

    # Audit Fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
        help_text=_('Timestamp when the notification was created'),
        db_index=True
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
        help_text=_('Timestamp when the notification was last updated')
    )

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'isRead']),
            models.Index(fields=['recipient', 'notification_type']),
            models.Index(fields=['recipient', 'level']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['notification_type', 'level']),
            models.Index(fields=['is_deleted', 'created_at']),
        ]
        permissions = [
            ("view_all_notifications", "Can view all notifications"),
            ("manage_notifications", "Can manage notifications"),
        ]

    def __str__(self):
        """String representation of the notification."""
        return f"Notification for {self.recipient.username}: {self.title}"

    def clean(self):
        """Validate the notification data."""
        super().clean()
        
        # Validate that action_text and action_url are provided together
        if bool(self.action_text) != bool(self.action_url):
            raise ValidationError({
                'action_text': 'Action text and action URL must be provided together.',
                'action_url': 'Action text and action URL must be provided together.'
            })
        
        # Validate priority range
        if self.priority < 0 or self.priority > 100:
            raise ValidationError({
                'priority': 'Priority must be between 0 and 100.'
            })

    def save(self, *args, **kwargs):
        """Override save to ensure data consistency."""
        self.full_clean()
        super().save(*args, **kwargs)

    def mark_as_read(self):
        """Mark the notification as read and set read timestamp."""
        if not self.isRead:
            self.isRead = True
            self.read_at = timezone.now()
            self.status = self.NotificationStatus.READ
            self.save(update_fields=['isRead', 'read_at', 'status'])

    def mark_as_unread(self):
        """Mark the notification as unread and clear read timestamp."""
        if self.isRead:
            self.isRead = False
            self.read_at = None
            self.status = self.NotificationStatus.DELIVERED
            self.save(update_fields=['isRead', 'read_at', 'status'])

    def soft_delete(self):
        """Soft delete the notification."""
        if not self.is_deleted:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """Restore a soft-deleted notification."""
        if self.is_deleted:
            self.is_deleted = False
            self.deleted_at = None
            self.save(update_fields=['is_deleted', 'deleted_at'])

    @property
    def is_actionable(self):
        """Check if the notification has an action."""
        return bool(self.action_text and self.action_url)

    @property
    def age_in_hours(self):
        """Get the age of the notification in hours."""
        if not self.created_at:
            return 0.0
        return (timezone.now() - self.created_at).total_seconds() / 3600

    @property
    def is_urgent(self):
        """Check if the notification is urgent (high priority or critical level)."""
        return self.priority >= 8 or self.level == self.NotificationLevel.CRITICAL

    def get_absolute_url(self):
        """Get the absolute URL for this notification."""
        from django.urls import reverse
        return reverse('notification-detail', kwargs={'pk': self.pk})

