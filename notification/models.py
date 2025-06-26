import uuid
from django.db import models
from django.conf import settings
from order.models import Order
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Notification(models.Model):
    """
    Model to store user notifications.
    Supports different types, levels, and read status.
    """
    class NotificationType(models.TextChoices):
        NEW_ORDER = 'new_order', _('New Order')
        ORDER_STATUS_UPDATE = 'order_status_update', _('Order Status Update')
        PASSWORD_RESET = 'password_reset', _('Password Reset')
        PROMOTION = 'promotion', _('Promotion')
        NEW_MESSAGE = 'new_message', _('New Message')
        SYSTEM_ALERT = 'system_alert', _('System Alert')
        WISHLIST_UPDATE = 'wishlist_update', _('Wishlist Update')
        REVIEW_REMINDER = 'review_reminder', _('Review Reminder')
        OTHER = 'other', _('Other')

    class NotificationLevel(models.TextChoices):
        INFO = 'info', _('Info')
        SUCCESS = 'success', _('Success')
        WARNING = 'warning', _('Warning')
        ERROR = 'error', _('Error')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    orderId = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Order ID'),
        help_text=_('The order associated with this notification, if applicable.'),
        null=True,
        blank=True
    )

    userId = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_notifications',
        verbose_name=_('User ID'),
        help_text=_('The user associated with this notification.')
    )


    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Recipient'),
        help_text=_('The user who receives this notification.')
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name=_('Sender'),
        help_text=_('The user or system sending the notification.')
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_('Title'),
        help_text=_('The title of the notification.')
    )
    message = models.TextField(
        verbose_name=_('Message'),
        help_text=_('The main content of the notification.')
    )
    link = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Link'),
        help_text=_('An optional URL to direct the user to.')
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.OTHER,
        verbose_name=_('Notification Type'),
        help_text=_('The category of the notification.')
    )
    level = models.CharField(
        max_length=10,
        choices=NotificationLevel.choices,
        default=NotificationLevel.INFO,
        verbose_name=_('Level'),
        help_text=_('The importance level of the notification (e.g., info, warning).')
    )
    isRead = models.BooleanField(
        default=False,
        verbose_name=_('Is Read'),
        help_text=_('Whether the user has read the notification.')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        blank=True,
        verbose_name=_('Updated At'),
        help_text=_('The timestamp when the notification was last updated.')
    )   
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
        help_text=_('The timestamp when the notification was created.')
    )

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'isRead']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"

    def mark_as_read(self):
        """Marks the notification as read."""
        if not self.isRead:
            self.isRead = True
            self.save(update_fields=['isRead'])

    def mark_as_unread(self):
        """Marks the notification as unread."""
        if self.isRead:
            self.isRead = False
            self.save(update_fields=['isRead'])
