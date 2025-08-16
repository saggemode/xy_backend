import uuid
import random
import string
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.hashers import make_password, check_password

class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = PhoneNumberField(unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expiry = models.DateTimeField(blank=True, null=True)
    notify_email = models.BooleanField(default=True, help_text='Receive notifications via email')
    notify_sms = models.BooleanField(default=False, help_text='Receive notifications via SMS')
    notify_push = models.BooleanField(default=False, help_text='Receive notifications via push')
    notify_in_app = models.BooleanField(default=True, help_text='Receive notifications in-app')
    fcm_token = models.CharField(max_length=255, blank=True, null=True, help_text='FCM device token for push notifications')
    transaction_pin = models.CharField(max_length=128, blank=True, null=True, help_text="Hashed transaction PIN")

    def set_transaction_pin(self, raw_pin):
        self.transaction_pin = make_password(raw_pin)
        self.save(update_fields=['transaction_pin'])

    def check_transaction_pin(self, raw_pin):
        return check_password(raw_pin, self.transaction_pin)
    
    def __str__(self):
        return f"{self.user.username} - {self.phone}"

class AuditLog(models.Model):
    """Audit log for tracking admin actions and security events."""
    ACTION_TYPES = [
        ('user_created', 'User Created'),
        ('user_updated', 'User Updated'),
        ('user_deleted', 'User Deleted'),
        ('user_verified', 'User Verified'),
        ('user_suspended', 'User Suspended'),
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('password_changed', 'Password Changed'),
        ('otp_sent', 'OTP Sent'),
        ('otp_verified', 'OTP Verified'),
        ('admin_action', 'Admin Action'),
        ('security_alert', 'Security Alert'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='low')
    
    # For tracking specific objects
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'action']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"

class SecurityAlert(models.Model):
    """Security alerts and notifications."""
    ALERT_TYPES = [
        ('suspicious_login', 'Suspicious Login'),
        ('multiple_failed_attempts', 'Multiple Failed Login Attempts'),
        ('unusual_activity', 'Unusual Activity'),
        ('system_breach', 'System Breach'),
        ('data_leak', 'Data Leak'),
        ('compliance_violation', 'Compliance Violation'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True)
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    title = models.CharField(max_length=200)
    description = models.TextField()
    affected_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.alert_type} - {self.severity}"

class UserSession(models.Model):
    """Track user sessions for security monitoring."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address} - {self.created_at}"

# --- KYC constants and choices ---
class KYCLevelChoices(models.TextChoices):
    TIER_1 = 'tier_1', _('Tier 1')
    TIER_2 = 'tier_2', _('Tier 2')
    TIER_3 = 'tier_3', _('Tier 3')

GOVT_ID_TYPE_CHOICES = [
    ('national_id', _('National ID Card')),
    ('voters_card', _('Voter\'s Card')),
    ('passport', _('International Passport')),
    ('drivers_license', _('Driver\'s License')),
]

class KYCProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bvn = models.CharField(max_length=11, unique=True, blank=True, null=True)
    nin = models.CharField(max_length=11, unique=True, blank=True, null=True)
    date_of_birth = models.DateField()
    state = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', _('Male')),
            ('female', _('Female')),
          
        ],
        blank=True, 
        null=True
    )
    lga = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField()
    telephone_number = models.CharField(max_length=15, blank=True, null=True)
    passport_photo = models.ImageField(upload_to="kyc/passport_photos/")
    selfie = models.ImageField(upload_to="kyc/selfies/")
    id_document = models.FileField(upload_to="kyc/ids/")
    kyc_level = models.CharField(
        max_length=10,
        choices=KYCLevelChoices.choices,
        default=KYCLevelChoices.TIER_1,
        verbose_name=_('KYC Level')
    )
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_kyc_profiles'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Tier upgrade tracking
    last_upgrade_check = models.DateTimeField(null=True, blank=True)
    upgrade_eligibility_score = models.IntegerField(default=0, help_text=_('Score based on user activity and compliance'))
    upgrade_requested = models.BooleanField(default=False, help_text=_('User has requested tier upgrade'))
    upgrade_request_date = models.DateTimeField(null=True, blank=True)
    
    govt_id_type = models.CharField(max_length=20, choices=GOVT_ID_TYPE_CHOICES, blank=True, null=True)
    govt_id_document = models.FileField(upload_to="kyc/govt_ids/", blank=True, null=True)
    proof_of_address = models.FileField(upload_to="kyc/proof_of_address/", blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('KYC Profile')
        verbose_name_plural = _('KYC Profiles')
    
    def clean(self):
        # ... (same as in bank/models.py)
        pass

    def can_upgrade_to_tier_2(self):
        """
        Check if user can upgrade to Tier 2.
        Requirements:
        - Must be currently on Tier 1
        - Must be approved
        - Must have BVN or NIN
        """
        if self.kyc_level != KYCLevelChoices.TIER_1:
            return False, f"Cannot upgrade to Tier 2. Current level is {self.get_kyc_level_display()}"
        
        if not self.is_approved:
            return False, "KYC must be approved before upgrading to Tier 2"
        
        if not self.bvn and not self.nin:
            return False, "BVN or NIN is required for Tier 2 upgrade"
        
        return True, "Eligible for Tier 2 upgrade"

    def can_upgrade_to_tier_3(self):
        """
        Check if user can upgrade to Tier 3.
        Requirements:
        - Must be currently on Tier 2
        - Must be approved
        - Must have both BVN and NIN
        - Must have additional documents
        """
        if self.kyc_level != KYCLevelChoices.TIER_2:
            return False, f"Cannot upgrade to Tier 3. Current level is {self.get_kyc_level_display()}. Must be on Tier 2 first."
        
        if not self.is_approved:
            return False, "KYC must be approved before upgrading to Tier 3"
        
        if not self.bvn or not self.nin:
            return False, "Both BVN and NIN are required for Tier 3 upgrade"
        
        if not self.govt_id_document or not self.proof_of_address:
            return False, "Government ID and proof of address are required for Tier 3 upgrade"
        
        return True, "Eligible for Tier 3 upgrade"

    def get_upgrade_requirements(self, target_tier):
        """
        Get requirements for upgrading to a specific tier.
        """
        if target_tier == KYCLevelChoices.TIER_2:
            requirements = {
                'current_tier': self.kyc_level,
                'target_tier': target_tier,
                'requirements': [
                    'Must be on Tier 1',
                    'KYC must be approved',
                    'BVN or NIN required',
                ],
                'current_status': {
                    'is_tier_1': self.kyc_level == KYCLevelChoices.TIER_1,
                    'is_approved': self.is_approved,
                    'has_bvn_or_nin': bool(self.bvn or self.nin),
                }
            }
        elif target_tier == KYCLevelChoices.TIER_3:
            requirements = {
                'current_tier': self.kyc_level,
                'target_tier': target_tier,
                'requirements': [
                    'Must be on Tier 2',
                    'KYC must be approved',
                    'Both BVN and NIN required',
                    'Government ID document required',
                    'Proof of address required',
                ],
                'current_status': {
                    'is_tier_2': self.kyc_level == KYCLevelChoices.TIER_2,
                    'is_approved': self.is_approved,
                    'has_bvn': bool(self.bvn),
                    'has_nin': bool(self.nin),
                    'has_govt_id': bool(self.govt_id_document),
                    'has_proof_of_address': bool(self.proof_of_address),
                }
            }
        else:
            requirements = {
                'error': f'Invalid target tier: {target_tier}'
            }
        
        return requirements

    def upgrade_to_tier_2(self):
        """
        Upgrade user to Tier 2 if eligible.
        """
        can_upgrade, message = self.can_upgrade_to_tier_2()
        if not can_upgrade:
            raise ValidationError(message)
        
        self.kyc_level = KYCLevelChoices.TIER_2
        self.save()
        return True, f"Successfully upgraded to Tier 2"

    def upgrade_to_tier_3(self):
        """
        Upgrade user to Tier 3 if eligible.
        """
        can_upgrade, message = self.can_upgrade_to_tier_3()
        if not can_upgrade:
            raise ValidationError(message)
        
        self.kyc_level = KYCLevelChoices.TIER_3
        self.save()
        return True, f"Successfully upgraded to Tier 3"

    def get_available_upgrades(self):
        """
        Get list of available tier upgrades for this user.
        """
        available_upgrades = []
        
        if self.kyc_level == KYCLevelChoices.TIER_1:
            can_upgrade, message = self.can_upgrade_to_tier_2()
            if can_upgrade:
                available_upgrades.append({
                    'tier': KYCLevelChoices.TIER_2,
                    'display_name': 'Tier 2',
                    'requirements': self.get_upgrade_requirements(KYCLevelChoices.TIER_2)
                })
        
        elif self.kyc_level == KYCLevelChoices.TIER_2:
            can_upgrade, message = self.can_upgrade_to_tier_3()
            if can_upgrade:
                available_upgrades.append({
                    'tier': KYCLevelChoices.TIER_3,
                    'display_name': 'Tier 3',
                    'requirements': self.get_upgrade_requirements(KYCLevelChoices.TIER_3)
                })
        
        return available_upgrades

    def get_tier_limits(self):
        """
        Get transaction and balance limits for current tier.
        """
        limits = {
            KYCLevelChoices.TIER_1: {
                'daily_transaction_limit': 50000,
                'max_balance_limit': 300000,
                'description': 'Basic tier with limited transactions'
            },
            KYCLevelChoices.TIER_2: {
                'daily_transaction_limit': 200000,
                'max_balance_limit': 500000,
                'description': 'Enhanced tier with moderate limits'
            },
            KYCLevelChoices.TIER_3: {
                'daily_transaction_limit': 5000000,
                'max_balance_limit': None,  # Unlimited
                'description': 'Premium tier with high limits'
            }
        }
        
        return limits.get(self.kyc_level, {})

    def get_daily_transaction_limit(self):
        """
        Get daily transaction limit for current tier.
        """
        limits = self.get_tier_limits()
        return limits.get('daily_transaction_limit', 0)

    def get_max_balance_limit(self):
        """
        Get maximum balance limit for current tier.
        """
        limits = self.get_tier_limits()
        return limits.get('max_balance_limit', 0)

    def can_transact_amount(self, amount):
        """
        Check if user can transact the given amount based on KYC level.
        """
        daily_limit = self.get_daily_transaction_limit()
        
        # Check if amount exceeds daily limit
        if daily_limit and amount > daily_limit:
            return False, f'Amount exceeds daily transaction limit of {daily_limit} for your KYC level.'
        
        # Check if user has completed required KYC level
        if not self.is_approved:
            return False, 'KYC profile not approved. Please complete KYC verification first.'
        
        return True, 'Transaction allowed.'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
