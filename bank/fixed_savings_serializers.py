from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError
from djmoney.money import Money
from .models import (
    FixedSavingsAccount, FixedSavingsTransaction, FixedSavingsSettings,
    FixedSavingsSource, FixedSavingsPurpose
)
from .fixed_savings_services import FixedSavingsService

class FixedSavingsPurposeSerializer(serializers.Serializer):
    """Serializer for Fixed Savings Purpose choices"""
    value = serializers.CharField()
    label = serializers.CharField()

class FixedSavingsSourceSerializer(serializers.Serializer):
    """Serializer for Fixed Savings Source choices"""
    value = serializers.CharField()
    label = serializers.CharField()

class FixedSavingsAccountSerializer(serializers.ModelSerializer):
    """Serializer for Fixed Savings Account"""
    user = serializers.ReadOnlyField(source='user.username')
    user_id = serializers.ReadOnlyField(source='user.id')
    purpose_display = serializers.ReadOnlyField(source='get_purpose_display')
    source_display = serializers.ReadOnlyField(source='get_source_display')
    duration_days = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    is_mature = serializers.ReadOnlyField()
    can_be_paid_out = serializers.ReadOnlyField()
    
    class Meta:
        model = FixedSavingsAccount
        fields = [
            'id', 'user', 'user_id', 'account_number', 'amount', 'source', 'source_display',
            'purpose', 'purpose_display', 'purpose_description', 'start_date', 'payback_date',
            'auto_renewal_enabled', 'is_active', 'is_matured', 'is_paid_out',
            'interest_rate', 'total_interest_earned', 'maturity_amount',
            'duration_days', 'days_remaining', 'is_mature', 'can_be_paid_out',
            'created_at', 'updated_at', 'matured_at', 'paid_out_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_id', 'account_number', 'interest_rate', 
            'total_interest_earned', 'maturity_amount', 'duration_days', 
            'days_remaining', 'is_mature', 'can_be_paid_out', 'created_at', 
            'updated_at', 'matured_at', 'paid_out_at'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Format Money fields as strings to avoid DRF Decimal parsing issues
        if hasattr(instance, 'amount') and instance.amount is not None:
            data['amount'] = f"{instance.amount.currency}{instance.amount.amount:,.2f}"
        if hasattr(instance, 'total_interest_earned') and instance.total_interest_earned is not None:
            data['total_interest_earned'] = f"{instance.total_interest_earned.currency}{instance.total_interest_earned.amount:,.2f}"
        if hasattr(instance, 'maturity_amount') and instance.maturity_amount is not None:
            data['maturity_amount'] = f"{instance.maturity_amount.currency}{instance.maturity_amount.amount:,.2f}"
        return data

class FixedSavingsAccountCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Fixed Savings Account"""
    amount = serializers.DecimalField(max_digits=19, decimal_places=2, min_value=1000)
    start_date = serializers.DateField()
    payback_date = serializers.DateField()
    
    class Meta:
        model = FixedSavingsAccount
        fields = [
            'amount', 'source', 'purpose', 'purpose_description', 
            'start_date', 'payback_date', 'auto_renewal_enabled'
        ]
    
    def validate(self, data):
        """Validate fixed savings creation data"""
        amount = data.get('amount')
        start_date = data.get('start_date')
        payback_date = data.get('payback_date')
        source = data.get('source')
        
        # Validate minimum amount
        if amount < 1000:
            raise ValidationError("Minimum fixed savings amount is ₦1,000")
        
        # Validate dates
        today = timezone.now().date()
        if start_date < today:
            raise ValidationError("Start date cannot be in the past")
        
        if payback_date <= start_date:
            raise ValidationError("Payback date must be after start date")
        
        # Validate duration (minimum 7 days, maximum 1000 days)
        duration_days = (payback_date - start_date).days
        if duration_days < 7:
            raise ValidationError("Minimum duration is 7 days")
        if duration_days > 1000:
            raise ValidationError("Maximum duration is 1000 days")
        
        # Validate user has sufficient funds
        user = self.context['request'].user
        if not FixedSavingsService._validate_sufficient_funds(user, Money(amount=amount, currency='NGN'), source):
            raise ValidationError("Insufficient funds for fixed savings")
        
        return data
    
    def create(self, validated_data):
        """Create fixed savings account"""
        user = self.context['request'].user
        amount = Money(amount=validated_data['amount'], currency='NGN')
        
        return FixedSavingsService.create_fixed_savings(
            user=user,
            amount=amount,
            source=validated_data['source'],
            purpose=validated_data['purpose'],
            purpose_description=validated_data.get('purpose_description', ''),
            start_date=validated_data['start_date'],
            payback_date=validated_data['payback_date'],
            auto_renewal_enabled=validated_data.get('auto_renewal_enabled', False)
        )

    def to_representation(self, instance):
        # After creation, return the full account representation
        return FixedSavingsAccountSerializer(instance).data

class FixedSavingsAccountDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Fixed Savings Account"""
    user = serializers.ReadOnlyField(source='user.username')
    user_id = serializers.ReadOnlyField(source='user.id')
    purpose_display = serializers.ReadOnlyField(source='get_purpose_display')
    source_display = serializers.ReadOnlyField(source='get_source_display')
    duration_days = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    is_mature = serializers.ReadOnlyField()
    can_be_paid_out = serializers.ReadOnlyField()
    transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = FixedSavingsAccount
        fields = [
            'id', 'user', 'user_id', 'account_number', 'amount', 'source', 'source_display',
            'purpose', 'purpose_display', 'purpose_description', 'start_date', 'payback_date',
            'auto_renewal_enabled', 'is_active', 'is_matured', 'is_paid_out',
            'interest_rate', 'total_interest_earned', 'maturity_amount',
            'duration_days', 'days_remaining', 'is_mature', 'can_be_paid_out',
            'created_at', 'updated_at', 'matured_at', 'paid_out_at', 'transactions'
        ]
    
    def get_transactions(self, obj):
        """Get recent transactions for the fixed savings account"""
        transactions = obj.transactions.all()[:10]  # Last 10 transactions
        return FixedSavingsTransactionSerializer(transactions, many=True).data

class FixedSavingsTransactionSerializer(serializers.ModelSerializer):
    """Serializer for Fixed Savings Transaction"""
    fixed_savings_account = serializers.ReadOnlyField(source='fixed_savings_account.id')
    transaction_type_display = serializers.ReadOnlyField(source='get_transaction_type_display')
    source_account_display = serializers.ReadOnlyField(source='get_source_account_display')
    
    class Meta:
        model = FixedSavingsTransaction
        fields = [
            'id', 'fixed_savings_account', 'transaction_type', 'transaction_type_display',
            'amount', 'balance_before', 'balance_after', 'reference', 'description',
            'interest_earned', 'interest_rate_applied', 'source_account', 'source_account_display',
            'source_transaction_id', 'metadata', 'created_at'
        ]
        read_only_fields = [
            'id', 'fixed_savings_account', 'balance_before', 'balance_after', 
            'reference', 'interest_earned', 'interest_rate_applied', 'created_at'
        ]

class FixedSavingsSettingsSerializer(serializers.ModelSerializer):
    """Serializer for Fixed Savings Settings"""
    user = serializers.ReadOnlyField(source='user.username')
    default_source_display = serializers.ReadOnlyField(source='get_default_source_display')
    
    class Meta:
        model = FixedSavingsSettings
        fields = [
            'id', 'user', 'maturity_notifications', 'interest_notifications', 
            'auto_renewal_notifications', 'default_auto_renewal', 'default_renewal_duration',
            'default_source', 'default_source_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

class FixedSavingsSummarySerializer(serializers.Serializer):
    """Serializer for Fixed Savings Summary"""
    total_active_fixed_savings = serializers.IntegerField()
    total_active_amount = serializers.CharField()
    total_maturity_amount = serializers.CharField()
    total_interest_earned = serializers.CharField()
    matured_unpaid_count = serializers.IntegerField()
    matured_unpaid_amount = serializers.DecimalField(max_digits=19, decimal_places=2)

class FixedSavingsPayoutSerializer(serializers.Serializer):
    """Serializer for Fixed Savings Payout"""
    fixed_savings_id = serializers.UUIDField()
    
    def validate_fixed_savings_id(self, value):
        """Validate fixed savings exists and can be paid out"""
        try:
            fixed_savings = FixedSavingsAccount.objects.get(id=value)
            if not fixed_savings.can_be_paid_out:
                raise ValidationError("Fixed savings cannot be paid out")
            return value
        except FixedSavingsAccount.DoesNotExist:
            raise ValidationError("Fixed savings account not found")

class FixedSavingsAutoRenewalSerializer(serializers.Serializer):
    """Serializer for Fixed Savings Auto-Renewal"""
    fixed_savings_id = serializers.UUIDField()
    
    def validate_fixed_savings_id(self, value):
        """Validate fixed savings exists and can be auto-renewed"""
        try:
            fixed_savings = FixedSavingsAccount.objects.get(id=value)
            if not fixed_savings.auto_renewal_enabled:
                raise ValidationError("Auto-renewal is not enabled for this fixed savings")
            if not fixed_savings.is_mature:
                raise ValidationError("Fixed savings has not matured yet")
            return value
        except FixedSavingsAccount.DoesNotExist:
            raise ValidationError("Fixed savings account not found")

class FixedSavingsInterestRateSerializer(serializers.Serializer):
    """Serializer for Fixed Savings Interest Rate calculation"""
    amount = serializers.DecimalField(max_digits=19, decimal_places=2, min_value=1000)
    start_date = serializers.DateField()
    payback_date = serializers.DateField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    maturity_amount = serializers.CharField(read_only=True)
    interest_earned = serializers.CharField(read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    
    def validate(self, data):
        """Validate interest rate calculation data"""
        start_date = data.get('start_date')
        payback_date = data.get('payback_date')
        
        # Validate dates
        today = timezone.now().date()
        if start_date < today:
            raise ValidationError("Start date cannot be in the past")
        
        if payback_date <= start_date:
            raise ValidationError("Payback date must be after start date")
        
        # Validate duration
        duration_days = (payback_date - start_date).days
        if duration_days < 7:
            raise ValidationError("Minimum duration is 7 days")
        if duration_days > 1000:
            raise ValidationError("Maximum duration is 1000 days")
        
        return data
    
    def to_representation(self, instance):
        """Calculate and return interest rate information"""
        data = super().to_representation(instance)
        
        # Create a temporary fixed savings object to calculate rates
        temp_fixed_savings = FixedSavingsAccount(
            amount=Money(amount=data['amount'], currency='NGN'),
            start_date=data['start_date'],
            payback_date=data['payback_date']
        )
        
        # Calculate interest rate and maturity amount
        interest_rate = temp_fixed_savings.calculate_interest_rate()
        maturity_amount = temp_fixed_savings.calculate_maturity_amount()
        interest_earned = maturity_amount - temp_fixed_savings.amount
        duration_days = temp_fixed_savings.duration_days
        
        data['interest_rate'] = interest_rate
        data['maturity_amount'] = f"₦{maturity_amount:,.2f}"
        data['interest_earned'] = f"₦{interest_earned:,.2f}"
        data['duration_days'] = duration_days
        
        return data

class FixedSavingsChoicesSerializer(serializers.Serializer):
    """Serializer for Fixed Savings choices"""
    purposes = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()
    
    def get_purposes(self, obj):
        """Get purpose choices"""
        return [
            {'value': choice[0], 'label': choice[1]} 
            for choice in FixedSavingsPurpose.choices
        ]
    
    def get_sources(self, obj):
        """Get source choices"""
        return [
            {'value': choice[0], 'label': choice[1]} 
            for choice in FixedSavingsSource.choices
        ] 