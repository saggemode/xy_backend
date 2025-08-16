import os
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import (
    Transaction, StaffProfile, TransactionApproval, CustomerEscalation, 
    StaffActivity, KYCProfile, BankTransfer, Wallet, generate_alternative_account_number,
    XySaveTransaction
)
from decimal import Decimal
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError
import logging
logger = logging.getLogger(__name__)
from django.core.mail import send_mail
import requests
from notification.models import Notification, NotificationType, NotificationLevel, NotificationStatus
from django.template import Template, Context
from twilio.rest import Client
from pyfcm import FCMNotification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import uuid

WEBHOOK_URL = 'https://your-webhook-endpoint.com/notify'  # Replace with your actual webhook URL


# Notification helpers
def notify_user_of_transfer(user, subject, message):
    if user.email:
        try:
            send_mail(
                subject,
                message,
                'no-reply@yourbank.com',
                [user.email],
                fail_silently=True,
            )
            logger.info(f"[Notification] Email sent to {user.email}: {subject}")
        except Exception as e:
            logger.error(f"[Notification] Failed to send email to {user.email}: {e}")

def send_webhook(event_type, data):
    try:
        response = requests.post(WEBHOOK_URL, json={'event': event_type, 'data': data}, timeout=5)
        logger.info(f"[Webhook] Sent event '{event_type}' to webhook. Status: {response.status_code}")
    except Exception as e:
        logger.error(f"[Webhook] Failed to send event '{event_type}': {e}")

# --- Notification channel helpers ---
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')
FCM_API_KEY = os.getenv('FCM_API_KEY')

# Twilio SMS
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None
# FCM
fcm = FCMNotification(api_key=FCM_API_KEY) if FCM_API_KEY else None
# Channels
channel_layer = get_channel_layer()

def send_sms_notification(user, message):
    if hasattr(user, 'profile') and user.profile.notify_sms and hasattr(user.profile, 'phone') and user.profile.phone and client:
        try:
            client.messages.create(
                body=message,
                from_=TWILIO_FROM_NUMBER,
                to=str(user.profile.phone)
            )
            logger.info(f"[SMS] Sent to {user.profile.phone}: {message}")
        except Exception as e:
            logger.error(f"[SMS] Failed to send to {user.profile.phone}: {e}")
    else:
        logger.info(f"[SMS] Would send to {getattr(user.profile, 'phone', None)}: {message}")

def send_push_notification(user, title, message):
    if hasattr(user, 'profile') and user.profile.notify_push and getattr(user.profile, 'fcm_token', None) and fcm:
        try:
            result = fcm.notify_single_device(
                registration_id=user.profile.fcm_token,
                message_title=title,
                message_body=message
            )
            logger.info(f"[Push] Sent to {user.username}: {result}")
        except Exception as e:
            logger.error(f"[Push] Failed to send to {user.username}: {e}")
    else:
        logger.info(f"[Push] Would send to {user.username}: {title} - {message}")

def broadcast_in_app_notification(user, notification):
    if hasattr(user, 'profile') and user.profile.notify_in_app and channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}',
                {
                    'type': 'notify',
                    'title': notification.title,
                    'message': notification.message,
                    'extra_data': notification.extra_data,
                }
            )
            logger.info(f"[In-App] Broadcasted to {user.username}: {notification.title}")
        except Exception as e:
            logger.error(f"[In-App] Failed to broadcast to {user.username}: {e}")
    else:
        logger.info(f"[In-App] Would broadcast to {user.username}: {notification.title}")

def render_notification_template(template_str, context_dict):
    template = Template(template_str)
    context = Context(context_dict)
    return template.render(context)
# --- End helpers ---


from model_utils import FieldTracker
from .models import StaffProfile

# Add this to the StaffProfile model
StaffProfile.add_to_class('tracker', FieldTracker(fields=['role', 'is_active', 'supervisor'])) 

@receiver(post_save, sender=KYCProfile)
def create_wallet_on_kyc_approval(sender, instance, created, **kwargs):
    """Create wallet automatically when KYC is approved."""
    if instance.is_approved:  # Create wallet when KYC is approved (new or updated)
        # Check if wallet already exists
        if not Wallet.objects.filter(user=instance.user).exists():
            # Use phone number as account number
            phone_number = instance.user.profile.phone
            if phone_number:
                # Remove country code and get last 10 digits
                phone_str = str(phone_number)
                if phone_str.startswith('+234'):
                    phone_str = phone_str[4:]  # Remove +234
                elif phone_str.startswith('234'):
                    phone_str = phone_str[3:]   # Remove 234
                # Ensure it's 10 digits
                if len(phone_str) >= 10:
                    account_number = phone_str[-10:]  # Take last 10 digits
                else:
                    # Pad with zeros if less than 10 digits
                    account_number = phone_str.zfill(10)
                # Create wallet
                Wallet.objects.create(
                    user=instance.user,
                    account_number=account_number,
                    alternative_account_number=generate_alternative_account_number()
                )

@receiver(post_save, sender=Transaction)
def set_balance_after(sender, instance, created, **kwargs):
    if created and instance.wallet:
        instance.balance_after = instance.wallet.balance
        instance.save(update_fields=['balance_after'])

