from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import UserProfile

class Command(BaseCommand):
    help = 'Delete expired, unverified users whose OTP has expired.'

    def handle(self, *args, **options):
        User = get_user_model()
        now = timezone.now()
        expired_profiles = UserProfile.objects.filter(is_verified=False, otp_expiry__lt=now)
        count = 0
        for profile in expired_profiles:
            user = profile.user
            user.delete()
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} expired unverified users')) 