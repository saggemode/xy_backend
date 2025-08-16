from django.db import models
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model
from djmoney.models.fields import MoneyField

User = get_user_model()


class FeeStructure(models.Model):
    """Base model for fee structures"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FeeRule(models.Model):
    """Rules for calculating fees based on various conditions"""
    RULE_TYPES = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage'),
        ('tiered', 'Tiered'),
        ('capped_percentage', 'Capped Percentage'),
        ('minimum_fee', 'Minimum Fee'),
    ]

    TRANSACTION_TYPES = [
        ('all', 'All Transactions'),
        ('transfer', 'Transfer'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('airtime', 'Airtime'),
        ('data', 'Data'),
        ('bill_payment', 'Bill Payment'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='rules')
    name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='all')
    fixed_amount = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN', null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Percentage value (e.g., 2.5 for 2.5%)')
    min_amount = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN', null=True, blank=True, help_text='Minimum transaction amount for this rule to apply')
    max_amount = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN', null=True, blank=True, help_text='Maximum transaction amount for this rule to apply')
    cap_amount = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN', null=True, blank=True, help_text='Maximum fee amount when using capped_percentage')
    min_fee = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN', null=True, blank=True, help_text='Minimum fee to charge')
    priority = models.IntegerField(default=0, help_text='Higher priority rules are evaluated first')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"

    class Meta:
        ordering = ['-priority', 'name']


class DiscountCode(models.Model):
    """Discount codes for fee reductions"""
    DISCOUNT_TYPES = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage'),
        ('waive_fee', 'Waive Fee'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    fixed_amount = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN', null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    max_uses = models.IntegerField(null=True, blank=True, help_text='Maximum number of times this code can be used')
    uses_count = models.IntegerField(default=0, help_text='Number of times this code has been used')
    max_uses_per_user = models.IntegerField(null=True, blank=True, help_text='Maximum number of times a single user can use this code')
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if now < self.valid_from:
            return False
        return True


class DiscountUsage(models.Model):
    """Tracks usage of discount codes by users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discount_code = models.ForeignKey(DiscountCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discount_usages')
    transaction = models.ForeignKey('transactions.Transaction', on_delete=models.SET_NULL, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)
    amount_saved = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN')

    def __str__(self):
        return f"{self.discount_code.code} used by {self.user.username}"


class ReferralProgram(models.Model):
    """Configuration for referral programs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    referrer_reward = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN')
    referee_reward = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN')
    max_referrals_per_user = models.IntegerField(default=10)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Fraud prevention settings
    require_kyc_verification = models.BooleanField(default=True, help_text='Require KYC verification before rewarding referrer')
    minimum_activity_days = models.IntegerField(default=7, help_text='Minimum days of activity before rewarding referrer')
    minimum_transaction_count = models.IntegerField(default=3, help_text='Minimum number of transactions before rewarding referrer')
    minimum_transaction_volume = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN', default=5000.00, help_text='Minimum transaction volume before rewarding referrer')
    ip_address_validation = models.BooleanField(default=True, help_text='Validate that referrer and referee have different IP addresses')
    device_validation = models.BooleanField(default=True, help_text='Validate that referrer and referee have different devices')

    def __str__(self):
        return self.name


class ReferralCode(models.Model):
    """Individual referral codes for users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name='referral_codes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referral_codes')
    code = models.CharField(max_length=20, unique=True)
    times_used = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s referral code: {self.code}"


class Referral(models.Model):
    """Records of referrals between users"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rewarded', 'Rewarded'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name='referrals')
    referral_code = models.ForeignKey(ReferralCode, on_delete=models.CASCADE, related_name='referrals')
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referred_by')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Fraud prevention data
    referrer_ip = models.GenericIPAddressField(null=True, blank=True)
    referee_ip = models.GenericIPAddressField(null=True, blank=True)
    referrer_device_id = models.CharField(max_length=255, null=True, blank=True)
    referee_device_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Tracking dates
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.referrer.username} referred {self.referee.username}"


class SubscriptionPlan(models.Model):
    """Premium subscription plans"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    monthly_fee = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN')
    annual_fee = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PlanBenefit(models.Model):
    """Benefits associated with subscription plans"""
    BENEFIT_TYPES = [
        ('fee_discount', 'Fee Discount'),
        ('transaction_limit', 'Transaction Limit'),
        ('interest_rate_boost', 'Interest Rate Boost'),
        ('feature_access', 'Feature Access'),
        ('support_level', 'Support Level'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='benefits')
    benefit_type = models.CharField(max_length=20, choices=BENEFIT_TYPES)
    name = models.CharField(max_length=100)
    description = models.TextField()
    value = models.CharField(max_length=100, help_text='Value of the benefit (e.g., "50%" for fee discount, "500000" for transaction limit)')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.plan.name} - {self.name}"


class UserSubscription(models.Model):
    """User subscriptions to premium plans"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='subscribers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default='monthly')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

    @property
    def is_active(self):
        now = timezone.now()
        return self.status == 'active' and self.start_date <= now <= self.end_date


class SubscriptionTransaction(models.Model):
    """Transactions related to subscriptions"""
    TRANSACTION_TYPES = [
        ('new', 'New Subscription'),
        ('renewal', 'Renewal'),
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('cancellation', 'Cancellation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = MoneyField(max_digits=10, decimal_places=2, default_currency='NGN')
    payment_reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subscription.user.username} - {self.get_transaction_type_display()}"