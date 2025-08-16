import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import JSONField
from order.models import Order
from bank.models import Transaction, BankTransfer, BillPayment, VirtualCard

class NotificationType(models.TextChoices):
    # E-commerce and system events
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
    ESCALATION = 'escalation', _('Escalation')
    OTHER = 'other', _('Other')
    SMS = 'sms', _('Sms')
    EMAIL = 'email', _('Email')
    PUSH = 'push', _('Push')
    # Banking events
    BANK_TRANSACTION = 'bank_transaction', _('Bank Transaction')
    BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
    BILL_PAYMENT = 'bill_payment', _('Bill Payment')
    WALLET_CREDIT = 'wallet_credit', _('Wallet Credited')
    WALLET_DEBIT = 'wallet_debit', _('Wallet Debited')
    # Spend and Save specific events
    SPEND_AND_SAVE_ACTIVATION = 'spend_and_save_activation', _('Spend and Save Activation')
    SPEND_AND_SAVE_DEACTIVATION = 'spend_and_save_deactivation', _('Spend and Save Deactivation')
    AUTOMATIC_SAVE = 'automatic_save', _('Automatic Save')
    SAVINGS_MILESTONE = 'savings_milestone', _('Savings Milestone')
    INTEREST_CREDITED = 'interest_credited', _('Interest Credited')
    SAVINGS_WITHDRAWAL = 'savings_withdrawal', _('Savings Withdrawal')
    WEEKLY_SAVINGS_SUMMARY = 'weekly_savings_summary', _('Weekly Savings Summary')
    SAVINGS_GOAL_ACHIEVED = 'savings_goal_achieved', _('Savings Goal Achieved')
    # Target Saving specific events
    TARGET_SAVING_CREATED = 'target_saving_created', _('Target Saving Created')
    TARGET_SAVING_UPDATED = 'target_saving_updated', _('Target Saving Updated')
    TARGET_SAVING_COMPLETED = 'target_saving_completed', _('Target Saving Completed')
    TARGET_SAVING_DEPOSIT = 'target_saving_deposit', _('Target Saving Deposit')
    TARGET_SAVING_MILESTONE = 'target_saving_milestone', _('Target Saving Milestone')
    TARGET_SAVING_OVERDUE = 'target_saving_overdue', _('Target Saving Overdue')
    TARGET_SAVING_REMINDER = 'target_saving_reminder', _('Target Saving Reminder')
    TARGET_SAVING_WITHDRAWAL = 'target_saving_withdrawal', _('Target Saving Withdrawal')
    # Fixed Savings specific events
    FIXED_SAVINGS_CREATED = 'fixed_savings_created', _('Fixed Savings Created')
    FIXED_SAVINGS_ACTIVATED = 'fixed_savings_activated', _('Fixed Savings Activated')
    FIXED_SAVINGS_MATURED = 'fixed_savings_matured', _('Fixed Savings Matured')
    FIXED_SAVINGS_PAID_OUT = 'fixed_savings_paid_out', _('Fixed Savings Paid Out')
    FIXED_SAVINGS_INTEREST_CREDITED = 'fixed_savings_interest_credited', _('Fixed Savings Interest Credited')
    FIXED_SAVINGS_AUTO_RENEWAL = 'fixed_savings_auto_renewal', _('Fixed Savings Auto Renewal')
    FIXED_SAVINGS_MATURITY_REMINDER = 'fixed_savings_maturity_reminder', _('Fixed Savings Maturity Reminder')
    FIXED_SAVINGS_EARLY_WITHDRAWAL = 'fixed_savings_early_withdrawal', _('Fixed Savings Early Withdrawal')

class NotificationLevel(models.TextChoices):
    LOW = 'low', _('Low')
    INFO = 'info', _('Info')
    SUCCESS = 'success', _('Success')
    WARNING = 'warning', _('Warning')
    ERROR = 'error', _('Error')
    CRITICAL = 'critical', _('Critical')

class NotificationStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    SENT = 'sent', _('Sent')
    DELIVERED = 'delivered', _('Delivered')
    READ = 'read', _('Read')
    FAILED = 'failed', _('Failed')

class Notification(models.Model):
    """
    Professional notification system for multi-vendor e-commerce platform.
    Supports various notification types, priority levels, read status tracking,
    actionable notifications with rich metadata.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID'),
        help_text=_('Unique identifier for the notification')
    )
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
    # --- Banking references ---
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('Transaction'),
        help_text=_('The transaction associated with this notification, if applicable')
    )
    bank_transfer = models.ForeignKey(
        BankTransfer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('Bank Transfer'),
        help_text=_('The bank transfer associated with this notification, if applicable')
    )
    bill_payment = models.ForeignKey(
        BillPayment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('Bill Payment'),
        help_text=_('The bill payment associated with this notification, if applicable')
    )
    virtual_card = models.ForeignKey(
        VirtualCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('Virtual Card'),
        help_text=_('The virtual card associated with this notification, if applicable')
    )
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
    notification_type = models.CharField(
        max_length=35,
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
        ]
        permissions = [
            ("view_all_notifications", "Can view all notifications"),
            ("manage_notifications", "Can manage notifications"),
        ]
    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"
    def clean(self):
        super().clean()
        if bool(self.action_text) != bool(self.action_url):
            raise ValidationError({
                'action_text': 'Action text and action URL must be provided together.',
                'action_url': 'Action text and action URL must be provided together.'
            })
        if self.priority < 0 or self.priority > 100:
            raise ValidationError({
                'priority': 'Priority must be between 0 and 100.'
            })
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    def mark_as_read(self):
        if not self.isRead:
            self.isRead = True
            self.read_at = timezone.now()
            self.status = NotificationStatus.READ
            self.save(update_fields=['isRead', 'read_at', 'status'])
    def mark_as_unread(self):
        if self.isRead:
            self.isRead = False
            self.read_at = None
            self.status = NotificationStatus.DELIVERED
            self.save(update_fields=['isRead', 'read_at', 'status'])
    @property
    def is_actionable(self):
        return bool(self.action_text and self.action_url)
    @property
    def age_in_hours(self):
        if not self.created_at:
            return 0.0
        return (timezone.now() - self.created_at).total_seconds() / 3600
    @property
    def is_urgent(self):
        return self.priority >= 8 or self.level == NotificationLevel.CRITICAL
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('notification-detail', kwargs={'pk': self.pk})

# ---
# Example: Creating a banking notification
# from notification.models import Notification, NotificationType, NotificationLevel, NotificationStatus
# Notification.objects.create(
#     recipient=user,
#     title="Bank Transfer Successful",
#     message=f"Your transfer of NGN {amount} to {bank_name} ({account_number}) was successful.",
#     notification_type=NotificationType.BANK_TRANSFER,
#     level=NotificationLevel.SUCCESS,
#     status=NotificationStatus.PENDING,
#     bank_transfer=bank_transfer_instance,
#     extra_data={"amount": str(amount), "bank": bank_name, "account": account_number}
# )

