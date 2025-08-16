from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    WalletViewSet, TransactionViewSet, BankTransferViewSet, BillPaymentViewSet, BankViewSet,
    StaffRoleViewSet, StaffProfileViewSet, TransactionApprovalViewSet, 
    CustomerEscalationViewSet, StaffActivityViewSet
)
from . import interest_views, xysave_views
from . import spend_and_save_views
from . import target_saving_views
from . import fixed_savings_views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'bank-transfers', BankTransferViewSet, basename='bank-transfer')
router.register(r'bill-payments', BillPaymentViewSet, basename='bill-payment')
router.register(r'banks', BankViewSet, basename='bank')

# Staff Management URLs
router.register(r'staff/roles', StaffRoleViewSet, basename='staff-role')
router.register(r'staff/profiles', StaffProfileViewSet, basename='staff-profile')
router.register(r'staff/activities', StaffActivityViewSet, basename='staff-activity')

# Transaction Approval URLs
router.register(r'approvals', TransactionApprovalViewSet, basename='transaction-approval')

# Customer Escalation URLs
router.register(r'escalations', CustomerEscalationViewSet, basename='customer-escalation')

# XySave routers
xysave_router = DefaultRouter()
xysave_router.register(r'accounts', xysave_views.XySaveAccountViewSet, basename='xysave-account')
xysave_router.register(r'transactions', xysave_views.XySaveTransactionViewSet, basename='xysave-transaction')
xysave_router.register(r'goals', xysave_views.XySaveGoalViewSet, basename='xysave-goal')
xysave_router.register(r'investments', xysave_views.XySaveInvestmentViewSet, basename='xysave-investment')
xysave_router.register(r'settings', xysave_views.XySaveSettingsViewSet, basename='xysave-settings')
xysave_router.register(r'auto-save', xysave_views.XySaveAutoSaveViewSet, basename='xysave-auto-save')

# Spend and Save routers
spend_and_save_router = DefaultRouter()
spend_and_save_router.register(r'accounts', spend_and_save_views.SpendAndSaveAccountViewSet, basename='spend-and-save-account')
spend_and_save_router.register(r'transactions', spend_and_save_views.SpendAndSaveTransactionViewSet, basename='spend-and-save-transaction')
spend_and_save_router.register(r'settings', spend_and_save_views.SpendAndSaveSettingsViewSet, basename='spend-and-save-settings')
spend_and_save_router.register(r'interest', spend_and_save_views.SpendAndSaveInterestViewSet, basename='spend-and-save-interest')
spend_and_save_router.register(r'statistics', spend_and_save_views.SpendAndSaveStatisticsViewSet, basename='spend-and-save-statistics')

# Target Saving routers
target_saving_router = DefaultRouter()
target_saving_router.register(r'targets', target_saving_views.TargetSavingViewSet, basename='target-saving')
target_saving_router.register(r'deposits', target_saving_views.TargetSavingDepositViewSet, basename='target-saving-deposit')

# Fixed Savings routers
fixed_savings_router = DefaultRouter()
fixed_savings_router.register(r'accounts', fixed_savings_views.FixedSavingsAccountViewSet, basename='fixed-savings-account')
fixed_savings_router.register(r'transactions', fixed_savings_views.FixedSavingsTransactionViewSet, basename='fixed-savings-transaction')
fixed_savings_router.register(r'settings', fixed_savings_views.FixedSavingsSettingsViewSet, basename='fixed-savings-settings')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Additional utility endpoints
    path('user-status/', views.get_user_status, name='user-status'),
    
    # Interest Rate Calculator endpoints
    path('interest/calculate/', interest_views.calculate_interest, name='calculate-interest'),
    path('interest/rates/', interest_views.get_interest_rates, name='get-interest-rates'),
    path('interest/wallet/', interest_views.calculate_wallet_interest, name='calculate-wallet-interest'),
    path('interest/apply/', interest_views.apply_interest_to_wallet, name='apply-interest-to-wallet'),
    path('interest/report/', interest_views.get_interest_report, name='get-interest-report'),
    path('interest/process-monthly/', interest_views.process_monthly_interest, name='process-monthly-interest'),
    path('interest/demo/', interest_views.interest_calculator_demo, name='interest-calculator-demo'),
    
    # XySave endpoints
    path('xysave/', include(xysave_router.urls)),
    
    # Spend and Save endpoints
    path('spend-and-save/', include(spend_and_save_router.urls)),
    
    # Target Saving endpoints
    path('target-saving/', include(target_saving_router.urls)),
    
    # Fixed Savings endpoints
    path('fixed-savings/', include(fixed_savings_router.urls)),
]

urlpatterns += [
    path('statement/pdf/', views.download_pdf_statement, name='download_pdf_statement'),
]
