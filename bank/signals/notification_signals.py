import logging
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from twilio.rest import Client
from pyfcm import FCMNotification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from bank.models import CustomerEscalation, StaffActivity, Transaction, BankTransfer
from notification.models import Notification, NotificationType, NotificationLevel, NotificationStatus

logger = logging.getLogger(__name__)

# Initialize Twilio client for SMS
try:
    twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
except:
    twilio_client = None
    logger.warning("Twilio not configured - SMS notifications disabled")

# Initialize FCM for push notifications
try:
    fcm_client = FCMNotification(api_key=settings.FCM_API_KEY)
except:
    fcm_client = None
    logger.warning("FCM not configured - push notifications disabled")


def send_sms_notification(phone_number, message):
    """Send SMS notification using Twilio."""
    if not twilio_client or not hasattr(settings, 'TWILIO_PHONE_NUMBER'):
        logger.warning("SMS notification skipped - Twilio not configured")
        return False
    
    try:
        message = twilio_client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        logger.info(f"SMS sent successfully: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"SMS sending failed: {str(e)}")
        return False


def send_push_notification(user, title, message, data=None):
    """Send push notification using FCM."""
    if not fcm_client:
        logger.warning("Push notification skipped - FCM not configured")
        return False
    
    try:
        # Get user's FCM token (you'll need to implement this)
        fcm_token = getattr(user, 'fcm_token', None)
        if not fcm_token:
            logger.warning(f"No FCM token for user {user.id}")
            return False
        
        result = fcm_client.notify_single_device(
            registration_id=fcm_token,
            message_title=title,
            message_body=message,
            data_message=data or {}
        )
        logger.info(f"Push notification sent: {result}")
        return True
    except Exception as e:
        logger.error(f"Push notification failed: {str(e)}")
        return False


def send_websocket_notification(user, notification_data):
    """Send real-time notification via WebSocket."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",
            {
                "type": "notification.message",
                "message": notification_data
            }
        )
        logger.info(f"WebSocket notification sent to user {user.id}")
        return True
    except Exception as e:
        logger.error(f"WebSocket notification failed: {str(e)}")
        return False


@receiver(post_save, sender=Transaction)
def handle_transaction_notifications(sender, instance, created, **kwargs):
    """Handle notifications for all transaction types."""
    if not created:
        return

    logger.info(f"Creating comprehensive notifications for transaction {instance.id} - type: {instance.type}")

    # Get user details
    user = instance.wallet.user
    user_full_name = user.get_full_name() or user.username or user.email
    
    # Determine notification content based on transaction type
    if instance.type == 'debit':
        title = f"Money Sent: {instance.amount}"
        message = f"Your transfer of {instance.amount} to {instance.description} was successful. Reference: {instance.reference}"
        notification_type = NotificationType.WALLET_DEBIT
        email_subject = f"Transaction {instance.status.title()}: {instance.reference}"
        is_credit = False
    elif instance.type == 'credit':
        sender_name = instance.receiver.user.get_full_name() if instance.receiver else "Unknown"
        title = f"Money Received: {instance.amount}"
        message = f"You received {instance.amount} from {sender_name}. Reference: {instance.reference}"
        notification_type = NotificationType.WALLET_CREDIT
        email_subject = f"You received a transfer: {instance.reference}"
        is_credit = True
    else:
        # Handle other transaction types
        title = f"Transaction: {instance.amount}"
        message = f"Your {instance.type} transaction of {instance.amount} was {instance.status}. Reference: {instance.reference}"
        notification_type = NotificationType.BANK_TRANSACTION
        email_subject = f"Transaction {instance.status.title()}: {instance.reference}"
        is_credit = False

    # Create in-app notification
    notification = Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        level=NotificationLevel.SUCCESS,
        status=NotificationStatus.SENT,
        transaction=instance,
        source='bank',
        extra_data={
            'amount': str(instance.amount),
            'reference': instance.reference,
            'balance_after': str(instance.balance_after),
            'transaction_type': instance.type,
            'is_credit': is_credit
        }
    )
    logger.info(f"Created {instance.type} notification for user: {user.email}")

    # Send email notification
    try:
        context = {
            'subject': email_subject,
            'user_full_name': user_full_name,
            'amount': instance.amount,
            'currency': instance.currency,
            'description': instance.description,
            'status': instance.status.title(),
            'reference': instance.reference,
            'type': instance.type.title(),
            'channel': instance.channel.title(),
            'balance_after': instance.balance_after,
            'is_credit': is_credit,
            'sender_name': instance.receiver.user.get_full_name() if instance.receiver else '',
        }
        
        html_message = render_to_string('bank/transaction_email.html', context)
        plain_message = (
            f"Dear {user_full_name},\n\n"
            f"Your transaction of {context['amount']} {context['currency']} "
            f"({context['description']}) is now '{context['status']}'.\n\n"
            f"Reference: {context['reference']}\n"
            f"Type: {context['type']}\n"
            f"Channel: {context['channel']}\n"
            f"Balance after transaction: {context['balance_after']}\n\n"
            "Thank you for banking with us."
        )
        
        send_mail(
            email_subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=True,
        )
        logger.info(f"Email sent to: {user.email}")
    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}")

    # Send SMS notification (if phone number exists)
    try:
        # Check if user has a profile with phone number
        if hasattr(user, 'profile') and hasattr(user.profile, 'phone') and user.profile.phone:
            sms_message = f"{title}: {message}"
            send_sms_notification(str(user.profile.phone), sms_message)
        else:
            logger.info(f"No phone number found for user {user.id} - SMS skipped")
    except Exception as e:
        logger.error(f"SMS sending failed: {str(e)}")

    # Send push notification
    try:
        send_push_notification(user, title, message, {
            'transaction_id': instance.id,
            'reference': instance.reference,
            'amount': str(instance.amount),
            'type': instance.type
        })
    except Exception as e:
        logger.error(f"Push notification failed: {str(e)}")

    # Send WebSocket notification
    try:
        send_websocket_notification(user, {
            'id': str(notification.id),
            'title': title,
            'message': message,
            'type': notification_type,
            'created_at': notification.created_at.isoformat()
        })
    except Exception as e:
        logger.error(f"WebSocket notification failed: {str(e)}")


@receiver(post_save, sender=CustomerEscalation)
def handle_escalation_status_change(sender, instance, created, **kwargs):
    """Handle escalation status changes and send notifications."""
    if created:
        # Log staff activity
        StaffActivity.objects.create(
            staff=instance.created_by,
            activity_type='escalation_created',
            description=f'Created escalation: {instance.subject}',
            related_object=instance
        )
        
        # Send notification to the creator
        Notification.objects.create(
            recipient=instance.created_by,
            title="Escalation Created",
            message=f"Your escalation '{instance.subject}' has been created and is being reviewed.",
            notification_type=NotificationType.ESCALATION,
            level=NotificationLevel.INFO,
            status=NotificationStatus.SENT,
            source='bank',
            extra_data={
                'escalation_id': instance.id,
                'subject': instance.subject,
                'priority': instance.priority
            }
        )
        
        # Send email to creator
        try:
            send_mail(
                "Escalation Created",
                f"Your escalation '{instance.subject}' has been created and is being reviewed.",
                settings.DEFAULT_FROM_EMAIL,
                [instance.created_by.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Escalation email failed: {str(e)}")
            
    else:
        # Handle status changes
        if instance.status == 'resolved' and instance.resolved_at is None:
            instance.resolved_at = timezone.now()
            instance.save(update_fields=['resolved_at'])
            
            if instance.assigned_to:
                # Log staff activity
                StaffActivity.objects.create(
                    staff=instance.assigned_to,
                    activity_type='escalation_resolved',
                    description=f'Resolved escalation: {instance.subject}',
                    related_object=instance
                )
                
                # Send notification to assigned staff
                Notification.objects.create(
                    recipient=instance.assigned_to,
                    title="Escalation Resolved",
                    message=f"The escalation '{instance.subject}' assigned to you has been resolved.",
                    notification_type=NotificationType.ESCALATION,
                    level=NotificationLevel.SUCCESS,
                    status=NotificationStatus.SENT,
                    source='bank',
                    extra_data={
                        'escalation_id': instance.id,
                        'subject': instance.subject,
                        'resolved_at': instance.resolved_at.isoformat()
                    }
                )
                
                # Send email to assigned staff
                try:
                    send_mail(
                        "Escalation Resolved",
                        f"The escalation '{instance.subject}' assigned to you has been resolved.",
                        settings.DEFAULT_FROM_EMAIL,
                        [instance.assigned_to.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.error(f"Escalation resolution email failed: {str(e)}")


@receiver(post_save, sender=BankTransfer)
def handle_bank_transfer_notifications(sender, instance, created, **kwargs):
    """Handle notifications for bank transfer status changes."""
    if not created:
        # Handle status changes for existing transfers
        if instance.status == 'completed':
            # Send completion notification
            Notification.objects.create(
                recipient=instance.user,
                title="Transfer Completed",
                message=f"Your transfer of {instance.amount} to {instance.account_number} has been completed successfully.",
                notification_type=NotificationType.BANK_TRANSFER,
                level=NotificationLevel.SUCCESS,
                status=NotificationStatus.SENT,
                bank_transfer=instance,
                source='bank',
                extra_data={
                    'amount': str(instance.amount),
                    'account_number': instance.account_number,
                    'reference': instance.reference
                }
            )
        elif instance.status == 'failed':
            # Send failure notification
            Notification.objects.create(
                recipient=instance.user,
                title="Transfer Failed",
                message=f"Your transfer of {instance.amount} to {instance.account_number} has failed. Please contact support.",
                notification_type=NotificationType.BANK_TRANSFER,
                level=NotificationLevel.ERROR,
                status=NotificationStatus.SENT,
                bank_transfer=instance,
                source='bank',
                extra_data={
                    'amount': str(instance.amount),
                    'account_number': instance.account_number,
                    'reference': instance.reference,
                    'failure_reason': instance.failure_reason
                }
            ) 