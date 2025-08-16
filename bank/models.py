import uuid
import logging
import random
import string
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from djmoney.models.fields import MoneyField
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime
from djmoney.money import Money
from .constants import FraudFlag, SecurityLevel, TransferType, TransferStatus, IPWhitelistStatus, DeviceFingerprint
from django.contrib.auth import get_user_model
User = get_user_model()
import math

# Set up logger
logger = logging.getLogger(__name__)

# Add this BaseAbstractModel class
class BaseAbstractModel(models.Model):
    """
    Abstract base model that provides common fields and functionality
    for all bank models.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Override save to ensure updated_at is set on every save."""
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_or_create_with_defaults(cls, defaults=None, **kwargs):
        """
        A helper method to get or create an object with default values.
        Similar to get_or_create but with better default handling.
        """
        try:
            obj = cls.objects.get(**kwargs)
            return obj, False
        except cls.DoesNotExist:
            if defaults:
                kwargs.update(defaults)
            obj = cls.objects.create(**kwargs)
            return obj, True

class GeneralStatusChoices(models.TextChoices):
    DRAFT = 'draft', _('Draft')
    PENDING = 'pending', _('Pending')
    PROCESSING = 'processing', _('Processing')
    ACTIVE = 'active', _('Active')
    SUSPENDED = 'suspended', _('Suspended')
    CLOSED = 'closed', _('Closed')
    SUCCESS = 'success', _('Success')
    SUCCESSFUL = 'successful', _('Successful')
    FAILED = 'failed', _('Failed')
    COMPLETED = 'completed', _('Completed')
    BLOCKED = 'blocked', _('Blocked')
    CREDIT = 'credit', _('Credit')
    DEBIT = 'debit', _('Debit')
    TRANSFER = 'transfer', _('Transfer')
    DEPOSIT = 'deposit', _('Deposit')
    BILL = 'bill', _('Bill Payment')

def generate_alternative_account_number():
    """Generate a unique 10-digit alternative account number."""
    while True:
        # Generate a 10-digit number
        number = ''.join(random.choices(string.digits, k=10))
        # Ensure it doesn't start with 0
        if not number.startswith('0'):
            # Check if it's unique
            if not Wallet.objects.filter(alternative_account_number=number).exists():
                return number

# Remove KYCProfile and related constants from this file.
# Update any references to import from accounts.models instead.
from accounts.models import KYCProfile, KYCLevelChoices

GOVT_ID_TYPE_CHOICES = [
    ('national_id', _('National ID Card')),
    ('voters_card', _('Voter\'s Card')),
    ('passport', _('International Passport')),
    ('drivers_license', _('Driver\'s License')),
]

class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=10, unique=True)
    alternative_account_number = models.CharField(max_length=10, unique=True)
    balance = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    currency = models.CharField(max_length=5, default="NGN")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Wallet')
        verbose_name_plural = _('Wallets')
    
    def __str__(self):
        return f"Wallet - {self.user.username} ({self.account_number})"
    
    def save(self, *args, **kwargs):
        # Generate alternative account number if not provided
        if not self.alternative_account_number:
            self.alternative_account_number = generate_alternative_account_number()
        
        # Validate balance against KYC level limits
        try:
            kyc_profile = KYCProfile.objects.get(user=self.user)
            # TODO: Implement balance validation logic if needed
            # can_have_balance, message = kyc_profile.can_have_balance(self.balance)
            # if not can_have_balance:
            #     raise ValidationError(message)
        except KYCProfile.DoesNotExist:
            # If no KYC profile, allow the save (wallet might be created before KYC)
            pass
        
        super().save(*args, **kwargs)

class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    receiver = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name='received_transactions',
        null=True, blank=True, help_text=_('Receiver wallet for transfers (null for non-transfer transactions)')
    )
    reference = models.CharField(max_length=100, unique=True, blank=True)
  
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    type = models.CharField(
        max_length=10,
        choices=[
            (GeneralStatusChoices.CREDIT, _('Credit')),
            (GeneralStatusChoices.DEBIT, _('Debit')),
        ]
    )
    channel = models.CharField(
        max_length=20,
        choices=[
            (GeneralStatusChoices.TRANSFER, _('Transfer')),
            (GeneralStatusChoices.DEPOSIT, _('Deposit')),
            (GeneralStatusChoices.BILL, _('Bill Payment')),
        ]
    )
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=[
            (GeneralStatusChoices.SUCCESS, _('Success')),
            (GeneralStatusChoices.PENDING, _('Pending')),
            (GeneralStatusChoices.FAILED, _('Failed')),
        ]
    )
    balance_after = MoneyField(max_digits=19, decimal_places=4, null=True, blank=True, default_currency='NGN', default=0.00, help_text=_('Wallet balance after this transaction'))
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reversals', help_text=_('Original transaction if this is a reversal/refund'))
    currency = models.CharField(max_length=5, default='NGN', help_text=_('Transaction currency'))
    # Generic relation to link to BankTransfer, BillPayment, etc.
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=36, null=True, blank=True)  # Changed to CharField to support UUID
    related_object = GenericForeignKey('content_type', 'object_id')
    # Metadata for extensibility
    metadata = models.JSONField(null=True, blank=True, help_text=_('Extra metadata for this transaction'))
    class Meta:
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        ordering = ['-timestamp']
    def __str__(self):
        return f"Transaction - {self.reference} ({self.amount} {self.currency})"

    def save(self, *args, **kwargs):
        if not self.reference:
            date_str = datetime.now().strftime('%Y%m%d')
            time_str = datetime.now().strftime('%H%M%S')
            unique_part = uuid.uuid4().hex[:6].upper()
            # Include wallet account number for better traceability
            account_suffix = self.wallet.account_number[-4:] if self.wallet else '0000'
            self.reference = f"TX-{date_str}-{time_str}-{account_suffix}-{unique_part}"
        super().save(*args, **kwargs)

class BankTransfer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10, blank=True, null=True, help_text=_('Recipient bank code'))
    account_number = models.CharField(max_length=10)
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    fee = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    vat = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    levy = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    reference = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            (GeneralStatusChoices.PENDING, _('Pending')),
            (GeneralStatusChoices.PROCESSING, _('Processing')),
            (GeneralStatusChoices.SUCCESSFUL, _('Successful')),
            (GeneralStatusChoices.COMPLETED, _('Completed')),
            (GeneralStatusChoices.FAILED, _('Failed')),
        ],
        default=GeneralStatusChoices.PENDING,
        help_text=_('Transfer status: Pending, Processing, Successful, Completed, or Failed')
    )
    transfer_type = models.CharField(
        max_length=10,
        choices=[('intra', 'Intra-bank'), ('inter', 'Inter-bank')],
        default='inter',
        help_text=_('Type of transfer: intra-bank (internal) or inter-bank (external)')
    )
    description = models.CharField(max_length=255, blank=True, null=True, help_text=_('Optional description of the transfer'))
    failure_reason = models.TextField(blank=True, null=True, help_text=_('Reason for transfer failure if status is Failed'))
    requires_approval = models.BooleanField(default=False, help_text=_('Whether this transfer requires staff approval'))
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_transfers',
        help_text=_('Staff member who approved this transfer')
    )
    approved_at = models.DateTimeField(null=True, blank=True, help_text=_('When the transfer was approved'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    nibss_reference = models.CharField(max_length=64, blank=True, null=True, help_text=_('NIBSS transaction reference'))
    
    # Enhanced Security & Fraud Detection Fields
    idempotency_key = models.CharField(max_length=64, unique=True, blank=True, null=True, help_text=_('Idempotency key to prevent duplicate transfers'))
    requires_2fa = models.BooleanField(default=False, help_text=_('Whether this transfer requires 2FA'))
    two_fa_verified = models.BooleanField(default=False, help_text=_('Whether 2FA has been verified'))
    two_fa_code = models.CharField(max_length=6, blank=True, null=True, help_text=_('2FA verification code'))
    two_fa_expires_at = models.DateTimeField(null=True, blank=True, help_text=_('When 2FA code expires'))
    
    # Fraud Detection Fields
    fraud_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text=_('Fraud risk score (0-100)'))
    fraud_flags = models.JSONField(default=dict, blank=True, help_text=_('Fraud detection flags'))
    is_suspicious = models.BooleanField(default=False, help_text=_('Whether transfer was flagged as suspicious'))
    reviewed_by_fraud_team = models.BooleanField(default=False, help_text=_('Whether fraud team has reviewed'))
    
    # Device & Location Tracking
    device_fingerprint = models.CharField(max_length=255, blank=True, null=True, help_text=_('Device fingerprint for security'))
    ip_address = models.GenericIPAddressField(blank=True, null=True, help_text=_('IP address of transfer request'))
    user_agent = models.TextField(blank=True, null=True, help_text=_('User agent string'))
    location_data = models.JSONField(default=dict, blank=True, help_text=_('Geographic location data'))
    
    # Retry & Circuit Breaker Fields
    retry_count = models.PositiveIntegerField(default=0, help_text=_('Number of retry attempts'))
    max_retries = models.PositiveIntegerField(default=3, help_text=_('Maximum retry attempts'))
    last_retry_at = models.DateTimeField(null=True, blank=True, help_text=_('Last retry attempt timestamp'))
    circuit_breaker_tripped = models.BooleanField(default=False, help_text=_('Whether circuit breaker is tripped'))
    
    # Scheduled & Recurring Transfer Fields
    is_scheduled = models.BooleanField(default=False, help_text=_('Whether this is a scheduled transfer'))
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text=_('When to execute scheduled transfer'))
    is_recurring = models.BooleanField(default=False, help_text=_('Whether this is a recurring transfer'))
    recurring_pattern = models.CharField(max_length=50, blank=True, null=True, help_text=_('Recurring pattern (daily, weekly, monthly)'))
    parent_transfer = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='recurring_transfers', help_text=_('Parent transfer for recurring transfers'))
    
    # Bulk Transfer Fields
    is_bulk = models.BooleanField(default=False, help_text=_('Whether this is part of a bulk transfer'))
    bulk_transfer_id = models.UUIDField(null=True, blank=True, help_text=_('ID of the bulk transfer group'))
    bulk_index = models.PositiveIntegerField(null=True, blank=True, help_text=_('Index in bulk transfer sequence'))
    
    # Escrow Fields
    is_escrow = models.BooleanField(default=False, help_text=_('Whether this is an escrow transfer'))
    escrow_release_conditions = models.JSONField(default=dict, blank=True, help_text=_('Conditions for escrow release'))
    escrow_expires_at = models.DateTimeField(null=True, blank=True, help_text=_('When escrow expires'))
    
    # Enhanced Status Tracking
    processing_started_at = models.DateTimeField(null=True, blank=True, help_text=_('When processing started'))
    processing_completed_at = models.DateTimeField(null=True, blank=True, help_text=_('When processing completed'))
    external_service_response = models.JSONField(default=dict, blank=True, help_text=_('Response from external service'))
    
    # Metadata for extensibility
    metadata = models.JSONField(default=dict, blank=True, help_text=_('Additional metadata'))
    
    class Meta:
        verbose_name = _('Bank Transfer')
        verbose_name_plural = _('Bank Transfers')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', 'created_at']),
            models.Index(fields=['account_number', 'bank_code']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['bulk_transfer_id', 'bulk_index']),
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['fraud_score']),
        ]
    
    def __str__(self):
        return f"Bank Transfer - {self.reference} ({self.amount})"

    def save(self, *args, **kwargs):
        if not self.reference:
            date_str = datetime.now().strftime('%Y%m%d')
            time_str = datetime.now().strftime('%H%M%S')
            unique_part = uuid.uuid4().hex[:6].upper()
            # Include user's account number for better traceability
            account_suffix = self.user.wallet.account_number[-4:] if hasattr(self.user, 'wallet') else '0000'
            self.reference = f"BT-{date_str}-{time_str}-{account_suffix}-{unique_part}"
        super().save(*args, **kwargs)

    def mark_as_pending(self, reason="Transfer submitted for processing"):
        """Mark transfer as pending with optional reason."""
        self.status = GeneralStatusChoices.PENDING
        if reason:
            self.failure_reason = reason
        self.save(update_fields=['status', 'failure_reason', 'updated_at'])

    def mark_as_completed(self, approved_by=None):
        """Mark transfer as completed."""
        self.status = GeneralStatusChoices.COMPLETED
        if approved_by:
            self.approved_by = approved_by
            self.approved_at = timezone.now()
        self.failure_reason = None  # Clear any previous failure reason
        self.save(update_fields=['status', 'approved_by', 'approved_at', 'failure_reason', 'updated_at'])

    def mark_as_failed(self, reason, error_code=None, technical_details=None):
        """Mark transfer as failed with detailed reason and tracking information."""
        self.status = GeneralStatusChoices.FAILED
        self.failure_reason = reason
        
        # Update processing completed timestamp
        self.processing_completed_at = timezone.now()
        
        self.save(update_fields=[
            'status', 'failure_reason', 'processing_completed_at', 'updated_at'
        ])
        
        # Create or update detailed failure record
        try:
            # Determine error category based on error code
            error_category_map = {
                'INSUFFICIENT_FUNDS': 'business_logic',
                'SELF_TRANSFER_ATTEMPT': 'validation',
                'WALLET_NOT_FOUND': 'business_logic',
                'PROCESSING_ERROR': 'technical',
                'DATABASE_ERROR': 'technical',
                'VALIDATION_ERROR': 'validation',
                'EXTERNAL_SERVICE_ERROR': 'external_service',
                'FRAUD_DETECTION': 'fraud_detection',
                'LIMIT_EXCEEDED': 'business_logic',
                'KYC_REQUIRED': 'business_logic',
            }
            
            error_category = error_category_map.get(error_code, 'technical')
            
            # Get request information if available
            request = getattr(self, '_request', None)
            user_agent = ''
            ip_address = None
            
            if request:
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                ip_address = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0]
            
            # Check if a TransferFailure record already exists for this transfer
            failure_data = {
                'error_code': error_code or 'GENERAL_FAILURE',
                'error_category': error_category,
                'failure_reason': reason,
                'technical_details': technical_details or {},
                'user_id': self.user.id,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'transfer_amount': self.amount,
                'recipient_account': self.account_number,
                'recipient_bank_code': getattr(self, 'bank_code', None),
                'processing_duration': (
                    (self.processing_completed_at - self.created_at).total_seconds() 
                    if self.processing_completed_at and self.created_at else None
                )
            }
            
            # Use get_or_create to avoid duplicate records
            TransferFailure.objects.update_or_create(
                transfer=self,
                defaults=failure_data
            )
        except Exception as e:
            # Log the error but don't fail the main operation
            logger.error(f"Failed to create TransferFailure record: {str(e)}")
        
        # Log the failure for monitoring
        logger.error(f"Transfer {self.id} failed: {reason} (Code: {error_code})")
        
        return self

    def requires_staff_approval(self):
        """Check if transfer requires staff approval based on amount."""
        # Define approval thresholds (can be moved to settings)
        APPROVAL_THRESHOLDS = {
            'tier_1': 50000,  # 50k for tier 1
            'tier_2': 500000,  # 500k for tier 2
            'tier_3': 5000000,  # 5M for tier 3
        }
        
        try:
            kyc_profile = self.user.kycprofile
            threshold = APPROVAL_THRESHOLDS.get(kyc_profile.kyc_level, 50000)
            return self.amount > threshold
        except:
            # Default to requiring approval for amounts over 50k
            return self.amount > 50000

    def can_be_processed(self):
        """Check if transfer can be processed."""
        return self.status == GeneralStatusChoices.PENDING and not self.requires_approval

    def get_status_display_with_reason(self):
        """Get status display with failure reason if applicable."""
        status_display = self.get_status_display()
        if self.status == GeneralStatusChoices.FAILED and self.failure_reason:
            return f"{status_display} - {self.failure_reason}"
        return status_display

class BillPayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=50)  # e.g., MTN, DSTV, PHCN
    account_or_meter = models.CharField(max_length=50)
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    status = models.CharField(
        max_length=10,
        choices=[
            (GeneralStatusChoices.SUCCESS, _('Success')),
            (GeneralStatusChoices.FAILED, _('Failed')),
            (GeneralStatusChoices.PENDING, _('Pending')),
        ]
    )
    reference = models.CharField(max_length=100, unique=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Bill Payment')
        verbose_name_plural = _('Bill Payments')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Bill Payment - {self.reference} ({self.amount})"

    def save(self, *args, **kwargs):
        if not self.reference:
            date_str = datetime.now().strftime('%Y%m%d')
            time_str = datetime.now().strftime('%H%M%S')
            unique_part = uuid.uuid4().hex[:6].upper()
            account_suffix = self.user.wallet.account_number[-4:] if hasattr(self.user, 'wallet') else '0000'
            self.reference = f"BP-{date_str}-{time_str}-{account_suffix}-{unique_part}"
        super().save(*args, **kwargs)

class VirtualCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    card_number = models.CharField(max_length=16)
    expiry = models.CharField(max_length=5)
    cvv = models.CharField(max_length=3)
    provider = models.CharField(max_length=50)  # e.g., Union54
    status = models.CharField(
        max_length=20,
        choices=[
            (GeneralStatusChoices.ACTIVE, _('Active')),
            (GeneralStatusChoices.BLOCKED, _('Blocked')),
        ]
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Virtual Card')
        verbose_name_plural = _('Virtual Cards')
        ordering = ['-issued_at']
    
    def __str__(self):
        return f"Virtual Card - {self.card_number[-4:]} ({self.user.username})"

class Bank(BaseAbstractModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    slug = models.SlugField()
    ussd = models.CharField(max_length=20, blank=True, null=True, help_text=_('USSD code for the bank'))
    logo = models.URLField(blank=True, null=True, help_text=_('URL to bank logo'))
    is_active = models.BooleanField(default=True, help_text=_('Whether this bank is active for transfers'))
    
    class Meta:
        verbose_name = _('Bank')
        verbose_name_plural = _('Banks')
        ordering = ['name']
    
    def __str__(self):
        return self.name

    
    # Additional Configuration
    applies_to_fees = models.BooleanField(
        default=True,
        help_text=_('Apply VAT to transfer fees')
    )
    applies_to_levies = models.BooleanField(
        default=False,
        help_text=_('Apply VAT to CBN levies')
    )
    minimum_vatable_amount = MoneyField(
        max_digits=19,
        decimal_places=4,
        default_currency='NGN',
        default=0.00,
        help_text=_('Minimum amount subject to VAT')
    )
    
    # Exemption Settings
    exempt_internal_transfers = models.BooleanField(
        default=False,
        help_text=_('Exempt internal transfers from VAT')
    )
    exempt_international_transfers = models.BooleanField(
        default=False,
        help_text=_('Exempt international transfers from VAT')
    )
    
    # Rounding Configuration
    rounding_method = models.CharField(
        max_length=20,
        choices=[
            ('none', _('No Rounding')),
            ('nearest', _('Nearest Whole Number')),
            ('up', _('Round Up')),
            ('down', _('Round Down')),
        ],
        default='none',
        help_text=_('How to round VAT amounts')
    )

    class Meta:
        verbose_name = _('VAT Charge')
        verbose_name_plural = _('VAT Charges')
        indexes = [
            models.Index(fields=['active']),
            models.Index(fields=['effective_from', 'effective_to']),
        ]
    
    def __str__(self):
        return f"VAT {self.rate * 100}% ({'Active' if self.active else 'Inactive'})"
    
    def calculate_vat(self, base_amount, transfer_type='external'):
        """Calculate VAT for a given base amount."""
        if not self.active:
            return Money(0, 'NGN')
            
        if base_amount < self.minimum_vatable_amount:
            return Money(0, 'NGN')
            
        if self.exempt_internal_transfers and transfer_type == 'internal':
            return Money(0, 'NGN')
            
        if self.exempt_international_transfers and transfer_type == 'international':
            return Money(0, 'NGN')
            
        vat_amount = base_amount * self.rate
        
        if self.rounding_method == 'nearest':
            vat_amount = round(vat_amount)
        elif self.rounding_method == 'up':
            vat_amount = math.ceil(vat_amount)
        elif self.rounding_method == 'down':
            vat_amount = math.floor(vat_amount)
            
        return Money(vat_amount, 'NGN')
    
    @classmethod
    def get_current_rate(cls):
        """Get the currently active VAT rate."""
        return cls.objects.filter(active=True).first()
    
    def save(self, *args, **kwargs):
        if self.active:
            # Deactivate other active rates
            type(self).objects.filter(active=True).exclude(pk=self.pk).update(active=False)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('VAT Charge')
        verbose_name_plural = _('VAT Charges')

    def __str__(self):
        return f"VAT {self.rate * 100}% (Active: {self.active})"

class CBNLevy(models.Model):
    """Model for managing CBN transaction levies."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Levy configuration
    name = models.CharField(max_length=100)
    rate = models.DecimalField(
        max_digits=5, 
        decimal_places=4,
        help_text=_('Levy rate as decimal')
    )
    fixed_amount = MoneyField(
        max_digits=19,
        decimal_places=4,
        default_currency='NGN',
        null=True,
        blank=True,
        help_text=_('Fixed levy amount (if applicable)')
    )
    
    # Applicability
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('all', 'All Transactions'),
            ('internal', 'Internal Transfers'),
            ('external', 'External Transfers'),
            ('international', 'International Transfers'),
        ],
        default='all'
    )
    min_amount = MoneyField(
        max_digits=19,
        decimal_places=4,
        default_currency='NGN',
        default=0.00,
        help_text=_('Minimum amount for levy application')
    )
    max_amount = MoneyField(
        max_digits=19,
        decimal_places=4,
        default_currency='NGN',
        null=True,
        blank=True,
        help_text=_('Maximum amount for levy application')
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    
    # Regulatory info
    regulation_reference = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'bank_cbn_levy'
        verbose_name = 'CBN Levy'
        verbose_name_plural = 'CBN Levies'
        
    def __str__(self):
        return f"{self.name} - {self.rate}% ({self.transaction_type})"
    
    def calculate_levy(self, amount, transaction_type='external'):
        """Calculate applicable levy for a transaction."""
        if not self.is_active:
            return Money(0, 'NGN')
            
        if amount < self.min_amount:
            return Money(0, 'NGN')
            
        if self.max_amount and amount > self.max_amount:
            return Money(0, 'NGN')
            
        if self.transaction_type != 'all' and self.transaction_type != transaction_type:
            return Money(0, 'NGN')
            
        if self.fixed_amount:
            return self.fixed_amount
            
        return Money(amount * self.rate, 'NGN')


class TransactionCharge(models.Model):
    """Model for tracking all charges applied to a transaction."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.OneToOneField('BankTransfer', on_delete=models.CASCADE, related_name='charges')
    
    # Individual charges
    transfer_fee = MoneyField(
        max_digits=19,
        decimal_places=4,
        default_currency='NGN',
        default=0.00,
        help_text=_('Transfer fee amount')
    )
    vat_amount = MoneyField(
        max_digits=19,
        decimal_places=4,
        default_currency='NGN',
        default=0.00,
        help_text=_('VAT amount')
    )
    levy_amount = MoneyField(
        max_digits=19,
        decimal_places=4,
        default_currency='NGN',
        default=0.00,
        help_text=_('CBN levy amount')
    )
    
    # Rates used
    fee_rule = models.ForeignKey(
        'TransferFeeRule',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transaction_charges'
    )
    vat_rate = models.ForeignKey(
        'VATCharge',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transaction_charges'
    )
    levy = models.ForeignKey(
        'CBNLevy',
        on_delete=models.SET_NULL,
        null=True,
        related_name='transaction_charges'
    )
    
    # Charge metadata
    charge_status = models.CharField(
        max_length=20,
        choices=[
            ('calculated', 'Calculated'),
            ('applied', 'Applied'),
            ('refunded', 'Refunded'),
            ('waived', 'Waived'),
        ],
        default='calculated'
    )
    waiver_reason = models.TextField(blank=True)
    waived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='charge_waivers'
    )
    
    # Audit trail
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_charge_controls'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_charge_controls'
    )
    
    class Meta:
        db_table = 'bank_transaction_charge'
        
    def __str__(self):
        return f"Charges for {self.transfer.reference}"
    
    @property
    def total_charges(self):
        """Calculate total charges."""
        return self.transfer_fee + self.vat_amount + self.levy_amount
    
    def waive_charges(self, user, reason):
        """Waive all charges for this transaction."""
        self.charge_status = 'waived'
        self.waiver_reason = reason
        self.waived_by = user
        self.transfer_fee = Money(0, 'NGN')
        self.vat_amount = Money(0, 'NGN')
        self.levy_amount = Money(0, 'NGN')
        self.save()

    class Meta:
        verbose_name = _('CBN VAT Charge')
        verbose_name_plural = _('CBN VAT Charges')

    def __str__(self):
        return f'VAT {self.vat_amount} for Transfer {self.transfer.reference}'

class TransferChargeControl(models.Model):
    """Model for managing and configuring transaction charges."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    
    # Core charge controls
    levy_active = models.BooleanField(default=True, help_text=_("Apply CBN levy to transfers?"))
    vat_active = models.BooleanField(default=True, help_text=_("Apply VAT to transfers?"))
    fee_active = models.BooleanField(default=True, help_text=_("Apply transfer fee to transfers?"))
    
    # Charge thresholds
    min_amount_for_charges = MoneyField(
        max_digits=19, 
        decimal_places=4, 
        default_currency='NGN', 
        default=0.00,
        help_text=_('Minimum transfer amount to apply charges')
    )
    
    # Exemption settings
    exempt_internal_transfers = models.BooleanField(
        default=False,
        help_text=_('Exempt internal transfers from charges')
    )
    exempt_first_monthly_transfer = models.BooleanField(
        default=False,
        help_text=_('Exempt first transfer of each month')
    )
    
    # VAT configuration
    vat_calculation_base = models.CharField(
        max_length=20,
        choices=[
            ('fee_only', _('Apply VAT on Fee Only')),
            ('fee_and_levy', _('Apply VAT on Fee and Levy')),
            ('total_amount', _('Apply VAT on Total Amount')),
        ],
        default='fee_only',
        help_text=_('Base amount for VAT calculation')
    )
    
    # Levy configuration
    levy_calculation_method = models.CharField(
        max_length=20,
        choices=[
            ('fixed', _('Fixed Amount')),
            ('percentage', _('Percentage of Amount')),
            ('tiered', _('Tiered Based on Amount')),
        ],
        default='fixed',
        help_text=_('Method to calculate CBN levy')
    )
    
    # Charge order
    charge_application_order = models.CharField(
        max_length=20,
        choices=[
            ('fee_vat_levy', _('Fee → VAT → Levy')),
            ('levy_vat_fee', _('Levy → VAT → Fee')),
            ('vat_fee_levy', _('VAT → Fee → Levy')),
        ],
        default='fee_vat_levy',
        help_text=_('Order of applying charges')
    )
    
    # Additional settings
    round_charges = models.BooleanField(
        default=True,
        help_text=_('Round calculated charges to nearest whole number')
    )
    allow_charge_overrides = models.BooleanField(
        default=False,
        help_text=_('Allow manual override of calculated charges')
    )
    
    # Audit trail
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_charge_controls'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_charge_controls'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Transfer Charge Control')
        verbose_name_plural = _('Transfer Charge Controls')
    
    def __str__(self):
        status = []
        if self.fee_active:
            status.append('Fee')
        if self.vat_active:
            status.append('VAT')
        if self.levy_active:
            status.append('Levy')
        return f"Charge Control ({', '.join(status)} Active)"
    
    def calculate_total_charges(self, amount, transfer_type='external'):
        """Calculate total charges for a given amount."""
        if amount < self.min_amount_for_charges:
            return Money(0, 'NGN')
            
        if self.exempt_internal_transfers and transfer_type == 'internal':
            return Money(0, 'NGN')
            
        total_charges = Money(0, 'NGN')
        
        # Calculate individual charges based on application order
        order = self.charge_application_order.split('_')
        for charge_type in order:
            if charge_type == 'fee' and self.fee_active:
                fee = self._calculate_fee(amount)
                total_charges += fee
            elif charge_type == 'vat' and self.vat_active:
                vat = self._calculate_vat(amount, total_charges)
                total_charges += vat
            elif charge_type == 'levy' and self.levy_active:
                levy = self._calculate_levy(amount)
                total_charges += levy
        
        if self.round_charges:
            total_charges = self._round_amount(total_charges)
            
        return total_charges
    
    def _calculate_fee(self, amount):
        """Calculate transfer fee."""
        # Implementation would use TransferFeeRule
        pass
    
    def _calculate_vat(self, amount, previous_charges):
        """Calculate VAT based on configuration."""
        # Implementation would use VATCharge
        pass
    
    def _calculate_levy(self, amount):
        """Calculate CBN levy based on configuration."""
        # Implementation would use levy calculation rules
        pass
    
    def _round_amount(self, amount):
        """Round amount according to configuration."""
        return round(amount)

    class Meta:
        verbose_name = "Transfer Charge Control"
        verbose_name_plural = "Transfer Charge Controls"

    def __str__(self):
        return f"Levy: {'On' if self.levy_active else 'Off'}, VAT: {'On' if self.vat_active else 'Off'}, Fee: {'On' if self.fee_active else 'Off'}"


class StaffRole(models.Model):
    """Banking hall staff roles with hierarchical permissions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    ROLE_CHOICES = [
        ('teller', 'Teller'),
        ('customer_service', 'Customer Service Representative'),
        ('personal_banker', 'Personal Banker'),
        ('assistant_manager', 'Assistant Manager'),
        ('manager', 'Manager'),
        ('branch_manager', 'Branch Manager'),
    ]
    
    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    level = models.IntegerField(help_text="Hierarchical level (1=lowest, 6=highest)")
    description = models.TextField()
    max_transaction_approval = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0)
    can_approve_kyc = models.BooleanField(default=False)
    can_manage_staff = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    can_override_transactions = models.BooleanField(default=False)
    can_handle_escalations = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['level']
    
    def __str__(self):
        return self.name
    
    def can_approve_amount(self, amount):
        """Check if this role can approve a transaction amount."""
        return amount <= self.max_transaction_approval


class StaffProfile(models.Model):
    """Staff profile extending the user model with role and branch information."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.ForeignKey(StaffRole, on_delete=models.PROTECT, related_name='staff_members')
    employee_id = models.CharField(max_length=20, unique=True)
    branch = models.CharField(max_length=100, blank=True, help_text="Branch or location")
    department = models.CharField(max_length=100, blank=True)
    supervisor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subordinates'
    )
    is_active = models.BooleanField(default=True)
    hire_date = models.DateField()
    last_review_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['role__level', 'user__username']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role.name}"
    
    def can_approve_transaction(self, amount):
        """Check if this staff member can approve a transaction amount."""
        return self.role.can_approve_amount(amount)
    
    def can_approve_kyc(self):
        """Check if this staff member can approve KYC."""
        return self.role.can_approve_kyc
    
class Charge(models.Model):
    """A charge for a transaction."""
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='charge'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    receipt_url = models.URLField(blank=True)
    waiver_reason = models.TextField(blank=True)
    waived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='charge_waivers'
    )
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_manage_staff(self):
        """Check if this staff member can manage other staff."""
        return self.role.can_manage_staff
    
    def get_subordinates(self):
        """Get all staff members this person supervises."""
        return StaffProfile.objects.filter(supervisor=self)
    
    def get_supervisor_chain(self):
        """Get the chain of supervisors up to the top."""
        chain = []
        current = self.supervisor
        while current:
            chain.append(current)
            current = current.supervisor
        return chain


class TransactionApproval(models.Model):
    """Model for tracking transaction approvals and escalations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('escalated', 'Escalated'),
    ]
    
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='approvals')
    requested_by = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='approval_requests')
    approved_by = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approvals_given'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True, help_text="Reason for approval/rejection")
    escalation_reason = models.TextField(blank=True, help_text="Reason for escalation")
    escalated_to = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='escalations_received'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Approval for {self.transaction.reference} - {self.status}"


class CustomerEscalation(models.Model):
    """Model for tracking customer service escalations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escalations')
    created_by = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='escalations_created')
    assigned_to = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='escalations_assigned'
    )
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.customer.username} ({self.status})"


class StaffActivity(models.Model):
    """Model for tracking staff activities and performance."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=[
        ('transaction_processed', 'Transaction Processed'),
        ('kyc_approved', 'KYC Approved'),
        ('escalation_handled', 'Escalation Handled'),
        ('customer_served', 'Customer Served'),
        ('report_generated', 'Report Generated'),
        ('staff_managed', 'Staff Managed'),
    ])
    description = models.TextField()
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    related_object = GenericForeignKey('related_object_type', 'related_object_id')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Staff Activities'
    
    def __str__(self):
        return f"{self.staff.user.username} - {self.activity_type} at {self.timestamp}"


class TransferFeeRule(models.Model):
    """
    Dynamic fee rules for transfers with tiered pricing.
    Allows business logic for fees to be configurable without code changes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_('ID'))
    name = models.CharField(max_length=100, help_text=_('Name of the fee rule'))
    min_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00, help_text=_('Minimum amount for this rule'))
    max_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00, help_text=_('Maximum amount for this rule (0 for unlimited)'))
    fee_percent = models.DecimalField(max_digits=5, decimal_places=4, default=0.00, help_text=_('Fee as percentage (e.g., 0.005 for 0.5%)'))
    fee_fixed = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00, help_text=_('Fixed fee amount'))
    bank_type = models.CharField(
        max_length=20,
        choices=[
            ('internal', _('Internal Transfer')),
            ('external', _('External Transfer')),
            ('both', _('Both Internal and External')),
        ],
        default='both',
        help_text=_('Type of transfer this rule applies to')
    )
    kyc_level = models.CharField(
        max_length=20,
        choices=KYCLevelChoices.choices,
        blank=True,
        null=True,
        help_text=_('KYC level this rule applies to (blank for all levels)')
    )
    is_active = models.BooleanField(default=True, help_text=_('Whether this rule is active'))
    priority = models.PositiveIntegerField(default=0, help_text=_('Priority order (higher number = higher priority)'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Transfer Fee Rule')
        verbose_name_plural = _('Transfer Fee Rules')
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.min_amount} to {self.max_amount} ({self.fee_percent}% + {self.fee_fixed})"

    def calculate_fee(self, amount):
        """Calculate fee for a given amount."""
        if amount < self.min_amount:
            return Money(0, 'NGN')
        
        if self.max_amount and amount > self.max_amount:
            return Money(0, 'NGN')
        
        percentage_fee = amount * self.fee_percent
        total_fee = percentage_fee + self.fee_fixed
        return total_fee

    def is_applicable(self, amount, transfer_type, kyc_level=None):
        """Check if this rule is applicable to the given parameters."""
        if not self.is_active:
            return False
        
        if amount < self.min_amount:
            return False
        
        if self.max_amount and amount > self.max_amount:
            return False
        
        if self.bank_type not in ['both', transfer_type]:
            return False
        
        if self.kyc_level and kyc_level != self.kyc_level:
            return False
        
        return True


class TwoFactorAuthentication(models.Model):
    """Model for 2FA tokens and verification."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='two_fa_tokens')
    token = models.CharField(max_length=6)
    token_type = models.CharField(max_length=20, choices=[
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('totp', 'TOTP'),
        ('push', 'Push Notification'),
    ])
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'bank_two_factor_authentication'
        indexes = [
            models.Index(fields=['user', 'token_type', 'is_used']),
            models.Index(fields=['expires_at']),
        ]
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        return not self.is_used and not self.is_expired()

class IPWhitelist(models.Model):
    """Model for IP address whitelisting."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ip_whitelist')
    ip_address = models.GenericIPAddressField()
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=IPWhitelistStatus.CHOICES, default=IPWhitelistStatus.PENDING)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_ips')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'bank_ip_whitelist'
        unique_together = ['user', 'ip_address']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['ip_address']),
        ]

class DeviceFingerprint(models.Model):
    """Model for device fingerprinting and tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_fingerprints')
    device_id = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=20, choices=DeviceFingerprint.CHOICES)
    user_agent = models.TextField()
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=255, blank=True)
    is_trusted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bank_device_fingerprint'
        indexes = [
            models.Index(fields=['user', 'is_trusted']),
            models.Index(fields=['device_id']),
        ]

class NightGuardSettings(models.Model):
    """Per-user Night Guard configuration for stricter transfer verification during set hours.

    Applies only to app-initiated bank transfers. When active, transfers require
    face verification first, then a fallback verification method if face fails.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='night_guard_settings'
    )
    enabled = models.BooleanField(default=False)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    # Primary verification is face; keep for extensibility
    primary_method = models.CharField(max_length=20, default='face')
    # Fallback options: 2fa, pin, none
    fallback_method = models.CharField(max_length=20, default='2fa')
    # Scope is fixed to app-only per product spec, but stored for clarity
    applies_to = models.CharField(max_length=20, default='app_only')
    # Face enrollment
    face_template_hash = models.CharField(max_length=128, null=True, blank=True)
    face_template_alg = models.CharField(max_length=20, default='sha256')
    face_registered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_night_guard_settings'
        verbose_name = _('Night Guard Settings')
        verbose_name_plural = _('Night Guard Settings')

    def __str__(self):
        return f"NightGuardSettings(user={self.user_id}, enabled={self.enabled})"


class LargeTransactionShieldSettings(models.Model):
    """Per-user Large Transaction Shield configuration with face enrollment.

    Applies to app-initiated bank transfers. Requires face verification when
    thresholds are exceeded.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='large_tx_shield_settings'
    )
    enabled = models.BooleanField(default=False)
    per_transaction_limit = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    daily_limit = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    monthly_limit = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    # Face enrollment
    face_template_hash = models.CharField(max_length=128, null=True, blank=True)
    face_template_alg = models.CharField(max_length=20, default='sha256')
    face_registered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_large_tx_shield_settings'
        verbose_name = _('Large Transaction Shield Settings')
        verbose_name_plural = _('Large Transaction Shield Settings')

    def __str__(self):
        return f"LTSSettings(user={self.user_id}, enabled={self.enabled})"


class LocationGuardSettings(models.Model):
    """Per-user Location Guard configuration. Requires face verification when user is
    outside their usual states for app-initiated bank transfers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='location_guard_settings'
    )
    enabled = models.BooleanField(default=False)
    allowed_states = models.JSONField(default=list, blank=True, help_text=_('List of up to 6 states user usually resides'))
    # Face enrollment
    face_template_hash = models.CharField(max_length=128, null=True, blank=True)
    face_template_alg = models.CharField(max_length=20, default='sha256')
    face_registered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_location_guard_settings'
        verbose_name = _('Location Guard Settings')
        verbose_name_plural = _('Location Guard Settings')

    def __str__(self):
        return f"LocationGuardSettings(user={self.user_id}, enabled={self.enabled})"


class PaymentIntent(models.Model):
    """Represents a payment initiated from marketplace/social apps using wallet."""
    STATUS_CHOICES = [
        ('requires_confirmation', 'Requires Confirmation'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_intents')
    order_id = models.CharField(max_length=128)
    merchant_id = models.CharField(max_length=128)
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    currency = models.CharField(max_length=5, default='NGN')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='requires_confirmation')
    description = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=100, unique=True, blank=True)
    escrowed = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_payment_intent'
        indexes = [
            models.Index(fields=['user', 'status', 'created_at']),
            models.Index(fields=['order_id']),
            models.Index(fields=['merchant_id']),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            date_str = datetime.now().strftime('%Y%m%d')
            time_str = datetime.now().strftime('%H%M%S')
            unique_part = uuid.uuid4().hex[:6].upper()
            account_suffix = getattr(getattr(self.user, 'wallet', None), 'account_number', '')
            suffix = account_suffix[-4:] if account_suffix else '0000'
            self.reference = f"PI-{date_str}-{time_str}-{suffix}-{unique_part}"
        super().save(*args, **kwargs)


class PayoutRequest(models.Model):
    """Represents a merchant payout request from wallet to bank."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant_id = models.CharField(max_length=128)
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    destination_bank_code = models.CharField(max_length=10)
    destination_account_number = models.CharField(max_length=20)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_payout_request'
        indexes = [
            models.Index(fields=['merchant_id', 'status', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"PO-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)


class MerchantSettlementAccount(models.Model):
    """Store/merchant settlement destination and preferences."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant_id = models.CharField(max_length=128, unique=True)
    bank_code = models.CharField(max_length=10)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=128, blank=True)
    is_verified = models.BooleanField(default=False)
    verification_method = models.CharField(max_length=20, default='api', blank=True)
    preferred_schedule = models.CharField(max_length=20, default='manual', blank=True)  # manual|daily|weekly
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_merchant_settlement_account'
        indexes = [
            models.Index(fields=['merchant_id']),
        ]

    def __str__(self):
        return f"{self.merchant_id} -> {self.bank_code}:{self.account_number}"

class FraudDetection(models.Model):
    """Model for fraud detection and suspicious activity tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fraud_detections')
    transfer = models.ForeignKey('BankTransfer', on_delete=models.CASCADE, related_name='fraud_detections', null=True, blank=True)
    fraud_type = models.CharField(max_length=50, choices=[
        # Basic Checks
        ('velocity_check', 'Velocity Check'),
        ('geographic_anomaly', 'Geographic Anomaly'),
        ('behavioral_anomaly', 'Behavioral Anomaly'),
        ('device_mismatch', 'Device Mismatch'),
        ('ip_anomaly', 'IP Anomaly'),
        ('amount_anomaly', 'Amount Anomaly'),
        ('recipient_anomaly', 'Recipient Anomaly'),
        # Advanced ML Patterns
        ('time_pattern_anomaly', 'Time Pattern Anomaly'),
        ('transaction_sequence_anomaly', 'Transaction Sequence Anomaly'),
        ('beneficiary_network_anomaly', 'Beneficiary Network Anomaly'),
        ('spending_pattern_deviation', 'Spending Pattern Deviation'),
        ('account_takeover_pattern', 'Account Takeover Pattern'),
        ('multi_device_anomaly', 'Multi-Device Usage Anomaly'),
        ('cross_border_pattern', 'Cross-Border Pattern'),
        ('recurring_pattern_break', 'Recurring Pattern Break'),
        ('velocity_pattern_change', 'Velocity Pattern Change'),
        ('device_fingerprint_anomaly', 'Device Fingerprint Anomaly'),
        ('location_pattern_break', 'Location Pattern Break'),
        ('transaction_amount_pattern', 'Transaction Amount Pattern'),
        ('new_beneficiary_risk', 'New Beneficiary Risk Pattern'),
        ('mule_account_pattern', 'Mule Account Pattern'),
    ])
    risk_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    flag = models.CharField(max_length=20, choices=FraudFlag.CHOICES, default=FraudFlag.NORMAL)
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_fraud')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bank_fraud_detection'
        indexes = [
            models.Index(fields=['user', 'flag']),
            models.Index(fields=['risk_score']),
            models.Index(fields=['created_at']),
        ]

class MLFeatureEngineering(models.Model):
    """Model for storing and managing ML feature engineering configurations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature_name = models.CharField(max_length=100, unique=True)
    feature_type = models.CharField(max_length=50, choices=[
        ('numerical', 'Numerical'),
        ('categorical', 'Categorical'),
        ('temporal', 'Temporal'),
        ('text', 'Text'),
        ('composite', 'Composite'),
    ])
    description = models.TextField()
    computation_logic = models.JSONField(help_text=_('Logic for feature computation'))
    dependencies = models.JSONField(help_text=_('Required input features'))
    validation_rules = models.JSONField(help_text=_('Feature validation rules'))
    
    # Feature statistics
    mean_value = models.FloatField(null=True, blank=True)
    std_dev = models.FloatField(null=True, blank=True)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    unique_values = models.JSONField(null=True, blank=True)
    
    # Feature importance
    importance_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Feature importance in model')
    )
    
    # Version control
    version = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_ml_feature_engineering'
        indexes = [
            models.Index(fields=['feature_type']),
            models.Index(fields=['importance_score']),
        ]
    
    def __str__(self):
        return f"{self.feature_name} v{self.version}"


class MLModelTraining(models.Model):
    """Model for tracking ML model training sessions and performance."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=50, choices=[
        ('classification', 'Classification'),
        ('regression', 'Regression'),
        ('clustering', 'Clustering'),
        ('anomaly_detection', 'Anomaly Detection'),
    ])
    
    # Training data info
    training_data_size = models.PositiveIntegerField()
    features_used = models.JSONField()
    training_start = models.DateTimeField()
    training_end = models.DateTimeField(null=True, blank=True)
    
    # Model configuration
    hyperparameters = models.JSONField()
    model_architecture = models.JSONField()
    
    # Performance metrics
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    auc_roc = models.FloatField(null=True, blank=True)
    
    # Cross-validation results
    cv_scores = models.JSONField(null=True, blank=True)
    validation_metrics = models.JSONField(null=True, blank=True)
    
    # Model artifacts
    model_file_path = models.CharField(max_length=255)
    feature_importance = models.JSONField()
    
    # Version control
    version = models.CharField(max_length=50)
    is_production = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('ML Model Training')
        verbose_name_plural = _('ML Model Trainings')
        indexes = [
            models.Index(fields=['model_name']),
            models.Index(fields=['version']),
            models.Index(fields=['is_production']),
            models.Index(fields=['training_start', 'training_end']),
        ]
    
    def __str__(self):
        return f"{self.model_name} v{self.version} ({'Prod' if self.is_production else 'Non-Prod'})"


# --- Restored fee/charge control models ---
class VATCharge(models.Model):
    """Application-wide VAT configuration (rate stored as decimal fraction, e.g., 0.075 for 7.5%)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rate = models.DecimalField(max_digits=5, decimal_places=4, validators=[MinValueValidator(0), MaxValueValidator(1)])
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('VAT Charge')
        verbose_name_plural = _('VAT Charges')
        ordering = ['-updated_at']

    def __str__(self) -> str:
        pct = float(self.rate) * 100
        return f"VAT {pct:.2f}% ({'Active' if self.active else 'Inactive'})"


class TransferChargeControl(models.Model):
    """Feature toggles for applying fees, VAT and levy to transfers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    levy_active = models.BooleanField(default=True)
    vat_active = models.BooleanField(default=True)
    fee_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Transfer Charge Control')
        verbose_name_plural = _('Transfer Charge Controls')
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f"Charges(L:{self.levy_active}, V:{self.vat_active}, F:{self.fee_active})"


class CBNLevy(models.Model):
    """Configuration for CBN levy by transfer type (rate stored as fraction)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    regulation_reference = models.CharField(max_length=100, blank=True)
    rate = models.DecimalField(max_digits=5, decimal_places=4, validators=[MinValueValidator(0), MaxValueValidator(1)])
    transaction_type = models.CharField(max_length=10, choices=[(TransferType.INTERNAL, 'Intra-bank'), (TransferType.EXTERNAL, 'Inter-bank')], default=TransferType.EXTERNAL)
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('CBN Levy')
        verbose_name_plural = _('CBN Levies')
        ordering = ['-effective_from']

    def __str__(self) -> str:
        return f"{self.name} {float(self.rate) * 100:.2f}% ({self.get_transaction_type_display()})"


class TransactionChargeStatus(models.TextChoices):
    CALCULATED = 'calculated', _('Calculated')
    APPLIED = 'applied', _('Applied')
    FAILED = 'failed', _('Failed')


class TransactionCharge(models.Model):
    """Computed charges for a specific bank transfer (fee, VAT, levy)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.OneToOneField('BankTransfer', on_delete=models.CASCADE, related_name='charges')
    transfer_fee = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0)
    vat_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0)
    levy_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0)
    charge_status = models.CharField(max_length=20, choices=TransactionChargeStatus.choices, default=TransactionChargeStatus.CALCULATED)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Transaction Charge')
        verbose_name_plural = _('Transaction Charges')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Charges for {self.transfer.reference}"


class SecurityAlert(models.Model):
    """Model for security alerts and notifications."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_alerts')
    alert_type = models.CharField(max_length=50, choices=[
        ('login_attempt', 'Login Attempt'),
        ('transfer_attempt', 'Transfer Attempt'),
        ('device_change', 'Device Change'),
        ('location_change', 'Location Change'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('limit_exceeded', 'Limit Exceeded'),
        ('two_fa_required', '2FA Required'),
    ])
    severity = models.CharField(max_length=20, choices=SecurityLevel.CHOICES, default=SecurityLevel.MEDIUM)
    title = models.CharField(max_length=255)
    message = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'bank_security_alert'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['severity']),
            models.Index(fields=['created_at']),
        ]

class RealTimeMonitoring(models.Model):
    """Model for real-time transaction monitoring and anomaly detection."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monitoring_records')
    transaction = models.ForeignKey('BankTransfer', on_delete=models.CASCADE, related_name='monitoring_data')
    
    # Real-time metrics
    velocity_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Transaction velocity risk score')
    )
    amount_anomaly_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Transaction amount anomaly score')
    )
    pattern_deviation_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Pattern deviation risk score')
    )
    location_risk_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Location-based risk score')
    )
    device_risk_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Device-based risk score')
    )
    
    # Behavioral patterns
    user_patterns = models.JSONField(help_text=_('User behavioral patterns'))
    transaction_patterns = models.JSONField(help_text=_('Transaction patterns'))
    device_patterns = models.JSONField(help_text=_('Device usage patterns'))
    
    # ML model outputs
    model_predictions = models.JSONField(help_text=_('ML model prediction outputs'))
    confidence_scores = models.JSONField(help_text=_('Confidence scores for predictions'))
    feature_contributions = models.JSONField(help_text=_('Feature importance for decisions'))
    
    # Alert flags
    requires_review = models.BooleanField(default=False)
    alert_level = models.CharField(max_length=20, choices=SecurityLevel.CHOICES, default=SecurityLevel.LOW)
    alerts_generated = models.JSONField(default=list, help_text=_('List of alerts generated'))
    
    # Monitoring metadata
    monitored_at = models.DateTimeField(auto_now_add=True)
    processing_time = models.FloatField(help_text=_('Time taken for monitoring in milliseconds'))
    
    class Meta:
        db_table = 'bank_realtime_monitoring'
        indexes = [
            models.Index(fields=['user', 'monitored_at']),
            models.Index(fields=['alert_level']),
            models.Index(fields=['requires_review']),
        ]
    
    def __str__(self):
        return f"Monitoring - {self.user.username} at {self.monitored_at}"
    
    def calculate_composite_risk(self):
        """Calculate overall risk score from all components."""
        weights = {
            'velocity': 0.2,
            'amount': 0.25,
            'pattern': 0.2,
            'location': 0.15,
            'device': 0.2
        }
        
        composite_score = (
            weights['velocity'] * self.velocity_score +
            weights['amount'] * self.amount_anomaly_score +
            weights['pattern'] * self.pattern_deviation_score +
            weights['location'] * self.location_risk_score +
            weights['device'] * self.device_risk_score
        )
        
        return min(composite_score, 1.0)


class AnomalyDetection(models.Model):
    """Model for advanced anomaly detection using multiple ML techniques."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anomaly_detections')
    transaction = models.ForeignKey('BankTransfer', on_delete=models.CASCADE, related_name='anomaly_detections', null=True)
    
    # Anomaly scores
    isolation_forest_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Isolation Forest anomaly score')
    )
    local_outlier_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Local Outlier Factor score')
    )
    autoencoder_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Autoencoder reconstruction error score')
    )
    
    # Contextual features
    temporal_features = models.JSONField(help_text=_('Time-based contextual features'))
    behavioral_features = models.JSONField(help_text=_('User behavior features'))
    transaction_features = models.JSONField(help_text=_('Transaction-specific features'))
    
    # Anomaly classification
    anomaly_type = models.CharField(max_length=50, choices=[
        ('point_anomaly', 'Point Anomaly'),
        ('contextual_anomaly', 'Contextual Anomaly'),
        ('collective_anomaly', 'Collective Anomaly'),
    ])
    confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Detection confidence score')
    )
    
    # Decision thresholds
    threshold_config = models.JSONField(help_text=_('Dynamic threshold configuration'))
    is_anomaly = models.BooleanField(default=False)
    
    # Investigation status
    requires_investigation = models.BooleanField(default=False)
    investigation_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ], default='pending')
    investigation_notes = models.TextField(blank=True)
    
    # Response actions
    actions_taken = models.JSONField(default=list, help_text=_('Actions taken in response'))
    resolution = models.CharField(max_length=50, choices=[
        ('true_positive', 'True Positive'),
        ('false_positive', 'False Positive'),
        ('inconclusive', 'Inconclusive'),
    ], null=True, blank=True)
    
    # Metadata
    detected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_anomaly_detection'
        indexes = [
            models.Index(fields=['user', 'is_anomaly']),
            models.Index(fields=['investigation_status']),
            models.Index(fields=['detected_at']),
        ]
    
    def __str__(self):
        return f"Anomaly Detection - {self.user.username} at {self.detected_at}"
    
    def calculate_composite_score(self):
        """Calculate weighted composite anomaly score."""
        weights = {
            'isolation_forest': 0.4,
            'local_outlier': 0.3,
            'autoencoder': 0.3
        }
        
        composite_score = (
            weights['isolation_forest'] * self.isolation_forest_score +
            weights['local_outlier'] * self.local_outlier_score +
            weights['autoencoder'] * self.autoencoder_score
        )
        
        return min(composite_score, 1.0)
    
    def update_investigation_status(self, status, notes=None):
        """Update investigation status and notes."""
        self.investigation_status = status
        if notes:
            self.investigation_notes = notes
        self.save()
    
    def mark_resolution(self, resolution_type, actions_taken=None):
        """Mark anomaly resolution and record actions taken."""
        self.resolution = resolution_type
        if actions_taken:
            self.actions_taken.extend(actions_taken)
        self.save()


class MLModelRegistry(models.Model):
    """Model for ML model versioning, deployment and performance tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50)
    model_type = models.CharField(max_length=50, choices=[
        ('fraud_detection', 'Fraud Detection'),
        ('risk_scoring', 'Risk Scoring'),
        ('anomaly_detection', 'Anomaly Detection'),
        ('behavioral_analysis', 'Behavioral Analysis'),
        ('transaction_monitoring', 'Transaction Monitoring'),
    ])
    
    # Model metadata
    framework = models.CharField(max_length=50, help_text=_('ML framework used'))
    input_features = models.JSONField(help_text=_('Required input features'))
    output_format = models.JSONField(help_text=_('Model output specification'))
    preprocessing_steps = models.JSONField(help_text=_('Data preprocessing pipeline'))
    
    # Deployment info
    deployment_environment = models.CharField(max_length=50, choices=[
        ('development', 'Development'),
        ('staging', 'Staging'),
        ('production', 'Production'),
    ])
    deployed_at = models.DateTimeField(null=True, blank=True)
    deployed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='model_deployments')
    is_active = models.BooleanField(default=False)
    
    # Performance metrics
    performance_metrics = models.JSONField(help_text=_('Model performance metrics'))
    inference_latency = models.FloatField(help_text=_('Average inference time in ms'))
    error_rate = models.FloatField(help_text=_('Model error rate'))
    
    # Monitoring
    health_status = models.CharField(max_length=20, choices=[
        ('healthy', 'Healthy'),
        ('degraded', 'Degraded'),
        ('failed', 'Failed'),
    ])
    last_monitoring_check = models.DateTimeField(auto_now=True)
    monitoring_metrics = models.JSONField(help_text=_('Real-time monitoring metrics'))
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_ml_model_registry'
        unique_together = ['model_name', 'model_version']
        indexes = [
            models.Index(fields=['model_name', 'model_version']),
            models.Index(fields=['deployment_environment', 'is_active']),
            models.Index(fields=['health_status']),
        ]
    
    def __str__(self):
        return f"{self.model_name} v{self.model_version} ({self.deployment_environment})"
    
    def deploy(self, environment, deployed_by):
        """Deploy model to specified environment."""
        self.deployment_environment = environment
        self.deployed_at = timezone.now()
        self.deployed_by = deployed_by
        self.is_active = True
        self.save()
    
    def rollback(self):
        """Rollback model deployment."""
        self.is_active = False
        self.health_status = 'failed'
        self.save()
    
    def update_metrics(self, metrics):
        """Update model performance metrics."""
        self.performance_metrics.update(metrics)
        self.save(update_fields=['performance_metrics', 'updated_at'])
    
    def check_health(self):
        """Check model health based on metrics."""
        if self.error_rate > 0.1:  # 10% error rate threshold
            self.health_status = 'degraded'
        if self.error_rate > 0.2:  # 20% error rate threshold
            self.health_status = 'failed'
            self.is_active = False
        self.save()


class ChargeHistory(models.Model):
    """Model for tracking historical changes in fees, VAT, and levies."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    charge_type = models.CharField(max_length=20, choices=[
        ('fee', 'Transfer Fee'),
        ('vat', 'VAT'),
        ('levy', 'CBN Levy'),
    ])
    
    # Previous and new values
    old_value = models.DecimalField(max_digits=10, decimal_places=4)
    new_value = models.DecimalField(max_digits=10, decimal_places=4)
    
    # Change metadata
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='charge_changes')
    change_reason = models.TextField(help_text=_('Reason for the change'))
    approval_reference = models.CharField(max_length=100, blank=True, help_text=_('Reference to regulatory approval if any'))
    effective_from = models.DateTimeField()
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bank_charge_history'
        indexes = [
            models.Index(fields=['charge_type', 'effective_from']),
            models.Index(fields=['created_at']),
        ]
        
    def __str__(self):
        return f"{self.charge_type} change: {self.old_value} → {self.new_value} ({self.effective_from})"


class TransferLimit(models.Model):
    """Model for configurable transfer limits."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfer_limits')
    limit_type = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('per_transaction', 'Per Transaction'),
        ('per_recipient', 'Per Recipient'),
    ])
    amount_limit = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    count_limit = models.IntegerField(default=0)  # 0 means unlimited
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_transfer_limit'
        unique_together = ['user', 'limit_type']
        indexes = [
            models.Index(fields=['user', 'limit_type', 'is_active']),
        ]

class BehavioralAnalysis(models.Model):
    """Model for ML-based behavioral analysis and profiling."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='behavioral_profiles')
    
    # Temporal patterns
    active_hours = models.JSONField(help_text=_('Typical hours of activity'))
    active_days = models.JSONField(help_text=_('Typical days of activity'))
    session_patterns = models.JSONField(help_text=_('Session duration and frequency patterns'))
    
    # Transaction patterns
    amount_patterns = models.JSONField(help_text=_('Amount distribution patterns'))
    frequency_patterns = models.JSONField(help_text=_('Transaction frequency patterns'))
    recipient_patterns = models.JSONField(help_text=_('Recipient interaction patterns'))
    
    # Location patterns
    location_clusters = models.JSONField(help_text=_('Common location clusters'))
    travel_patterns = models.JSONField(help_text=_('User movement patterns'))
    typical_radius = models.FloatField(help_text=_('Typical activity radius in km'))
    
    # Device patterns
    device_fingerprints = models.JSONField(help_text=_('Known device fingerprints'))
    device_usage_patterns = models.JSONField(help_text=_('Device usage patterns'))
    
    # Behavioral scores
    regularity_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Score indicating behavior regularity')
    )
    risk_appetite = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Score indicating risk tolerance')
    )
    trust_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Overall trust score')
    )
    
    # Analysis metadata
    last_analyzed = models.DateTimeField(auto_now=True)
    data_points = models.PositiveIntegerField(help_text=_('Number of data points analyzed'))
    confidence_level = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=_('Confidence in analysis')
    )
    
    class Meta:
        db_table = 'bank_behavioral_analysis'
        indexes = [
            models.Index(fields=['user', 'trust_score']),
            models.Index(fields=['last_analyzed']),
        ]
    
    def __str__(self):
        return f"Behavioral Profile - {self.user.username}"
    
    def get_risk_factors(self):
        """Get list of risk factors based on behavioral analysis."""
        risk_factors = []
        
        # Check temporal anomalies
        current_hour = timezone.now().hour
        if current_hour not in self.active_hours.get('peak_hours', []):
            risk_factors.append({
                'type': 'unusual_time',
                'severity': 'medium',
                'details': 'Activity outside normal hours'
            })
        
        # Check location anomalies
        if self.location_clusters:
            current_location = self.get_current_location()
            if not self.is_location_familiar(current_location):
                risk_factors.append({
                    'type': 'unusual_location',
                    'severity': 'high',
                    'details': 'Activity from unfamiliar location'
                })
        
        # Check device anomalies
        current_device = self.get_current_device()
        if current_device not in self.device_fingerprints:
            risk_factors.append({
                'type': 'unknown_device',
                'severity': 'high',
                'details': 'Activity from unknown device'
            })
        
        return risk_factors
    
    def update_patterns(self, new_activity_data):
        """Update behavioral patterns with new activity data."""
        # Update temporal patterns
        self._update_temporal_patterns(new_activity_data)
        
        # Update location patterns
        self._update_location_patterns(new_activity_data)
        
        # Update device patterns
        self._update_device_patterns(new_activity_data)
        
        # Recalculate scores
        self._recalculate_scores()
        
        self.data_points += 1
        self.save()
    
    def _update_temporal_patterns(self, activity_data):
        """Update temporal patterns with new activity."""
        hour = activity_data['timestamp'].hour
        day = activity_data['timestamp'].weekday()
        
        # Update active hours
        active_hours = self.active_hours
        if hour in active_hours:
            active_hours[hour]['count'] += 1
        else:
            active_hours[hour] = {'count': 1}
        
        # Update active days
        active_days = self.active_days
        if day in active_days:
            active_days[day]['count'] += 1
        else:
            active_days[day] = {'count': 1}
        
        self.active_hours = active_hours
        self.active_days = active_days


class SavedBeneficiary(models.Model):
    """Model for saved beneficiaries."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_beneficiaries')
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    bank_code = models.CharField(max_length=10)
    bank_name = models.CharField(max_length=255)
    nickname = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_saved_beneficiary'
        unique_together = ['user', 'account_number', 'bank_code']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['account_number', 'bank_code']),
        ]

class ScheduledTransfer(models.Model):
    """Model for scheduled and recurring transfers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_transfers')
    transfer_type = models.CharField(max_length=20, choices=TransferType.CHOICES, default=TransferType.EXTERNAL)
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    recipient_account = models.CharField(max_length=20)
    recipient_bank_code = models.CharField(max_length=10)
    recipient_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=20, choices=[
        ('once', 'Once'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ], default='once')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=TransferStatus.CHOICES, default=TransferStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_scheduled_transfer'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['next_execution']),
            models.Index(fields=['status']),
        ]

class BulkTransfer(models.Model):
    """Model for bulk transfer operations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bulk_transfers')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    total_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    total_count = models.IntegerField(default=0)
    completed_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('partial_completed', 'Partially Completed'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_bulk_transfer'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]

class BulkTransferItem(models.Model):
    """Model for individual items in bulk transfers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bulk_transfer = models.ForeignKey(BulkTransfer, on_delete=models.CASCADE, related_name='items')
    transfer = models.ForeignKey(BankTransfer, on_delete=models.CASCADE, related_name='bulk_items', null=True, blank=True)
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    bank_code = models.CharField(max_length=10)
    bank_name = models.CharField(max_length=255)
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=TransferStatus.CHOICES, default=TransferStatus.PENDING)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bank_bulk_transfer_item'
        indexes = [
            models.Index(fields=['bulk_transfer', 'status']),
        ]

class EscrowService(models.Model):
    """Model for escrow services."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escrow_sent')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='escrow_received')
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('funded', 'Funded'),
        ('released', 'Released'),
        ('refunded', 'Refunded'),
        ('expired', 'Expired'),
    ], default='pending')
    expires_at = models.DateTimeField()
    funded_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_escrow_service'
        indexes = [
            models.Index(fields=['sender', 'status']),
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['expires_at']),
        ]

class TransferReversal(models.Model):
    """Model for transfer reversals and refunds."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_transfer = models.ForeignKey(BankTransfer, on_delete=models.CASCADE, related_name='reversals')
    reversal_transfer = models.ForeignKey(BankTransfer, on_delete=models.CASCADE, related_name='reversed_from', null=True, blank=True)
    reason = models.CharField(max_length=50, choices=[
        ('user_request', 'User Request'),
        ('system_error', 'System Error'),
        ('fraud_detection', 'Fraud Detection'),
        ('bank_error', 'Bank Error'),
        ('duplicate_transfer', 'Duplicate Transfer'),
    ])
    description = models.TextField()
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    status = models.CharField(max_length=20, choices=TransferStatus.CHOICES, default=TransferStatus.PENDING)
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_reversals')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_reversals')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'bank_transfer_reversal'
        indexes = [
            models.Index(fields=['original_transfer']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

class TransferFailure(models.Model):
    """Model for tracking detailed transfer failure information."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.OneToOneField(BankTransfer, on_delete=models.CASCADE, related_name='failure_details')
    
    # Failure categorization
    error_code = models.CharField(max_length=50, help_text=_('Standardized error code'))
    error_category = models.CharField(max_length=50, choices=[
        ('validation', 'Validation Error'),
        ('business_logic', 'Business Logic Error'),
        ('technical', 'Technical Error'),
        ('external_service', 'External Service Error'),
        ('fraud_detection', 'Fraud Detection'),
        ('security', 'Security Error'),
        ('system', 'System Error'),
    ])
    
    # Detailed failure information
    failure_reason = models.TextField(help_text=_('Human-readable failure reason'))
    technical_details = models.JSONField(default=dict, help_text=_('Technical details for debugging'))
    stack_trace = models.TextField(blank=True, help_text=_('Stack trace if applicable'))
    
    # Context information
    user_id = models.UUIDField(help_text=_('User who initiated the transfer'))
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True, help_text=_('User agent from request'))
    device_fingerprint = models.CharField(max_length=255, blank=True, null=True, help_text=_('Device fingerprint for fraud detection'))
    
    # Transfer context
    transfer_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    recipient_account = models.CharField(max_length=20)
    recipient_bank_code = models.CharField(max_length=10, blank=True, null=True, help_text=_('Bank code for external transfers'))
    
    # Timing information
    failed_at = models.DateTimeField(auto_now_add=True)
    processing_duration = models.FloatField(null=True, blank=True, help_text=_('Processing duration in seconds'))
    
    # Resolution tracking
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_failures')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Retry information
    retry_count = models.PositiveIntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    max_retries = models.PositiveIntegerField(default=3)
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bank_transfer_failure'
        verbose_name = _('Transfer Failure')
        verbose_name_plural = _('Transfer Failures')
        ordering = ['-failed_at']
        indexes = [
            models.Index(fields=['error_code']),
            models.Index(fields=['error_category']),
            models.Index(fields=['user_id']),
            models.Index(fields=['failed_at']),
            models.Index(fields=['is_resolved']),
        ]
    
    def __str__(self):
        return f"Transfer Failure - {self.error_code} ({self.transfer.id})"
    
    def mark_resolved(self, resolved_by=None, notes=""):
        """Mark this failure as resolved."""
        self.is_resolved = True
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save(update_fields=['is_resolved', 'resolved_by', 'resolved_at', 'resolution_notes', 'updated_at'])
    
    def increment_retry(self):
        """Increment retry count and update last retry timestamp."""
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.save(update_fields=['retry_count', 'last_retry_at', 'updated_at'])
    
    def can_retry(self):
        """Check if this failure can be retried."""
        return self.retry_count < self.max_retries and not self.is_resolved
    
    @property
    def failure_summary(self):
        """Get a summary of the failure for reporting."""
        return {
            'error_code': self.error_code,
            'error_category': self.error_category,
            'failure_reason': self.failure_reason,
            'transfer_amount': float(self.transfer_amount.amount) if hasattr(self.transfer_amount, 'amount') else float(self.transfer_amount),
            'recipient_account': self.recipient_account,
            'failed_at': self.failed_at.isoformat(),
            'is_resolved': self.is_resolved,
            'retry_count': self.retry_count
        }


class XySaveAccount(models.Model):
    """
    XySave Account - Savings and Investment feature
    Similar to OWealth and PalmPay's Cashbox
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='xysave_account')
    account_number = models.CharField(max_length=20, unique=True)
    balance = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    total_interest_earned = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    last_interest_calculation = models.DateTimeField(auto_now_add=True)
    daily_interest_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0004)  # 0.04% daily = ~15% annual
    is_active = models.BooleanField(default=True)
    auto_save_enabled = models.BooleanField(default=False)
    auto_save_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)  # 10% by default
    auto_save_min_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=100.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "XySave Account"
        verbose_name_plural = "XySave Accounts"
    
    def __str__(self):
        return f"XySave Account - {self.user.username} ({self.account_number})"
    
    def calculate_daily_interest(self):
        """
        Calculate daily interest using tiered rates automatically.
        Tiers:
          - First 10,000 at 20% p.a
          - Next up to 100,000 at 16% p.a
          - Above 100,000 at 8% p.a
        """
        from decimal import Decimal
        if self.balance.amount <= 0:
            return Money(0, self.balance.currency)

        balance = self.balance.amount
        # Define thresholds and daily rates as Decimals to avoid float math
        TIER_1_THRESHOLD = Decimal('10000')
        TIER_2_THRESHOLD = Decimal('100000')
        DAILY_TIER_1_RATE = Decimal('0.20') / Decimal('365')
        DAILY_TIER_2_RATE = Decimal('0.16') / Decimal('365')
        DAILY_TIER_3_RATE = Decimal('0.08') / Decimal('365')

        total_interest = Decimal('0')

        # Tier 1
        tier_1_amount = min(balance, TIER_1_THRESHOLD)
        if tier_1_amount > 0:
            total_interest += tier_1_amount * DAILY_TIER_1_RATE
            balance -= tier_1_amount

        # Tier 2
        if balance > 0:
            tier_2_cap = TIER_2_THRESHOLD - TIER_1_THRESHOLD
            tier_2_amount = min(balance, tier_2_cap)
            if tier_2_amount > 0:
                total_interest += tier_2_amount * DAILY_TIER_2_RATE
                balance -= tier_2_amount

        # Tier 3
        if balance > 0:
            total_interest += balance * DAILY_TIER_3_RATE

        return Money(total_interest, self.balance.currency)
    
    def get_annual_interest_rate(self):
        """Get effective annual percentage rate based on current balance and tiers"""
        from decimal import Decimal
        if self.balance.amount <= 0:
            return Decimal('0')

        daily_interest = self.calculate_daily_interest().amount
        effective_daily_rate = (daily_interest / self.balance.amount) if self.balance.amount > 0 else Decimal('0')
        return effective_daily_rate * Decimal('36500')  # 365 * 100
    
    def can_withdraw(self, amount):
        """Check if withdrawal is possible"""
        return self.balance.amount >= amount.amount and self.is_active
    
    def get_interest_breakdown(self):
        """Get detailed interest breakdown"""
        try:
            from .interest_services import InterestRateCalculator as _IRC
            calculator = _IRC()
            return calculator.calculate_interest_breakdown(self.balance)
        except Exception:
            return {
                'tier_1': {'amount': 0, 'rate': 20, 'daily_rate': 0, 'interest': 0},
                'tier_2': {'amount': 0, 'rate': 16, 'daily_rate': 0, 'interest': 0},
                'tier_3': {'amount': 0, 'rate': 8,  'daily_rate': 0, 'interest': 0},
                'total_interest': 0
            }


class XySaveTransaction(models.Model):
    """
    XySave Transaction - Track all XySave activities
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('interest_credit', 'Interest Credit'),
        ('auto_save', 'Auto Save'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    xysave_account = models.ForeignKey(XySaveAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    balance_before = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    balance_after = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    reference = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "XySave Transaction"
        verbose_name_plural = "XySave Transactions"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.xysave_account.user.username}"


class XySaveGoal(models.Model):
    """
    XySave Goal - Users can set savings goals
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='xysave_goals')
    name = models.CharField(max_length=100)
    target_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    current_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    target_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "XySave Goal"
        verbose_name_plural = "XySave Goals"
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    def get_progress_percentage(self):
        """Get progress percentage towards goal"""
        if self.target_amount.amount > 0:
            return (self.current_amount.amount / self.target_amount.amount) * 100
        return 0
    
    def is_completed(self):
        """Check if goal is completed"""
        return self.current_amount.amount >= self.target_amount.amount


class XySaveInvestment(models.Model):
    """
    XySave Investment - Track investment allocations
    """
    INVESTMENT_TYPES = [
        ('treasury_bills', 'Treasury Bills'),
        ('mutual_funds', 'Mutual Funds'),
        ('short_term_placements', 'Short-term Placements'),
        ('government_bonds', 'Government Bonds'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    xysave_account = models.ForeignKey(XySaveAccount, on_delete=models.CASCADE, related_name='investments')
    investment_type = models.CharField(max_length=25, choices=INVESTMENT_TYPES)
    amount_invested = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    current_value = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    expected_return_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Annual percentage
    maturity_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "XySave Investment"
        verbose_name_plural = "XySave Investments"
    
    def __str__(self):
        return f"{self.investment_type} - {self.amount_invested} - {self.xysave_account.user.username}"
    
    def get_return_percentage(self):
        """Get current return percentage"""
        if self.amount_invested.amount > 0:
            return ((self.current_value.amount - self.amount_invested.amount) / self.amount_invested.amount) * 100
        return 0


class XySaveSettings(models.Model):
    """
    XySave Settings - User preferences for XySave
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='xysave_settings')
    daily_interest_notifications = models.BooleanField(default=True)
    goal_reminders = models.BooleanField(default=True)
    auto_save_notifications = models.BooleanField(default=True)
    investment_updates = models.BooleanField(default=True)
    preferred_interest_payout = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], default='daily')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "XySave Settings"
        verbose_name_plural = "XySave Settings"
    
    def __str__(self):
        return f"XySave Settings - {self.user.username}"


class SpendAndSaveAccount(models.Model):
    """
    Spend and Save Account - Automatic savings from daily spending
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='spend_and_save_account')
    account_number = models.CharField(max_length=20, unique=True)
    balance = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    total_interest_earned = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    total_saved_from_spending = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    
    # Spend and Save Configuration
    is_active = models.BooleanField(default=False, help_text=_('Whether Spend and Save is activated'))
    savings_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=5.00,
        validators=[MinValueValidator(1.0), MaxValueValidator(50.0)],
        help_text=_('Percentage of daily spending to automatically save (1-50%)')
    )
    min_transaction_amount = MoneyField(
        max_digits=19, 
        decimal_places=4, 
        default_currency='NGN', 
        default=100.00,
        help_text=_('Minimum transaction amount to trigger auto-save')
    )
    
    # Interest Rate Configuration (Tiered)
    TIER_1_THRESHOLD = 10000  # First 10,000 at 20% p.a
    TIER_2_THRESHOLD = 100000  # 10,001 - 100,000 at 16% p.a
    TIER_3_RATE = 0.08  # Above 100,000 at 8% p.a
    
    TIER_1_RATE = 0.20  # 20% p.a for first 10,000
    TIER_2_RATE = 0.16  # 16% p.a for 10,001 - 100,000
    
    # Daily rates (annual rate / 365)
    daily_tier_1_rate = models.DecimalField(max_digits=8, decimal_places=6, default=0.000548)  # 20% / 365
    daily_tier_2_rate = models.DecimalField(max_digits=8, decimal_places=6, default=0.000438)  # 16% / 365
    daily_tier_3_rate = models.DecimalField(max_digits=8, decimal_places=6, default=0.000219)  # 8% / 365
    
    # Tracking
    last_interest_calculation = models.DateTimeField(auto_now_add=True)
    total_transactions_processed = models.PositiveIntegerField(default=0)
    last_auto_save_date = models.DateField(null=True, blank=True)
    
    # Withdrawal destination preference
    default_withdrawal_destination = models.CharField(
        max_length=20,
        choices=[
            ('wallet', 'Wallet'),
            ('xysave', 'XySave Account'),
        ],
        default='wallet',
        help_text=_('Default destination for withdrawals')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Spend and Save Account"
        verbose_name_plural = "Spend and Save Accounts"
    
    def __str__(self):
        return f"Spend and Save - {self.user.username} ({self.account_number})"
    
    def calculate_tiered_interest(self):
        """Calculate interest using tiered rates"""
        if self.balance.amount <= 0:
            return Money(0, self.balance.currency)
        
        balance = self.balance.amount
        total_interest = 0
        
        # Tier 1: First 10,000 at 20% p.a
        if balance > 0:
            tier_1_amount = min(balance, self.TIER_1_THRESHOLD)
            tier_1_interest = tier_1_amount * self.daily_tier_1_rate
            total_interest += tier_1_interest
            balance -= tier_1_amount
        
        # Tier 2: 10,001 - 100,000 at 16% p.a
        if balance > 0:
            tier_2_amount = min(balance, self.TIER_2_THRESHOLD - self.TIER_1_THRESHOLD)
            tier_2_interest = tier_2_amount * self.daily_tier_2_rate
            total_interest += tier_2_interest
            balance -= tier_2_amount
        
        # Tier 3: Above 100,000 at 8% p.a
        if balance > 0:
            tier_3_interest = balance * self.daily_tier_3_rate
            total_interest += tier_3_interest
        
        return Money(total_interest, self.balance.currency)
    
    def get_interest_breakdown(self):
        """Get detailed interest breakdown by tier"""
        if self.balance.amount <= 0:
            return {
                'tier_1': {'amount': 0, 'rate': 20, 'interest': 0},
                'tier_2': {'amount': 0, 'rate': 16, 'interest': 0},
                'tier_3': {'amount': 0, 'rate': 8, 'interest': 0},
                'total_interest': 0
            }
        
        balance = self.balance.amount
        breakdown = {
            'tier_1': {'amount': 0, 'rate': 20, 'interest': 0},
            'tier_2': {'amount': 0, 'rate': 16, 'interest': 0},
            'tier_3': {'amount': 0, 'rate': 8, 'interest': 0},
            'total_interest': 0
        }
        
        # Tier 1: First 10,000 at 20% p.a
        if balance > 0:
            tier_1_amount = min(balance, self.TIER_1_THRESHOLD)
            breakdown['tier_1']['amount'] = tier_1_amount
            breakdown['tier_1']['interest'] = tier_1_amount * self.daily_tier_1_rate
            balance -= tier_1_amount
        
        # Tier 2: 10,001 - 100,000 at 16% p.a
        if balance > 0:
            tier_2_amount = min(balance, self.TIER_2_THRESHOLD - self.TIER_1_THRESHOLD)
            breakdown['tier_2']['amount'] = tier_2_amount
            breakdown['tier_2']['interest'] = tier_2_amount * self.daily_tier_2_rate
            balance -= tier_2_amount
        
        # Tier 3: Above 100,000 at 8% p.a
        if balance > 0:
            breakdown['tier_3']['amount'] = balance
            breakdown['tier_3']['interest'] = balance * self.daily_tier_3_rate
        
        breakdown['total_interest'] = (
            breakdown['tier_1']['interest'] + 
            breakdown['tier_2']['interest'] + 
            breakdown['tier_3']['interest']
        )
        
        return breakdown
    
    def can_withdraw(self, amount):
        """Check if withdrawal is possible"""
        return self.balance.amount >= amount.amount and self.is_active
    
    def activate(self, savings_percentage):
        """Activate Spend and Save with specified percentage"""
        self.is_active = True
        self.savings_percentage = savings_percentage
        self.save()
    
    def deactivate(self):
        """Deactivate Spend and Save"""
        self.is_active = False
        self.save()
    
    def process_spending_transaction(self, transaction_amount, wallet_balance_after_transfer=None):
        """
        Process a spending transaction and calculate auto-save amount
        Auto-save amount is calculated based on the transfer amount
        The auto-save amount will be deducted from the remaining wallet balance
        """
        if not self.is_active or transaction_amount.amount < self.min_transaction_amount.amount:
            return Money(0, transaction_amount.currency)
        
        # Calculate auto-save based on the transfer amount (not remaining balance)
        auto_save_amount = transaction_amount.amount * (self.savings_percentage / 100)
        
        return Money(auto_save_amount, transaction_amount.currency)


class SpendAndSaveTransaction(models.Model):
    """
    Spend and Save Transaction - Track all Spend and Save activities
    """
    TRANSACTION_TYPES = [
        ('auto_save', 'Auto Save from Spending'),
        ('withdrawal', 'Withdrawal'),
        ('interest_credit', 'Interest Credit'),
        ('manual_deposit', 'Manual Deposit'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
    ]
    
    WITHDRAWAL_DESTINATIONS = [
        ('wallet', 'Wallet'),
        ('xysave', 'XySave Account'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    spend_and_save_account = models.ForeignKey(SpendAndSaveAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    balance_before = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    balance_after = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    reference = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # For auto-save transactions
    original_transaction_id = models.UUIDField(null=True, blank=True, help_text=_('ID of the original spending transaction'))
    original_transaction_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', null=True, blank=True)
    savings_percentage_applied = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # For withdrawals
    withdrawal_destination = models.CharField(max_length=20, choices=WITHDRAWAL_DESTINATIONS, null=True, blank=True)
    destination_account = models.CharField(max_length=50, null=True, blank=True)
    
    # Interest tracking
    interest_earned = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    interest_breakdown = models.JSONField(default=dict, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Spend and Save Transaction"
        verbose_name_plural = "Spend and Save Transactions"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.spend_and_save_account.user.username}"


class SpendAndSaveSettings(models.Model):
    """
    Spend and Save Settings - User preferences for Spend and Save
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='spend_and_save_settings')
    
    # Notification preferences
    auto_save_notifications = models.BooleanField(default=True)
    interest_notifications = models.BooleanField(default=True)
    withdrawal_notifications = models.BooleanField(default=True)
    
    # Auto-save preferences
    preferred_savings_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=5.00,
        validators=[MinValueValidator(1.0), MaxValueValidator(50.0)]
    )
    min_transaction_threshold = MoneyField(
        max_digits=19, 
        decimal_places=4, 
        default_currency='NGN', 
        default=100.00
    )
    
    # Withdrawal preferences
    default_withdrawal_destination = models.CharField(
        max_length=20,
        choices=[
            ('wallet', 'Wallet'),
            ('xysave', 'XySave Account'),
        ],
        default='wallet'
    )
    # Funding source preferences for auto-save
    funding_preference = models.CharField(
        max_length=10,
        choices=[
            ('auto', 'Auto (prefer XySave, fallback Wallet)'),
            ('xysave', 'XySave (fallback Wallet)'),
            ('wallet', 'Wallet only'),
        ],
        default='auto'
    )
    
    # Interest preferences
    interest_payout_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='daily'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Spend and Save Settings"
        verbose_name_plural = "Spend and Save Settings"
    
    def __str__(self):
        return f"Spend and Save Settings - {self.user.username}"


# Utility function for calculating tiered interest rates
def calculate_tiered_interest_rate(balance_amount):
    """
    Calculate tiered interest rate for a given balance amount
    Returns: dict with tier breakdown and total interest
    """
    TIER_1_THRESHOLD = 10000
    TIER_2_THRESHOLD = 100000
    TIER_1_RATE = 0.20  # 20% p.a
    TIER_2_RATE = 0.16  # 16% p.a
    TIER_3_RATE = 0.08  # 8% p.a
    
    # Daily rates
    daily_tier_1_rate = TIER_1_RATE / 365
    daily_tier_2_rate = TIER_2_RATE / 365
    daily_tier_3_rate = TIER_3_RATE / 365
    
    if balance_amount <= 0:
        return {
            'tier_1': {'amount': 0, 'rate': 20, 'daily_rate': daily_tier_1_rate, 'interest': 0},
            'tier_2': {'amount': 0, 'rate': 16, 'daily_rate': daily_tier_2_rate, 'interest': 0},
            'tier_3': {'amount': 0, 'rate': 8, 'daily_rate': daily_tier_3_rate, 'interest': 0},
            'total_interest': 0
        }
    
    balance = balance_amount
    breakdown = {
        'tier_1': {'amount': 0, 'rate': 20, 'daily_rate': daily_tier_1_rate, 'interest': 0},
        'tier_2': {'amount': 0, 'rate': 16, 'daily_rate': daily_tier_2_rate, 'interest': 0},
        'tier_3': {'amount': 0, 'rate': 8, 'daily_rate': daily_tier_3_rate, 'interest': 0},
        'total_interest': 0
    }
    
    # Tier 1: First 10,000 at 20% p.a
    if balance > 0:
        tier_1_amount = min(balance, TIER_1_THRESHOLD)
        breakdown['tier_1']['amount'] = tier_1_amount
        breakdown['tier_1']['interest'] = tier_1_amount * daily_tier_1_rate
        balance -= tier_1_amount
    
    # Tier 2: 10,001 - 100,000 at 16% p.a
    if balance > 0:
        tier_2_amount = min(balance, TIER_2_THRESHOLD - TIER_1_THRESHOLD)
        breakdown['tier_2']['amount'] = tier_2_amount
        breakdown['tier_2']['interest'] = tier_2_amount * daily_tier_2_rate
        balance -= tier_2_amount
    
    # Tier 3: Above 100,000 at 8% p.a
    if balance > 0:
        breakdown['tier_3']['amount'] = balance
        breakdown['tier_3']['interest'] = balance * daily_tier_3_rate
    
    breakdown['total_interest'] = (
        breakdown['tier_1']['interest'] + 
        breakdown['tier_2']['interest'] + 
        breakdown['tier_3']['interest']
    )
    
    return breakdown

class TargetSavingCategory(models.TextChoices):
    """Categories for target savings"""
    ACCOMMODATION = 'accommodation', _('Accommodation')
    EDUCATION = 'education', _('Education')
    BUSINESS = 'business', _('Business')
    JAPA = 'japa', _('Japa (Relocation)')
    VEHICLE = 'vehicle', _('Vehicle')
    WEDDING = 'wedding', _('Wedding')
    EMERGENCY = 'emergency', _('Emergency Fund')
    INVESTMENT = 'investment', _('Investment')
    TRAVEL = 'travel', _('Travel')
    HOME_RENOVATION = 'home_renovation', _('Home Renovation')
    MEDICAL = 'medical', _('Medical')
    ENTERTAINMENT = 'entertainment', _('Entertainment')
    OTHER = 'other', _('Other')

class TargetSavingFrequency(models.TextChoices):
    """Frequency options for target savings"""
    DAILY = 'daily', _('Daily')
    WEEKLY = 'weekly', _('Weekly')
    MONTHLY = 'monthly', _('Monthly')

class TargetSavingSource(models.TextChoices):
    """Source options for target savings funding"""
    WALLET = 'wallet', _('Wallet')
    XYSAVE = 'xysave', _('XySave Account')
    BOTH = 'both', _('Both (50/50)')

class TargetSaving(models.Model):
    """Model for user target savings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='target_savings')
    
    # Basic Information
    name = models.CharField(max_length=255, verbose_name=_('Target Name'))
    category = models.CharField(
        max_length=20,
        choices=TargetSavingCategory.choices,
        verbose_name=_('Category')
    )
    target_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Target Amount')
    )
    
    # Enhanced fields
    account_number = models.CharField(max_length=20, unique=True, verbose_name=_('Account Number'))
    source = models.CharField(
        max_length=10,
        choices=TargetSavingSource.choices,
        default=TargetSavingSource.WALLET,
        verbose_name=_('Source')
    )
    strict_mode = models.BooleanField(default=False, verbose_name=_('Strict Mode'))
    
    # Frequency and Schedule
    frequency = models.CharField(
        max_length=10,
        choices=TargetSavingFrequency.choices,
        verbose_name=_('Frequency')
    )
    preferred_deposit_day = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Preferred Deposit Day'),
        help_text=_('Day of week for weekly/monthly deposits')
    )
    
    # Dates
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))
    
    # Progress Tracking
    current_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_('Current Amount')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_completed = models.BooleanField(default=False, verbose_name=_('Is Completed'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Target Saving')
        verbose_name_plural = _('Target Savings')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.target_amount is None or self.target_amount == 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount to reach target"""
        if self.target_amount is None:
            return 0
        return max(0, self.target_amount - self.current_amount)
    
    @property
    def days_remaining(self):
        """Calculate days remaining until end date"""
        if self.end_date is None:
            return 0
        from django.utils import timezone
        today = timezone.now().date()
        remaining = (self.end_date - today).days
        return max(0, remaining)
    
    @property
    def is_overdue(self):
        """Check if target is overdue"""
        if self.end_date is None:
            return False
        from django.utils import timezone
        return timezone.now().date() > self.end_date and not self.is_completed
    
    @property
    def daily_target(self):
        """Calculate daily target amount"""
        if self.days_remaining == 0:
            return 0
        remaining = self.remaining_amount
        if remaining == 0:
            return 0
        return remaining / self.days_remaining
    
    @property
    def weekly_target(self):
        """Calculate weekly target amount"""
        if self.days_remaining == 0:
            return 0
        remaining = self.remaining_amount
        if remaining == 0:
            return 0
        weeks_remaining = max(1, self.days_remaining // 7)
        return remaining / weeks_remaining
    
    @property
    def monthly_target(self):
        """Calculate monthly target amount"""
        if self.days_remaining == 0:
            return 0
        remaining = self.remaining_amount
        if remaining == 0:
            return 0
        months_remaining = max(1, self.days_remaining // 30)
        return remaining / months_remaining

class TargetSavingDeposit(models.Model):
    """Model for tracking deposits to target savings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_saving = models.ForeignKey(
        TargetSaving,
        on_delete=models.CASCADE,
        related_name='deposits'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Deposit Amount')
    )
    source = models.CharField(
        max_length=10,
        choices=TargetSavingSource.choices,
        default=TargetSavingSource.WALLET,
        verbose_name=_('Source')
    )
    deposit_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    
    class Meta:
        verbose_name = _('Target Saving Deposit')
        verbose_name_plural = _('Target Saving Deposits')
        ordering = ['-deposit_date']
        indexes = [
            models.Index(fields=['target_saving', 'deposit_date']),
        ]
    
    def __str__(self):
        return f"{self.amount} - {self.target_saving.name}"
    
    def save(self, *args, **kwargs):
        """Override save to update target saving current amount"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update target saving current amount
            self.target_saving.current_amount += self.amount
            self.target_saving.save()
            
            # Check if target is completed
            if self.target_saving.current_amount >= self.target_saving.target_amount:
                self.target_saving.is_completed = True
                self.target_saving.save()


class TargetSavingWithdrawal(models.Model):
    """Model for tracking withdrawals from target savings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_saving = models.ForeignKey(
        TargetSaving,
        on_delete=models.CASCADE,
        related_name='withdrawals'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Withdrawal Amount')
    )
    destination = models.CharField(
        max_length=10,
        choices=TargetSavingSource.choices,
        default=TargetSavingSource.WALLET,
        verbose_name=_('Destination')
    )
    withdrawal_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    
    class Meta:
        verbose_name = _('Target Saving Withdrawal')
        verbose_name_plural = _('Target Saving Withdrawals')
        ordering = ['-withdrawal_date']
        indexes = [
            models.Index(fields=['target_saving', 'withdrawal_date']),
        ]
    
    def __str__(self):
        return f"{self.amount} - {self.target_saving.name}"
    
    def save(self, *args, **kwargs):
        """Override save to update target saving current amount"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update target saving current amount
            self.target_saving.current_amount -= self.amount
            self.target_saving.save()

class FixedSavingsPurpose(models.TextChoices):
    """Purpose categories for fixed savings"""
    EDUCATION = 'education', _('Education')
    BUSINESS = 'business', _('Business')
    INVESTMENT = 'investment', _('Investment')
    EMERGENCY = 'emergency', _('Emergency Fund')
    TRAVEL = 'travel', _('Travel')
    WEDDING = 'wedding', _('Wedding')
    VEHICLE = 'vehicle', _('Vehicle')
    HOME_RENOVATION = 'home_renovation', _('Home Renovation')
    MEDICAL = 'medical', _('Medical')
    RETIREMENT = 'retirement', _('Retirement')
    OTHER = 'other', _('Other')

class FixedSavingsSource(models.TextChoices):
    """Source options for fixed savings funding"""
    WALLET = 'wallet', _('Wallet')
    XYSAVE = 'xysave', _('XySave Account')
    BOTH = 'both', _('Both Wallet and XySave')

class FixedSavingsAccount(models.Model):
    """
    Fixed Savings Account - Lock funds for a fixed period and earn higher interest
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fixed_savings_accounts')
    account_number = models.CharField(max_length=20, unique=True)
    
    # Fixed Savings Configuration
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', help_text=_('Amount to be fixed'))
    source = models.CharField(
        max_length=10,
        choices=FixedSavingsSource.choices,
        help_text=_('Source of funds (wallet, xysave, or both)')
    )
    purpose = models.CharField(
        max_length=20,
        choices=FixedSavingsPurpose.choices,
        help_text=_('Purpose of the fixed savings')
    )
    purpose_description = models.TextField(blank=True, help_text=_('Detailed description of the purpose'))
    
    # Interest Rate Configuration (Tiered based on duration)
    # 10% p.a for 7-29 days
    # 10% p.a for 30-59 days  
    # 12% p.a for 60-89 days
    # 15% p.a for 90-179 days
    # 18% p.a for 180-364 days
    # 20% p.a for 365-1000 days
    
    TIER_1_MIN_DAYS = 7
    TIER_1_MAX_DAYS = 29
    TIER_1_RATE = 0.10  # 10% p.a
    
    TIER_2_MIN_DAYS = 30
    TIER_2_MAX_DAYS = 59
    TIER_2_RATE = 0.10  # 10% p.a
    
    TIER_3_MIN_DAYS = 60
    TIER_3_MAX_DAYS = 89
    TIER_3_RATE = 0.12  # 12% p.a
    
    TIER_4_MIN_DAYS = 90
    TIER_4_MAX_DAYS = 179
    TIER_4_RATE = 0.15  # 15% p.a
    
    TIER_5_MIN_DAYS = 180
    TIER_5_MAX_DAYS = 364
    TIER_5_RATE = 0.18  # 18% p.a
    
    TIER_6_MIN_DAYS = 365
    TIER_6_MAX_DAYS = 1000
    TIER_6_RATE = 0.20  # 20% p.a
    
    # Dates
    start_date = models.DateField(help_text=_('Start date of the fixed savings'))
    payback_date = models.DateField(help_text=_('Date when funds will be paid back with interest'))
    
    # Auto-renewal
    auto_renewal_enabled = models.BooleanField(default=False, help_text=_('Whether to automatically renew on maturity'))
    
    # Status and tracking
    is_active = models.BooleanField(default=True, help_text=_('Whether the fixed savings is active'))
    is_matured = models.BooleanField(default=False, help_text=_('Whether the fixed savings has matured'))
    is_paid_out = models.BooleanField(default=False, help_text=_('Whether the matured amount has been paid out'))
    
    # Interest calculation
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text=_('Annual interest rate (%)'))
    total_interest_earned = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    maturity_amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    matured_at = models.DateTimeField(null=True, blank=True)
    paid_out_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Fixed Savings Account')
        verbose_name_plural = _('Fixed Savings Accounts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['payback_date', 'is_matured']),
            models.Index(fields=['is_active', 'payback_date']),
        ]
    
    def __str__(self):
        return f"Fixed Savings - {self.user.username} (₦{self.amount.amount:,.2f})"
    
    def save(self, *args, **kwargs):
        # Generate account number if not provided
        if not self.account_number:
            self.account_number = f"FS{self.user.id:08d}{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate interest rate based on duration if not set
        if not self.interest_rate:
            self.interest_rate = self.calculate_interest_rate()
        
        # Calculate maturity amount
        if not self.maturity_amount:
            self.maturity_amount = self.calculate_maturity_amount()
        
        super().save(*args, **kwargs)
    
    def calculate_interest_rate(self):
        """Calculate interest rate based on duration"""
        if not self.start_date or not self.payback_date:
            return 0
        
        duration_days = (self.payback_date - self.start_date).days
        
        if self.TIER_1_MIN_DAYS <= duration_days <= self.TIER_1_MAX_DAYS:
            return self.TIER_1_RATE * 100
        elif self.TIER_2_MIN_DAYS <= duration_days <= self.TIER_2_MAX_DAYS:
            return self.TIER_2_RATE * 100
        elif self.TIER_3_MIN_DAYS <= duration_days <= self.TIER_3_MAX_DAYS:
            return self.TIER_3_RATE * 100
        elif self.TIER_4_MIN_DAYS <= duration_days <= self.TIER_4_MAX_DAYS:
            return self.TIER_4_RATE * 100
        elif self.TIER_5_MIN_DAYS <= duration_days <= self.TIER_5_MAX_DAYS:
            return self.TIER_5_RATE * 100
        elif self.TIER_6_MIN_DAYS <= duration_days <= self.TIER_6_MAX_DAYS:
            return self.TIER_6_RATE * 100
        else:
            return 0  # Invalid duration
    
    def calculate_maturity_amount(self):
        """Calculate total amount at maturity (principal + interest)"""
        if not self.interest_rate:
            return self.amount
        
        duration_days = (self.payback_date - self.start_date).days
        annual_rate = self.interest_rate / 100
        daily_rate = annual_rate / 365
        
        # Convert daily_rate to Decimal to avoid type mismatch with self.amount.amount
        from decimal import Decimal
        daily_rate_decimal = Decimal(str(daily_rate))
        
        interest_earned = self.amount.amount * daily_rate_decimal * duration_days
        return Money(amount=self.amount.amount + interest_earned, currency=self.amount.currency)
    
    @property
    def duration_days(self):
        """Calculate duration in days"""
        if not self.start_date or not self.payback_date:
            return 0
        return (self.payback_date - self.start_date).days
    
    @property
    def days_remaining(self):
        """Calculate days remaining until maturity"""
        if not self.payback_date:
            return 0
        from django.utils import timezone
        today = timezone.now().date()
        remaining = (self.payback_date - today).days
        return max(0, remaining)
    
    @property
    def is_mature(self):
        """Check if the fixed savings has matured"""
        if not self.payback_date:
            return False
        from django.utils import timezone
        today = timezone.now().date()
        return today >= self.payback_date
    
    @property
    def can_be_paid_out(self):
        """Check if the fixed savings can be paid out"""
        return self.is_mature and not self.is_paid_out and self.is_active
    
    def mark_as_matured(self):
        """Mark the fixed savings as matured"""
        if not self.is_mature:
            return False
        
        self.is_matured = True
        self.matured_at = timezone.now()
        self.save()
        return True
    
    def pay_out(self):
        """Pay out the matured amount to user's xysave account"""
        if not self.can_be_paid_out:
            return False
        
        try:
            # Get user's xysave account
            xysave_account = self.user.xysave_account
            
            # Credit the maturity amount to xysave
            xysave_account.balance += self.maturity_amount
            xysave_account.save()
            
            # Create transaction record
            FixedSavingsTransaction.objects.create(
                fixed_savings_account=self,
                transaction_type='maturity_payout',
                amount=self.maturity_amount,
                balance_before=xysave_account.balance - self.maturity_amount,
                balance_after=xysave_account.balance,
                reference=f"FS_PAYOUT_{self.id}",
                description=f"Fixed savings maturity payout - {self.purpose_description or self.get_purpose_display()}",
                interest_earned=self.total_interest_earned
            )
            
            # Mark as paid out
            self.is_paid_out = True
            self.paid_out_at = timezone.now()
            self.save()
            
            return True
        except Exception as e:
            logger.error(f"Error paying out fixed savings {self.id}: {str(e)}")
            return False

class FixedSavingsTransaction(models.Model):
    """
    Fixed Savings Transaction - Track all Fixed Savings activities
    """
    TRANSACTION_TYPES = [
        ('initial_deposit', 'Initial Deposit'),
        ('maturity_payout', 'Maturity Payout'),
        ('early_withdrawal', 'Early Withdrawal'),
        ('interest_credit', 'Interest Credit'),
        ('auto_renewal', 'Auto Renewal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fixed_savings_account = models.ForeignKey(FixedSavingsAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    balance_before = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    balance_after = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN')
    reference = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Interest tracking
    interest_earned = MoneyField(max_digits=19, decimal_places=4, default_currency='NGN', default=0.00)
    interest_rate_applied = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Source tracking for initial deposits
    source_account = models.CharField(max_length=20, choices=FixedSavingsSource.choices, null=True, blank=True)
    source_transaction_id = models.UUIDField(null=True, blank=True, help_text=_('ID of the source transaction'))
    
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Fixed Savings Transaction')
        verbose_name_plural = _('Fixed Savings Transactions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['fixed_savings_account', 'transaction_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.fixed_savings_account.user.username} (₦{self.amount.amount:,.2f})"

class ExampleBankModel(BaseAbstractModel):
    """
    Example model demonstrating usage of BaseAbstractModel.
    This model shows how new models can inherit common fields and functionality.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta(BaseAbstractModel.Meta):
        # Extend the base meta instead of replacing it
        db_table = 'bank_example_model'
        verbose_name = _('Example Bank Model')
        verbose_name_plural = _('Example Bank Models')
        # Add specific indexes for this model
        indexes = [
            models.Index(fields=['name', 'is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name

class FixedSavingsSettings(models.Model):
    """
    Fixed Savings Settings - User preferences for Fixed Savings
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='fixed_savings_settings')
    
    # Notification preferences
    maturity_notifications = models.BooleanField(default=True)
    interest_notifications = models.BooleanField(default=True)
    auto_renewal_notifications = models.BooleanField(default=True)
    
    # Auto-renewal preferences
    default_auto_renewal = models.BooleanField(default=False)
    default_renewal_duration = models.PositiveIntegerField(default=30, help_text=_('Default renewal duration in days'))
    
    # Source preferences
    default_source = models.CharField(
        max_length=10,
        choices=FixedSavingsSource.choices,
        default=FixedSavingsSource.WALLET
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Fixed Savings Settings')
        verbose_name_plural = _('Fixed Savings Settings')
    
    def __str__(self):
        return f"Fixed Savings Settings - {self.user.username}"

