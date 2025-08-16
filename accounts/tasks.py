import logging
from django.core.mail import mail_admins
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import UserProfile
from .signals import pre_user_delete, post_user_delete

logger = logging.getLogger(__name__)

def delete_expired_unverified_users():
    User = get_user_model()
    now = timezone.now()
    expired_profiles = UserProfile.objects.filter(is_verified=False, otp_expiry__lt=now)
    count = 0
    deleted_users = []
    error_users = []
    for profile in expired_profiles:
        user = profile.user
        try:
            pre_user_delete.send(sender=User, user=user, profile=profile)
            logger.info(f"Deleting expired unverified user: {user.username} ({user.email})")
            user.delete()
            post_user_delete.send(sender=User, user=user, profile=profile)
            deleted_users.append(f"{user.username} ({user.email})")
            count += 1
        except Exception as e:
            logger.error(f"Error deleting user {user.username} ({user.email}): {str(e)}")
            error_users.append(f"{user.username} ({user.email}): {str(e)}")
    if count > 0 or error_users:
        message = ""
        if deleted_users:
            message += "The following users were deleted:\n" + "\n".join(deleted_users) + "\n\n"
        if error_users:
            message += "Errors occurred for the following users:\n" + "\n".join(error_users)
        mail_admins(
            "Expired Unverified Users Deleted (with errors)" if error_users else "Expired Unverified Users Deleted",
            message
        )
        logger.info(f"Deleted {count} expired unverified users. Errors: {len(error_users)}. Admins notified.")
    else:
        logger.info("No expired unverified users to delete.")
    return f"Deleted {count} expired unverified users. Errors: {len(error_users)}"
