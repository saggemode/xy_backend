from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, date
from .models import TargetSaving, TargetSavingDeposit, TargetSavingCategory, TargetSavingFrequency


class TargetSavingDepositSerializer(serializers.ModelSerializer):
    """Serializer for TargetSavingDeposit model"""
    
    class Meta:
        model = TargetSavingDeposit
        fields = [
            'id', 'target_saving', 'amount', 'deposit_date', 'notes'
        ]
        read_only_fields = ['id', 'deposit_date']
    
    def validate_amount(self, value):
        """Validate deposit amount"""
        if value <= 0:
            raise serializers.ValidationError("Deposit amount must be greater than zero")
        return value


class TargetSavingSerializer(serializers.ModelSerializer):
    """Serializer for TargetSaving model"""
    
    # Computed fields
    progress_percentage = serializers.ReadOnlyField()
    remaining_amount = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    daily_target = serializers.ReadOnlyField()
    weekly_target = serializers.ReadOnlyField()
    monthly_target = serializers.ReadOnlyField()
    
    # Category and frequency display
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    
    # Recent deposits
    recent_deposits = TargetSavingDepositSerializer(many=True, read_only=True)
    total_deposits = serializers.ReadOnlyField()
    
    class Meta:
        model = TargetSaving
        fields = [
            'id', 'user', 'name', 'category', 'category_display',
            'target_amount', 'frequency', 'frequency_display',
            'preferred_deposit_day', 'start_date', 'end_date',
            'current_amount', 'is_active', 'is_completed',
            'progress_percentage', 'remaining_amount', 'days_remaining',
            'is_overdue', 'daily_target', 'weekly_target', 'monthly_target',
            'recent_deposits', 'total_deposits', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'current_amount', 'is_completed',
            'progress_percentage', 'remaining_amount', 'days_remaining',
            'is_overdue', 'daily_target', 'weekly_target', 'monthly_target',
            'recent_deposits', 'total_deposits', 'created_at', 'updated_at'
        ]
    
    def validate_target_amount(self, value):
        """Validate target amount"""
        if value <= 0:
            raise serializers.ValidationError("Target amount must be greater than zero")
        return value
    
    def validate_end_date(self, value):
        """Validate end date"""
        if value <= timezone.now().date():
            raise serializers.ValidationError("End date must be in the future")
        return value
    
    def validate_start_date(self, value):
        """Validate start date"""
        if value < timezone.now().date():
            raise serializers.ValidationError("Start date cannot be in the past")
        return value
    
    def validate(self, data):
        """Validate the entire data set"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        frequency = data.get('frequency')
        preferred_deposit_day = data.get('preferred_deposit_day')
        
        # Validate date range
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError({
                'end_date': "End date must be after start date"
            })
        
        # Validate frequency and preferred deposit day
        if frequency in [TargetSavingFrequency.WEEKLY, TargetSavingFrequency.MONTHLY]:
            if not preferred_deposit_day:
                raise serializers.ValidationError({
                    'preferred_deposit_day': "Preferred deposit day is required for weekly/monthly frequency"
                })
        
        return data
    
    def to_representation(self, instance):
        """Custom representation with additional computed fields"""
        data = super().to_representation(instance)
        
        # Add computed fields
        data['progress_percentage'] = float(instance.progress_percentage)
        data['remaining_amount'] = float(instance.remaining_amount)
        data['days_remaining'] = instance.days_remaining
        data['is_overdue'] = instance.is_overdue
        data['daily_target'] = float(instance.daily_target)
        data['weekly_target'] = float(instance.weekly_target)
        data['monthly_target'] = float(instance.monthly_target)
        
        # Add recent deposits (limit to 5)
        recent_deposits = instance.deposits.all()[:5]
        data['recent_deposits'] = TargetSavingDepositSerializer(recent_deposits, many=True).data
        data['total_deposits'] = instance.deposits.count()
        
        return data


class TargetSavingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetSaving
        fields = ['name', 'category', 'target_amount', 'frequency', 'source', 'start_date','end_date']

    def validate_source(self, value):
        if value not in ['wallet', 'xysave', 'both']:
            raise serializers.ValidationError('Invalid funding source')
        return value
    
    def validate_target_amount(self, value):
        """Validate target amount"""
        if value <= 0:
            raise serializers.ValidationError("Target amount must be greater than zero")
        if value > 1000000000:  # 1 billion limit
            raise serializers.ValidationError("Target amount is too high")
        return value
    
    def validate_name(self, value):
        """Validate target name"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Target name must be at least 3 characters long")
        if len(value) > 255:
            raise serializers.ValidationError("Target name is too long")
        return value.strip()
    
    def validate(self, data):
        """Validate the entire data set"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        frequency = data.get('frequency')
        preferred_deposit_day = data.get('preferred_deposit_day')
        
        # Validate date range
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError({
                    'end_date': "End date must be after start date"
                })
            
            # Check if the date range is reasonable (not too long)
            days_diff = (end_date - start_date).days
            if days_diff > 3650:  # 10 years
                raise serializers.ValidationError({
                    'end_date': "Target period cannot exceed 10 years"
                })
            if days_diff < 1:  # At least 1 day
                raise serializers.ValidationError({
                    'end_date': "Target period must be at least 1 day"
                })
        
        # Validate frequency and preferred deposit day
        if frequency in [TargetSavingFrequency.WEEKLY, TargetSavingFrequency.MONTHLY]:
            if not preferred_deposit_day:
                raise serializers.ValidationError({
                    'preferred_deposit_day': "Preferred deposit day is required for weekly/monthly frequency"
                })
        
        return data


class TargetSavingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating target savings"""
    
    class Meta:
        model = TargetSaving
        fields = [
            'name', 'category', 'target_amount', 'frequency',
            'preferred_deposit_day', 'start_date', 'end_date'
        ]
    
    def validate_target_amount(self, value):
        """Validate target amount"""
        if value <= 0:
            raise serializers.ValidationError("Target amount must be greater than zero")
        if value > 1000000000:  # 1 billion limit
            raise serializers.ValidationError("Target amount is too high")
        return value
    
    def validate(self, data):
        """Validate the entire data set"""
        instance = self.instance
        
        # Don't allow updates if target is completed
        if instance.is_completed:
            raise serializers.ValidationError("Cannot update a completed target saving")
        
        start_date = data.get('start_date', instance.start_date)
        end_date = data.get('end_date', instance.end_date)
        frequency = data.get('frequency', instance.frequency)
        preferred_deposit_day = data.get('preferred_deposit_day', instance.preferred_deposit_day)
        
        # Validate date range
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError({
                    'end_date': "End date must be after start date"
                })
            
            # Check if the date range is reasonable
            days_diff = (end_date - start_date).days
            if days_diff > 3650:  # 10 years
                raise serializers.ValidationError({
                    'end_date': "Target period cannot exceed 10 years"
                })
            if days_diff < 1:  # At least 1 day
                raise serializers.ValidationError({
                    'end_date': "Target period must be at least 1 day"
                })
        
        # Validate frequency and preferred deposit day
        if frequency in [TargetSavingFrequency.WEEKLY, TargetSavingFrequency.MONTHLY]:
            if not preferred_deposit_day:
                raise serializers.ValidationError({
                    'preferred_deposit_day': "Preferred deposit day is required for weekly/monthly frequency"
                })
        
        return data


class TargetSavingDepositCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating deposits"""
    
    class Meta:
        model = TargetSavingDeposit
        fields = ['amount', 'notes']
    
    def validate_amount(self, value):
        """Validate deposit amount"""
        if value <= 0:
            raise serializers.ValidationError("Deposit amount must be greater than zero")
        if value > 100000000:  # 100 million limit
            raise serializers.ValidationError("Deposit amount is too high")
        return value
    
    def validate_notes(self, value):
        """Validate notes"""
        if value and len(value) > 1000:
            raise serializers.ValidationError("Notes are too long (maximum 1000 characters)")
        return value


class TargetSavingSummarySerializer(serializers.Serializer):
    """Serializer for target saving summary"""
    
    total_targets = serializers.IntegerField()
    active_targets = serializers.IntegerField()
    completed_targets = serializers.IntegerField()
    overdue_targets = serializers.IntegerField()
    total_target_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_current_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_progress_percentage = serializers.FloatField()
    category_breakdown = serializers.ListField()


class TargetSavingAnalyticsSerializer(serializers.Serializer):
    """Serializer for target saving analytics"""
    
    total_deposits = serializers.IntegerField()
    average_deposit = serializers.DecimalField(max_digits=15, decimal_places=2)
    deposit_frequency = serializers.FloatField()
    progress_percentage = serializers.FloatField()
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    days_remaining = serializers.IntegerField()
    is_overdue = serializers.BooleanField()
    daily_target = serializers.DecimalField(max_digits=15, decimal_places=2)
    weekly_target = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_target = serializers.DecimalField(max_digits=15, decimal_places=2)