from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
import uuid
import re
import hashlib
import secrets
from datetime import timedelta

class Address(models.Model):
    """
    Model to store user addresses with location information.
    Supports different types of addresses (home, office, etc.).
    """
    class AddressType(models.TextChoices):
        HOME = 'home', _('Home')
        OFFICE = 'office', _('Office')
        SCHOOL = 'school', _('School')
        MARKET = 'market', _('Market')
        OTHER = 'other', _('Other')
        BUSINESS = 'business', _('Business')
        MAILING = 'mailing', _('Mailing')

    # Unique identifier
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )

    # Location coordinates
    latitude = models.FloatField(
        verbose_name=_('Latitude'),
        help_text=_('Geographic latitude coordinate'),
        
    )
    longitude = models.FloatField(
        verbose_name=_('Longitude'),
        help_text=_('Geographic longitude coordinate'),
        
    )

    # Address details
    address = models.CharField(
        max_length=255,
        verbose_name=_('Address'),
        help_text=_('Full address including street, city, state, and postal code')
    )
    city = models.CharField(
        max_length=100,
        verbose_name=_('City'),
        help_text=_('City name')
    )
    state = models.CharField(
        max_length=100,
        verbose_name=_('State/Province'),
        help_text=_('State or province name')
    )
    postal_code = models.CharField(
        max_length=20,
        verbose_name=_('Postal Code'),
        help_text=_('Postal or ZIP code'),
        default='12345',
        validators=[
            RegexValidator(
                regex=r'^\d{5}(-\d{4})?$',
                message=_('Enter a valid postal code (e.g., 12345 or 12345-6789)')
            )
        ]
    )
    country = models.CharField(
        max_length=100,
        default='United States',
        verbose_name=_('Country'),
        help_text=_('Country name')
    )
    
    # Contact information
    phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message=_('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.')
            )
        ],
        verbose_name=_('Phone Number'),
        help_text=_('Contact phone number')
    )
    additional_phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message=_('Phone number must be entered in the format: "+999999999". Up to 15 digits allowed.')
            )
        ],
        verbose_name=_('Additional Phone'),
        help_text=_('Alternative contact phone number')
    )

    # Relationships and flags
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name=_('User'),
        help_text=_('User who owns this address')
    )
    address_type = models.CharField(
        max_length=10,
        choices=AddressType.choices,
        default=AddressType.HOME,
        verbose_name=_('Address Type'),
        help_text=_('Type of address (home, office, etc.)')
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Default Address'),
        help_text=_('Whether this is the user\'s default address')
    )



  
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
        help_text=_('When this address was created')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At'),
        help_text=_('When this address was last updated')
    )

    class Meta:
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')
        ordering = ['-is_default', '-created_at']
        unique_together = ['user', 'address', 'address_type']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['address_type']),
           
        ]

    def __str__(self):
        return f"{self.user.username}'s {self.address_type} address in {self.city}"

    def clean(self):
        """Validate the address data"""
       
        # Validate postal code format based on country
        if self.country == 'United States':
            if not re.match(r'^\d{5}(-\d{4})?$', self.postal_code):
                raise ValidationError({'postal_code': _('Invalid US postal code format')})

    def save(self, *args, **kwargs):
        """Override save to ensure only one default address per user"""
        self.full_clean()
        if self.is_default:
            # Set all other addresses of this user to non-default
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def full_address(self):
        """Return the complete formatted address"""
        return f"{self.address}, {self.city}, {self.state} {self.postal_code}, {self.country}"

 

    



class UserVerification(models.Model):
    """
    Model to store user verification information and OTP.
    Handles user verification status and OTP management.
    """
    class VerificationMethod(models.TextChoices):
        EMAIL = 'email', _('Email')
        PHONE = 'phone', _('Phone')
        TWO_FACTOR = '2fa', _('Two-Factor Authentication')
        BIOMETRIC = 'biometric', _('Biometric')
        SECURITY_QUESTIONS = 'security_questions', _('Security Questions')
        DOCUMENT_VERIFICATION = 'document', _('Document Verification')
        FACE_RECOGNITION = 'face', _('Face Recognition')
        VOICE_VERIFICATION = 'voice', _('Voice Verification')

    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        VERIFIED = 'verified', _('Verified')
        FAILED = 'failed', _('Failed')
        EXPIRED = 'expired', _('Expired')
        BLOCKED = 'blocked', _('Blocked')

    # Unique identifier
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='verifications',
        verbose_name=_('User'),
        help_text=_('User being verified')
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_('Verified Status'),
        help_text=_('Whether the user has been verified')
    )
    verification_method = models.CharField(
        max_length=20,
        choices=VerificationMethod.choices,
        default=VerificationMethod.EMAIL,
        verbose_name=_('Verification Method'),
        help_text=_('Method used for verification')
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        verbose_name=_('Verification Status'),
        help_text=_('Current status of verification')
    )
    otp = models.CharField(
        max_length=6,
        default='',
        verbose_name=_('OTP'),
        help_text=_('One-time password for verification')
    )
    otp_created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('OTP Created At'),
        help_text=_('When the OTP was created')
    )
    verification_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Verification Attempts'),
        help_text=_('Number of verification attempts made')
    )
    last_verification_attempt = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Verification Attempt'),
        help_text=_('When the last verification attempt was made')
    )
    max_attempts = models.PositiveIntegerField(
        default=3,
        verbose_name=_('Maximum Attempts'),
        help_text=_('Maximum number of verification attempts allowed')
    )
    is_blocked = models.BooleanField(
        default=False,
        verbose_name=_('Blocked'),
        help_text=_('Whether the user is blocked from verification attempts')
    )
    blocked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Blocked Until'),
        help_text=_('When the user can attempt verification again')
    )
    security_questions = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Security Questions'),
        help_text=_('Security questions and answers for verification')
    )
    document_verification = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Document Verification'),
        help_text=_('Document verification details')
    )
    biometric_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Biometric Data'),
        help_text=_('Biometric verification data')
    )
    verification_history = models.JSONField(
        default=list,
        verbose_name=_('Verification History'),
        help_text=_('History of verification attempts')
    )

    class Meta:
        verbose_name = _('User Verification')
        verbose_name_plural = _('User Verifications')
        ordering = ['-otp_created_at']
        indexes = [
            models.Index(fields=['user', 'is_verified']),
            models.Index(fields=['verification_method']),
            models.Index(fields=['is_blocked']),
            models.Index(fields=['verification_status'])
        ]

    def __str__(self):
        return f"{self.user.username}'s verification status"

    def is_otp_valid(self):
        """Check if the OTP is still valid (within 10 minutes)"""
        return (timezone.now() - self.otp_created_at).total_seconds() < 600  # 10 minutes

    def increment_attempts(self):
        """Increment verification attempts and handle blocking"""
        self.verification_attempts += 1
        self.last_verification_attempt = timezone.now()
        
        # Add to verification history
        history_entry = {
            'timestamp': timezone.now().isoformat(),
            'method': self.verification_method,
            'status': 'failed' if self.verification_attempts >= self.max_attempts else 'attempted'
        }
        self.verification_history.append(history_entry)
        
        if self.verification_attempts >= self.max_attempts:
            self.is_blocked = True
            self.blocked_until = timezone.now() + timezone.timedelta(hours=24)
            self.verification_status = self.VerificationStatus.BLOCKED
        
        self.save()

    def reset_attempts(self):
        """Reset verification attempts and unblock user"""
        self.verification_attempts = 0
        self.is_blocked = False
        self.blocked_until = None
        self.verification_status = self.VerificationStatus.PENDING
        self.save()

    def can_attempt_verification(self):
        """Check if user can attempt verification"""
        if not self.is_blocked:
            return True
        if self.blocked_until and timezone.now() > self.blocked_until:
            self.reset_attempts()
            return True
        return False

    def generate_new_otp(self):
        """Generate a new OTP and reset attempts"""
        self.otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        self.otp_created_at = timezone.now()
        self.verification_attempts = 0
        self.is_blocked = False
        self.blocked_until = None
        self.verification_status = self.VerificationStatus.PENDING
        self.save()
        return self.otp

    def verify_security_questions(self, answers):
        """Verify security questions"""
        if not self.security_questions:
            return False
        
        for question, answer in answers.items():
            if question not in self.security_questions or \
               self.security_questions[question].lower() != answer.lower():
                return False
        return True

    def verify_document(self, document_data):
        """Verify user document"""
        # Add document verification logic here
        self.document_verification = document_data
        self.verification_status = self.VerificationStatus.IN_PROGRESS
        self.save()
        return True

    def verify_biometric(self, biometric_data):
        """Verify biometric data"""
        # Add biometric verification logic here
        self.biometric_data = biometric_data
        self.verification_status = self.VerificationStatus.IN_PROGRESS
        self.save()
        return True

    def mark_as_verified(self):
        """Mark user as verified"""
        self.is_verified = True
        self.verification_status = self.VerificationStatus.VERIFIED
        self.verification_history.append({
            'timestamp': timezone.now().isoformat(),
            'method': self.verification_method,
            'status': 'verified'
        })
        self.save()

    def get_verification_summary(self):
        """Get verification summary"""
        return {
            'status': self.verification_status,
            'method': self.verification_method,
            'attempts': self.verification_attempts,
            'is_blocked': self.is_blocked,
            'blocked_until': self.blocked_until,
            'last_attempt': self.last_verification_attempt,
            'history': self.verification_history
        }
