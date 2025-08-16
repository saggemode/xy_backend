from rest_framework import serializers
from djmoney.money import Money
from .models import (
    SpendAndSaveAccount, SpendAndSaveTransaction, SpendAndSaveSettings,
    calculate_tiered_interest_rate
)


class SpendAndSaveAccountSerializer(serializers.ModelSerializer):
    """Serializer for Spend and Save Account"""
    balance = serializers.SerializerMethodField()
    total_interest_earned = serializers.SerializerMethodField()
    total_saved_from_spending = serializers.SerializerMethodField()
    min_transaction_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = SpendAndSaveAccount
        fields = [
            'id', 'account_number', 'balance', 'is_active', 'savings_percentage',
            'total_interest_earned', 'total_saved_from_spending', 'total_transactions_processed',
            'last_auto_save_date', 'default_withdrawal_destination', 'min_transaction_amount',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'account_number', 'balance', 'total_interest_earned', 
                           'total_saved_from_spending', 'total_transactions_processed', 
                           'last_auto_save_date', 'created_at', 'updated_at']
    
    def get_balance(self, obj):
        return str(obj.balance)
    
    def get_total_interest_earned(self, obj):
        return str(obj.total_interest_earned)
    
    def get_total_saved_from_spending(self, obj):
        return str(obj.total_saved_from_spending)
    
    def get_min_transaction_amount(self, obj):
        return str(obj.min_transaction_amount)


class SpendAndSaveTransactionSerializer(serializers.ModelSerializer):
    """Serializer for Spend and Save Transactions"""
    amount = serializers.SerializerMethodField()
    balance_before = serializers.SerializerMethodField()
    balance_after = serializers.SerializerMethodField()
    original_transaction_amount = serializers.SerializerMethodField()
    interest_earned = serializers.SerializerMethodField()
    
    class Meta:
        model = SpendAndSaveTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'balance_before', 'balance_after',
            'reference', 'description', 'original_transaction_id', 'original_transaction_amount',
            'savings_percentage_applied', 'withdrawal_destination', 'destination_account',
            'interest_earned', 'interest_breakdown', 'created_at'
        ]
        read_only_fields = ['id', 'reference', 'created_at']
    
    def get_amount(self, obj):
        return str(obj.amount)
    
    def get_balance_before(self, obj):
        return str(obj.balance_before)
    
    def get_balance_after(self, obj):
        return str(obj.balance_after)
    
    def get_original_transaction_amount(self, obj):
        return str(obj.original_transaction_amount) if obj.original_transaction_amount else None
    
    def get_interest_earned(self, obj):
        return str(obj.interest_earned)


class SpendAndSaveSettingsSerializer(serializers.ModelSerializer):
    """Serializer for Spend and Save Settings"""
    min_transaction_threshold = serializers.SerializerMethodField()
    
    class Meta:
        model = SpendAndSaveSettings
        fields = [
            'id', 'auto_save_notifications', 'interest_notifications', 'withdrawal_notifications',
            'preferred_savings_percentage', 'min_transaction_threshold', 'default_withdrawal_destination',
            'interest_payout_frequency', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_min_transaction_threshold(self, obj):
        return str(obj.min_transaction_threshold)


class ActivateSpendAndSaveSerializer(serializers.Serializer):
    """Serializer for activating Spend and Save"""
    savings_percentage = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2,
        min_value=1.0,
        max_value=50.0,
        help_text="Percentage of daily spending to automatically save (1-50%)"
    )
    fund_source = serializers.ChoiceField(
        choices=[('wallet', 'Wallet'), ('xysave', 'XySave Account'), ('both', 'Both Wallet and XySave')],
        help_text="Source of funds for initial Spend and Save account setup"
    )
    initial_amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=0.01,
        required=False,
        default=0.00,
        help_text="Initial amount to transfer from fund source (optional)"
    )
    wallet_amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=0.01,
        required=False,
        help_text="Amount to transfer from wallet (required when fund_source is 'both')"
    )
    xysave_amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=0.01,
        required=False,
        help_text="Amount to transfer from XySave account (required when fund_source is 'both')"
    )
    terms_accepted = serializers.BooleanField(
        required=True,
        help_text="Must be true to accept terms and conditions"
    )
    
    def validate_terms_accepted(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions to activate Spend and Save")
        return value
    
    def validate(self, data):
        """Validate fund source and initial amount"""
        fund_source = data.get('fund_source', 'wallet')
        initial_amount = data.get('initial_amount', 0.00)
        wallet_amount = data.get('wallet_amount', 0.00)
        xysave_amount = data.get('xysave_amount', 0.00)
        
        user = self.context['request'].user
        
        if fund_source == 'both':
            # Validate both amounts are provided
            if not wallet_amount and not xysave_amount:
                raise serializers.ValidationError(
                    "When fund_source is 'both', you must provide either wallet_amount or xysave_amount or both"
                )
            
            # Check wallet balance if wallet_amount is provided
            if wallet_amount > 0:
                try:
                    from bank.models import Wallet
                    wallet = Wallet.objects.get(user=user)
                    if wallet.balance.amount < wallet_amount:
                        raise serializers.ValidationError(
                            f"Insufficient wallet balance. Available: {wallet.balance}, Required: {wallet_amount}"
                        )
                except Wallet.DoesNotExist:
                    raise serializers.ValidationError("Wallet not found for user")
            
            # Check XySave balance if xysave_amount is provided
            if xysave_amount > 0:
                try:
                    from bank.models import XySaveAccount
                    xysave_account = XySaveAccount.objects.get(user=user)
                    if xysave_account.balance.amount < xysave_amount:
                        raise serializers.ValidationError(
                            f"Insufficient XySave balance. Available: {xysave_account.balance}, Required: {xysave_amount}"
                        )
                except XySaveAccount.DoesNotExist:
                    raise serializers.ValidationError("XySave account not found for user")
        
        elif initial_amount > 0:
            # Check if user has sufficient funds in the chosen source
            if fund_source == 'wallet':
                try:
                    from bank.models import Wallet
                    wallet = Wallet.objects.get(user=user)
                    if wallet.balance.amount < initial_amount:
                        raise serializers.ValidationError(
                            f"Insufficient wallet balance. Available: {wallet.balance}, Required: {initial_amount}"
                        )
                except Wallet.DoesNotExist:
                    raise serializers.ValidationError("Wallet not found for user")
                    
            elif fund_source == 'xysave':
                try:
                    from bank.models import XySaveAccount
                    xysave_account = XySaveAccount.objects.get(user=user)
                    if xysave_account.balance.amount < initial_amount:
                        raise serializers.ValidationError(
                            f"Insufficient XySave balance. Available: {xysave_account.balance}, Required: {initial_amount}"
                        )
                except XySaveAccount.DoesNotExist:
                    raise serializers.ValidationError("XySave account not found for user")
        
        return data


class DeactivateSpendAndSaveSerializer(serializers.Serializer):
    """Serializer for deactivating Spend and Save"""
    confirm_deactivation = serializers.BooleanField(
        required=True,
        help_text="Must be true to confirm deactivation"
    )
    
    def validate_confirm_deactivation(self, value):
        if not value:
            raise serializers.ValidationError("You must confirm deactivation")
        return value


class WithdrawFromSpendAndSaveSerializer(serializers.Serializer):
    """Serializer for withdrawing from Spend and Save"""
    amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=0.01,
        help_text="Amount to withdraw"
    )
    destination = serializers.ChoiceField(
        choices=[('wallet', 'Wallet'), ('xysave', 'XySave Account')],
        default='wallet',
        help_text="Destination for withdrawal"
    )
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class UpdateSpendAndSaveSettingsSerializer(serializers.Serializer):
    """Serializer for updating Spend and Save settings"""
    auto_save_notifications = serializers.BooleanField(required=False)
    interest_notifications = serializers.BooleanField(required=False)
    withdrawal_notifications = serializers.BooleanField(required=False)
    preferred_savings_percentage = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2,
        min_value=1.0,
        max_value=50.0,
        required=False
    )
    min_transaction_threshold = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=0.01,
        required=False
    )
    default_withdrawal_destination = serializers.ChoiceField(
        choices=[('wallet', 'Wallet'), ('xysave', 'XySave Account')],
        required=False
    )
    interest_payout_frequency = serializers.ChoiceField(
        choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')],
        required=False
    )


class SpendAndSaveAccountSummarySerializer(serializers.Serializer):
    """Serializer for comprehensive Spend and Save account summary"""
    account = SpendAndSaveAccountSerializer()
    settings = SpendAndSaveSettingsSerializer()
    interest_breakdown = serializers.DictField()
    recent_transactions = SpendAndSaveTransactionSerializer(many=True)


class InterestForecastSerializer(serializers.Serializer):
    """Serializer for interest forecast"""
    daily_interest = serializers.CharField()
    monthly_interest = serializers.CharField()
    annual_interest = serializers.CharField()
    forecast_days = serializers.IntegerField()
    current_balance = serializers.CharField()
    interest_breakdown = serializers.DictField()


class TieredInterestBreakdownSerializer(serializers.Serializer):
    """Serializer for tiered interest breakdown"""
    tier_1 = serializers.DictField()
    tier_2 = serializers.DictField()
    tier_3 = serializers.DictField()
    total_interest = serializers.FloatField()


class SpendAndSaveDashboardSerializer(serializers.Serializer):
    """Serializer for Spend and Save dashboard data"""
    account_summary = SpendAndSaveAccountSummarySerializer()
    interest_forecast = InterestForecastSerializer()
    tiered_rates_info = serializers.DictField()
    recent_activity = SpendAndSaveTransactionSerializer(many=True)
    savings_progress = serializers.DictField()


class ProcessSpendingTransactionSerializer(serializers.Serializer):
    """Serializer for processing spending transactions"""
    transaction_id = serializers.UUIDField(help_text="ID of the spending transaction to process")
    
    def validate_transaction_id(self, value):
        from .models import Transaction
        try:
            transaction = Transaction.objects.get(id=value)
            if transaction.type != 'debit':
                raise serializers.ValidationError("Only debit transactions can be processed for auto-save")
        except Transaction.DoesNotExist:
            raise serializers.ValidationError("Transaction not found")
        return value


class SpendAndSaveStatisticsSerializer(serializers.Serializer):
    """Serializer for Spend and Save statistics"""
    total_users = serializers.IntegerField()
    active_accounts = serializers.IntegerField()
    total_saved_amount = serializers.CharField()
    total_interest_paid = serializers.CharField()
    average_savings_percentage = serializers.FloatField()
    total_transactions_processed = serializers.IntegerField()
    daily_interest_payouts = serializers.IntegerField()
    monthly_growth_rate = serializers.FloatField()


class InterestCalculationSerializer(serializers.Serializer):
    """Serializer for interest calculation requests"""
    balance_amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=4,
        min_value=0,
        help_text="Balance amount to calculate interest for"
    )
    
    def to_representation(self, instance):
        """Convert balance to Money and calculate tiered interest"""
        balance = Money(instance['balance_amount'], 'NGN')
        breakdown = calculate_tiered_interest_rate(balance.amount)
        
        return {
            'balance_amount': str(balance),
            'daily_interest': breakdown['total_interest'],
            'monthly_interest': breakdown['total_interest'] * 30,
            'annual_interest': breakdown['total_interest'] * 365,
            'tier_breakdown': breakdown
        } 