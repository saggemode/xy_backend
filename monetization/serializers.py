from rest_framework import serializers
from .models import (
    FeeStructure, FeeRule, DiscountCode, DiscountUsage,
    ReferralProgram, ReferralCode, Referral,
    SubscriptionPlan, PlanBenefit, UserSubscription, SubscriptionTransaction
)


class FeeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeRule
        fields = [
            'id', 'fee_structure', 'name', 'description', 'rule_type',
            'transaction_type', 'min_amount', 'max_amount', 'fixed_amount',
            'percentage', 'cap_amount', 'min_fee', 'priority', 'is_active',
            'created_at', 'updated_at'
        ]


class FeeStructureSerializer(serializers.ModelSerializer):
    rules = FeeRuleSerializer(many=True, read_only=True, source='feerule_set')
    
    class Meta:
        model = FeeStructure
        fields = [
            'id', 'name', 'description', 'is_active', 'created_at', 'updated_at', 'rules'
        ]


class DiscountUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountUsage
        fields = [
            'id', 'discount_code', 'user', 'transaction', 'amount_saved', 'created_at'
        ]


class DiscountCodeSerializer(serializers.ModelSerializer):
    usages = DiscountUsageSerializer(many=True, read_only=True, source='discountusage_set')
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = DiscountCode
        fields = [
            'id', 'code', 'name', 'description', 'discount_type', 'fixed_amount',
            'percentage', 'uses_count', 'max_uses', 'max_uses_per_user',
            'is_active', 'valid_until', 'created_at', 'updated_at', 'is_valid', 'usages'
        ]


class ReferralCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralCode
        fields = [
            'id', 'program', 'user', 'code', 'times_used', 'is_active', 'created_at'
        ]


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = [
            'id', 'program', 'referral_code', 'referrer', 'referee',
            'status', 'created_at', 'verified_at', 'rewarded_at',
            'rejected_at', 'rejection_reason'
        ]
        read_only_fields = [
            'verified_at', 'rewarded_at', 'rejected_at'
        ]


class ReferralProgramSerializer(serializers.ModelSerializer):
    referral_codes = ReferralCodeSerializer(many=True, read_only=True, source='referralcode_set')
    
    class Meta:
        model = ReferralProgram
        fields = [
            'id', 'name', 'description', 'referrer_reward', 'referee_reward',
            'is_active', 'valid_until', 'max_referrals_per_user',
            'ip_address_validation', 'device_validation',
            'created_at', 'updated_at', 'referral_codes'
        ]


class PlanBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanBenefit
        fields = [
            'id', 'plan', 'benefit_type', 'value', 'description', 'is_active'
        ]


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    benefits = PlanBenefitSerializer(many=True, read_only=True, source='planbenefit_set')
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'monthly_fee', 'annual_fee',
            'is_active', 'created_at', 'updated_at', 'benefits'
        ]


class SubscriptionTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionTransaction
        fields = [
            'id', 'subscription', 'transaction_type', 'amount',
            'payment_reference', 'created_at'
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    transactions = SubscriptionTransactionSerializer(many=True, read_only=True, source='subscriptiontransaction_set')
    plan_details = SubscriptionPlanSerializer(read_only=True, source='plan')
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'user', 'plan', 'plan_details', 'status', 'billing_cycle',
            'start_date', 'end_date', 'auto_renew',
            'created_at', 'updated_at', 'transactions'
        ]


# Specialized serializers for specific operations
class CalculateFeeSerializer(serializers.Serializer):
    transaction_type = serializers.CharField()
    amount = serializers.DecimalField(max_digits=19, decimal_places=4)
    currency = serializers.CharField()
    discount_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class ApplyDiscountSerializer(serializers.Serializer):
    discount_code = serializers.CharField()
    fee_amount = serializers.DecimalField(max_digits=19, decimal_places=4)
    currency = serializers.CharField()


class ProcessReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField()
    referee_id = serializers.IntegerField()
    referrer_ip = serializers.IPAddressField(required=False, allow_null=True)
    referee_ip = serializers.IPAddressField(required=False, allow_null=True)
    referrer_device_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    referee_device_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class SubscribeUserSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    billing_cycle = serializers.ChoiceField(choices=['monthly', 'annual'], default='monthly')
    payment_reference = serializers.CharField(required=False, allow_null=True, allow_blank=True)