from rest_framework import serializers
from djmoney.contrib.django_rest_framework import MoneyField
from djmoney.money import Money
from .models import (
    XySaveAccount, XySaveTransaction, XySaveGoal, 
    XySaveInvestment, XySaveSettings
)


class XySaveAccountSerializer(serializers.ModelSerializer):
    """Serializer for XySave Account"""
    balance = MoneyField(max_digits=19, decimal_places=4)
    total_interest_earned = MoneyField(max_digits=19, decimal_places=4)
    daily_interest = serializers.SerializerMethodField()
    annual_interest_rate = serializers.SerializerMethodField()
    account_number_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XySaveAccount
        fields = [
            'id', 'account_number', 'account_number_display', 'balance', 
            'total_interest_earned', 'daily_interest_rate', 'annual_interest_rate',
            'daily_interest', 'is_active', 'auto_save_enabled', 'auto_save_percentage',
            'auto_save_min_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'account_number', 'balance', 'total_interest_earned',
            'daily_interest_rate', 'is_active', 'created_at', 'updated_at'
        ]
    
    def get_daily_interest(self, obj):
        """Get calculated daily interest"""
        daily_interest = obj.calculate_daily_interest()
        return str(daily_interest)
    
    def get_annual_interest_rate(self, obj):
        """Get annual interest rate"""
        return obj.get_annual_interest_rate()
    
    def get_account_number_display(self, obj):
        """Get formatted account number for display"""
        return f"XS-{obj.account_number[:4]}-{obj.account_number[4:8]}-{obj.account_number[8:]}"


class XySaveTransactionSerializer(serializers.ModelSerializer):
    """Serializer for XySave Transaction"""
    amount = MoneyField(max_digits=19, decimal_places=4)
    balance_before = MoneyField(max_digits=19, decimal_places=4)
    balance_after = MoneyField(max_digits=19, decimal_places=4)
    transaction_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XySaveTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display', 'amount',
            'balance_before', 'balance_after', 'reference', 'description',
            'metadata', 'created_at'
        ]
        read_only_fields = [
            'id', 'balance_before', 'balance_after', 'reference',
            'metadata', 'created_at'
        ]
    
    def get_transaction_type_display(self, obj):
        """Get human-readable transaction type"""
        return dict(XySaveTransaction.TRANSACTION_TYPES).get(obj.transaction_type, obj.transaction_type)


class XySaveGoalSerializer(serializers.ModelSerializer):
    """Serializer for XySave Goal"""
    target_amount = MoneyField(max_digits=19, decimal_places=4)
    current_amount = MoneyField(max_digits=19, decimal_places=4)
    progress_percentage = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    
    class Meta:
        model = XySaveGoal
        fields = [
            'id', 'name', 'target_amount', 'current_amount', 'target_date',
            'is_active', 'progress_percentage', 'is_completed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_amount', 'progress_percentage', 'is_completed', 'created_at', 'updated_at']
    
    def get_progress_percentage(self, obj):
        """Get progress percentage"""
        return obj.get_progress_percentage()
    
    def get_is_completed(self, obj):
        """Check if goal is completed"""
        return obj.is_completed()


class XySaveInvestmentSerializer(serializers.ModelSerializer):
    """Serializer for XySave Investment"""
    amount_invested = MoneyField(max_digits=19, decimal_places=4)
    current_value = MoneyField(max_digits=19, decimal_places=4)
    return_percentage = serializers.SerializerMethodField()
    investment_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XySaveInvestment
        fields = [
            'id', 'investment_type', 'investment_type_display', 'amount_invested',
            'current_value', 'expected_return_rate', 'return_percentage',
            'maturity_date', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'current_value', 'return_percentage', 'created_at', 'updated_at'
        ]
    
    def get_return_percentage(self, obj):
        """Get current return percentage"""
        return obj.get_return_percentage()
    
    def get_investment_type_display(self, obj):
        """Get human-readable investment type"""
        return dict(XySaveInvestment.INVESTMENT_TYPES).get(obj.investment_type, obj.investment_type)


class XySaveSettingsSerializer(serializers.ModelSerializer):
    """Serializer for XySave Settings"""
    
    class Meta:
        model = XySaveSettings
        fields = [
            'id', 'daily_interest_notifications', 'goal_reminders',
            'auto_save_notifications', 'investment_updates',
            'preferred_interest_payout', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class XySaveAccountSummarySerializer(serializers.Serializer):
    """Serializer for XySave Account Summary"""
    account = XySaveAccountSerializer()
    settings = XySaveSettingsSerializer()
    daily_interest = serializers.CharField()
    annual_interest_rate = serializers.FloatField()
    recent_transactions = XySaveTransactionSerializer(many=True)
    active_goals = XySaveGoalSerializer(many=True)
    investments = XySaveInvestmentSerializer(many=True)
    total_invested = serializers.DecimalField(max_digits=19, decimal_places=4)
    total_investment_value = serializers.DecimalField(max_digits=19, decimal_places=4)


class XySaveDepositSerializer(serializers.Serializer):
    """Serializer for XySave deposit request"""
    amount = MoneyField(max_digits=19, decimal_places=4)
    description = serializers.CharField(max_length=255, required=False, default="Deposit to XySave")
    
    def validate_amount(self, value):
        """Validate deposit amount"""
        if value.amount <= 0:
            raise serializers.ValidationError("Deposit amount must be positive")
        return value


class XySaveWithdrawalSerializer(serializers.Serializer):
    """Serializer for XySave withdrawal request"""
    amount = MoneyField(max_digits=19, decimal_places=4)
    description = serializers.CharField(max_length=255, required=False, default="Withdrawal from XySave")
    
    def validate_amount(self, value):
        """Validate withdrawal amount"""
        if value.amount <= 0:
            raise serializers.ValidationError("Withdrawal amount must be positive")
        return value


class XySaveAutoSaveSerializer(serializers.Serializer):
    """Serializer for XySave auto-save configuration"""
    enabled = serializers.BooleanField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=1, max_value=100, required=False)
    min_amount = MoneyField(max_digits=19, decimal_places=4, required=False)
    
    def validate(self, data):
        """Validate auto-save configuration"""
        if data.get('enabled'):
            # Provide sensible defaults if not supplied
            if 'percentage' not in data or data.get('percentage') is None:
                data['percentage'] = 100
            if 'min_amount' not in data or data.get('min_amount') is None:
                data['min_amount'] = Money(0, 'NGN')
        return data


class XySaveGoalCreateSerializer(serializers.Serializer):
    """Serializer for creating XySave goal"""
    name = serializers.CharField(max_length=100)
    target_amount = MoneyField(max_digits=19, decimal_places=4)
    target_date = serializers.DateField(required=False)
    
    def validate_target_amount(self, value):
        """Validate target amount"""
        if value.amount <= 0:
            raise serializers.ValidationError("Target amount must be positive")
        return value


class XySaveInvestmentCreateSerializer(serializers.Serializer):
    """Serializer for creating XySave investment"""
    investment_type = serializers.ChoiceField(choices=XySaveInvestment.INVESTMENT_TYPES)
    amount_invested = MoneyField(max_digits=19, decimal_places=4)
    expected_return_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)
    maturity_date = serializers.DateField(required=False)
    
    def validate_amount_invested(self, value):
        """Validate investment amount"""
        if value.amount <= 0:
            raise serializers.ValidationError("Investment amount must be positive")
        return value


class XySaveInterestForecastSerializer(serializers.Serializer):
    """Serializer for XySave interest forecast"""
    daily_interest = serializers.CharField()
    weekly_interest = serializers.CharField()
    monthly_interest = serializers.CharField()
    yearly_interest = serializers.CharField()
    annual_rate = serializers.FloatField()
    current_balance = serializers.CharField()
    total_interest_earned = serializers.CharField()


class XySaveDashboardSerializer(serializers.Serializer):
    """Serializer for XySave dashboard data"""
    account_summary = XySaveAccountSummarySerializer()
    interest_forecast = XySaveInterestForecastSerializer()
    recent_activity = XySaveTransactionSerializer(many=True)
    goals_progress = XySaveGoalSerializer(many=True)
    investment_portfolio = XySaveInvestmentSerializer(many=True) 