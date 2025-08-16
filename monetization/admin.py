from django.contrib import admin
from .models import (
    FeeStructure, FeeRule, DiscountCode, DiscountUsage,
    ReferralProgram, ReferralCode, Referral,
    SubscriptionPlan, PlanBenefit, UserSubscription, SubscriptionTransaction
)


class FeeRuleInline(admin.TabularInline):
    model = FeeRule
    extra = 1


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    inlines = [FeeRuleInline]


@admin.register(FeeRule)
class FeeRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'fee_structure', 'rule_type', 'transaction_type', 
                   'min_amount', 'max_amount', 'fixed_amount', 'percentage', 
                   'priority', 'is_active')
    list_filter = ('rule_type', 'transaction_type', 'is_active', 'fee_structure')
    search_fields = ('name', 'description')


class DiscountUsageInline(admin.TabularInline):
    model = DiscountUsage
    extra = 0
    readonly_fields = ('user', 'transaction', 'amount_saved', 'created_at')
    can_delete = False


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'discount_type', 'fixed_amount', 'percentage',
                   'uses_count', 'max_uses', 'is_active', 'valid_until')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code', 'name', 'description')
    readonly_fields = ('uses_count', 'created_at', 'updated_at')
    inlines = [DiscountUsageInline]


@admin.register(DiscountUsage)
class DiscountUsageAdmin(admin.ModelAdmin):
    list_display = ('discount_code', 'user', 'amount_saved', 'created_at')
    list_filter = ('discount_code', 'created_at')
    search_fields = ('discount_code__code', 'user__username', 'user__email')
    readonly_fields = ('discount_code', 'user', 'transaction', 'amount_saved', 'created_at')


class ReferralCodeInline(admin.TabularInline):
    model = ReferralCode
    extra = 0


@admin.register(ReferralProgram)
class ReferralProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'referrer_reward', 'referee_reward', 'is_active',
                   'valid_until', 'max_referrals_per_user')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    inlines = [ReferralCodeInline]


class ReferralInline(admin.TabularInline):
    model = Referral
    extra = 0
    readonly_fields = ('referrer', 'referee', 'status', 'created_at')
    can_delete = False


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'program', 'times_used', 'is_active', 'created_at')
    list_filter = ('program', 'is_active')
    search_fields = ('code', 'user__username', 'user__email')
    readonly_fields = ('times_used', 'created_at')
    inlines = [ReferralInline]


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referee', 'program', 'status', 'created_at',
                   'verified_at', 'rewarded_at')
    list_filter = ('status', 'program', 'created_at')
    search_fields = ('referrer__username', 'referrer__email', 'referee__username', 'referee__email')
    readonly_fields = ('referrer', 'referee', 'program', 'referral_code', 'created_at',
                      'verified_at', 'rewarded_at', 'rejected_at')
    fieldsets = (
        (None, {
            'fields': ('referrer', 'referee', 'program', 'referral_code', 'status')
        }),
        ('Fraud Prevention', {
            'fields': ('referrer_ip', 'referee_ip', 'referrer_device_id', 'referee_device_id')
        }),
        ('Status Tracking', {
            'fields': ('created_at', 'verified_at', 'rewarded_at', 'rejected_at', 'rejection_reason')
        }),
    )


class PlanBenefitInline(admin.TabularInline):
    model = PlanBenefit
    extra = 1


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'monthly_fee', 'annual_fee', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    inlines = [PlanBenefitInline]


@admin.register(PlanBenefit)
class PlanBenefitAdmin(admin.ModelAdmin):
    list_display = ('plan', 'benefit_type', 'value', 'is_active')
    list_filter = ('benefit_type', 'is_active', 'plan')
    search_fields = ('description',)


class SubscriptionTransactionInline(admin.TabularInline):
    model = SubscriptionTransaction
    extra = 0
    readonly_fields = ('transaction_type', 'amount', 'payment_reference', 'created_at')
    can_delete = False


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'billing_cycle', 'start_date', 'end_date', 'auto_renew')
    list_filter = ('status', 'plan', 'billing_cycle', 'auto_renew')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [SubscriptionTransactionInline]


@admin.register(SubscriptionTransaction)
class SubscriptionTransactionAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'transaction_type', 'amount', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('subscription__user__username', 'subscription__user__email', 'payment_reference')
    readonly_fields = ('subscription', 'transaction_type', 'amount', 'payment_reference', 'created_at')