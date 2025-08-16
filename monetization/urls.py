from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FeeStructureViewSet, FeeRuleViewSet, 
    DiscountCodeViewSet, DiscountUsageViewSet,
    ReferralProgramViewSet, ReferralCodeViewSet, ReferralViewSet,
    SubscriptionPlanViewSet, PlanBenefitViewSet, 
    UserSubscriptionViewSet, SubscriptionTransactionViewSet,
    FeeCalculationViewSet
)

router = DefaultRouter()
router.register(r'fee-structures', FeeStructureViewSet)
router.register(r'fee-rules', FeeRuleViewSet)
router.register(r'discount-codes', DiscountCodeViewSet)
router.register(r'discount-usages', DiscountUsageViewSet)
router.register(r'referral-programs', ReferralProgramViewSet)
router.register(r'referral-codes', ReferralCodeViewSet)
router.register(r'referrals', ReferralViewSet)
router.register(r'subscription-plans', SubscriptionPlanViewSet)
router.register(r'plan-benefits', PlanBenefitViewSet)
router.register(r'user-subscriptions', UserSubscriptionViewSet)
router.register(r'subscription-transactions', SubscriptionTransactionViewSet)
router.register(r'fee-calculation', FeeCalculationViewSet, basename='fee-calculation')

urlpatterns = [
    path('', include(router.urls)),
]