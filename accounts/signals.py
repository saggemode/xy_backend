from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile
from django.dispatch import Signal
import logging
from .models import UserSession

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

# Custom signals for user deletion
default_args = dict(providing_args=["user", "profile"])
pre_user_delete = Signal()
post_user_delete = Signal()

logger = logging.getLogger(__name__)

@receiver(pre_user_delete)
def log_pre_user_delete(sender, user, profile, **kwargs):
    logger.info(f"[AUDIT] About to delete user: {user.username} ({user.email}) with profile ID {profile.id}")

@receiver(post_user_delete)
def log_post_user_delete(sender, user, profile, **kwargs):
    logger.info(f"[AUDIT] Deleted user: {user.username} ({user.email}) with profile ID {profile.id}")


@receiver(post_user_delete)
def cleanup_user_sessions(sender, user, profile, **kwargs):
    UserSession.objects.filter(user=user).delete() 


