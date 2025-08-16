from django.urls import path
from .views import (
    profile, request_verification, verify,
    admin_dashboard, compliance_report, user_analytics, system_monitoring,
    api_dashboard_data, api_user_export, KYCProfileViewSet, validate_bvn, validate_nin, resume_registration, register, verify_otp, kyc_input,
    tier_upgrade_requirements, request_tier_upgrade, check_upgrade_eligibility, verify_email_link, TransactionPinViewSet
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'kyc-profiles', KYCProfileViewSet, basename='kyc-profile')
router.register(r'transaction-pin', TransactionPinViewSet, basename='transaction-pin')

urlpatterns = [
    # API endpoints
    path('profile/', profile, name='user-profile'),
    path('request-verification/', request_verification, name='request-verification'),
    path('verify/', verify, name='verify'),
    
    # Tier upgrade endpoints
    path('tier-upgrade/requirements/', tier_upgrade_requirements, name='tier-upgrade-requirements'),
    path('tier-upgrade/request/', request_tier_upgrade, name='request-tier-upgrade'),
    path('tier-upgrade/eligibility/', check_upgrade_eligibility, name='check-upgrade-eligibility'),
    
    # Custom admin views
    path('admin/dashboard/', admin_dashboard, name='admin-dashboard'),
    path('admin/compliance-report/', compliance_report, name='compliance-report'),
    path('admin/user-analytics/', user_analytics, name='user-analytics'),
    path('admin/system-monitoring/', system_monitoring, name='system-monitoring'),
    
    # Admin API endpoints
    path('admin/api/dashboard-data/', api_dashboard_data, name='api-dashboard-data'),
    path('admin/api/user-export/', api_user_export, name='api-user-export'),
    *router.urls,
]

urlpatterns += [
    path('kyc/validate-bvn/', validate_bvn, name='validate-bvn'),
    path('kyc/validate-nin/', validate_nin, name='validate-nin'),
    path('accounts/resume-registration/', resume_registration, name='resume-registration'),
    path('accounts/register/', register, name='register'),
    path('accounts/verify-otp/', verify_otp, name='verify-otp'),
    path('accounts/kyc-input/', kyc_input, name='kyc-input'),
    path('accounts/verify-email/', verify_email_link, name='verify-email-link'),
] 