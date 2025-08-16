import uuid
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from djmoney.money import Money
from djmoney.contrib.exchange.models import convert_money

from .models import (
    XySaveAccount, XySaveTransaction, XySaveGoal, 
    XySaveInvestment, XySaveSettings, Wallet
)
from .interest_services import InterestRateCalculator
from .ml_services import (
    XySaveFraudDetectionService,
    XySaveInvestmentRecommendationService,
    XySaveCustomerInsightsService,
    XySaveAnomalyDetectionService,
    XySaveInterestRateService
)

logger = logging.getLogger(__name__)


class XySaveAccountService:
    """Service for managing XySave accounts"""
    
    @staticmethod
    def create_xysave_account(user):
        """Create a new XySave account for user"""
        try:
            with transaction.atomic():
                # Generate unique account number
                account_number = f"XS{user.id:08d}{int(timezone.now().timestamp()) % 10000:04d}"
                
                # Create XySave account
                xysave_account = XySaveAccount.objects.create(
                    user=user,
                    account_number=account_number,
                    daily_interest_rate=Decimal('0.0004')  # 0.04% daily = ~15% annual
                )
                
                # Create default settings
                XySaveSettings.objects.create(user=user)
                
                logger.info(f"Created XySave account {account_number} for user {user.username}")
                return xysave_account
                
        except Exception as e:
            logger.error(f"Error creating XySave account for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def get_xysave_account(user):
        """Get or create XySave account for user"""
        try:
            return XySaveAccount.objects.get(user=user)
        except XySaveAccount.DoesNotExist:
            return XySaveAccountService.create_xysave_account(user)
    
    @staticmethod
    def get_account_summary(user):
        """Get comprehensive account summary"""
        try:
            account = XySaveAccountService.get_xysave_account(user)
            settings = XySaveSettings.objects.get(user=user)
            
            # Calculate today's interest
            daily_interest = account.calculate_daily_interest()
            
            # Get recent transactions
            recent_transactions = account.transactions.all()[:5]
            
            # Get active goals
            active_goals = user.xysave_goals.filter(is_active=True)
            
            # Get investments
            investments = account.investments.filter(is_active=True)
            
            return {
                'account': account,
                'settings': settings,
                'daily_interest': daily_interest,
                'annual_interest_rate': account.get_annual_interest_rate(),
                'recent_transactions': recent_transactions,
                'active_goals': active_goals,
                'investments': investments,
                'total_invested': sum(inv.amount_invested.amount for inv in investments),
                'total_investment_value': sum(inv.current_value.amount for inv in investments),
            }
            
        except Exception as e:
            logger.error(f"Error getting XySave summary for user {user.username}: {str(e)}")
            raise


class XySaveTransactionService:
    """Service for managing XySave transactions with ML-powered security"""
    
    def __init__(self):
        self.fraud_detector = XySaveFraudDetectionService()
        self.anomaly_detector = XySaveAnomalyDetectionService()
    
    def deposit_to_xysave(self, user, amount, description="Deposit to XySave"):
        """Deposit money to XySave account with ML-powered fraud and anomaly detection"""
        try:
            with transaction.atomic():
                # Get accounts
                wallet = Wallet.objects.get(user=user)
                xysave_account = XySaveAccountService.get_xysave_account(user)
                
                # Validate amount
                if amount.amount <= 0:
                    raise ValueError("Deposit amount must be positive")
                
                if wallet.balance.amount < amount.amount:
                    raise ValueError("Insufficient wallet balance")
                
                # Generate reference
                reference = f"XS_DEP_{uuid.uuid4().hex[:12].upper()}"
                
                # Record transaction first for ML analysis
                xysave_transaction = XySaveTransaction.objects.create(
                    xysave_account=xysave_account,
                    transaction_type='deposit',
                    amount=amount,
                    balance_before=xysave_account.balance,
                    balance_after=xysave_account.balance + amount,
                    reference=reference,
                    description=description
                )
                
                # ML-powered security checks
                fraud_risk = self.fraud_detector.predict_fraud_risk(xysave_transaction, user)
                anomaly_result = self.anomaly_detector.detect_anomaly(xysave_transaction, user)
                
                # Store ML analysis results
                xysave_transaction.metadata = {
                    'fraud_risk': fraud_risk,
                    'anomaly_detection': anomaly_result,
                    'ml_analysis_timestamp': timezone.now().isoformat()
                }
                
                # Check if transaction should be flagged
                if fraud_risk['is_suspicious'] or anomaly_result['is_anomalous']:
                    xysave_transaction.metadata['requires_review'] = True
                    xysave_transaction.metadata['security_flags'] = {
                        'fraud_suspicious': fraud_risk['is_suspicious'],
                        'anomaly_detected': anomaly_result['is_anomalous'],
                        'risk_level': max(fraud_risk['risk_level'], anomaly_result['risk_level'])
                    }
                    logger.warning(f"Transaction flagged for review: {xysave_transaction.reference}")
                
                xysave_transaction.save()
                
                # Update balances
                wallet.balance -= amount
                wallet.save()
                
                xysave_account.balance += amount
                xysave_account.save()
                
                logger.info(f"Deposited {amount} to XySave account {xysave_account.account_number}")
                return xysave_transaction
                
        except Exception as e:
            logger.error(f"Error depositing to XySave for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def withdraw_from_xysave(user, amount, description="Withdrawal from XySave"):
        """Withdraw money from XySave account"""
        try:
            with transaction.atomic():
                # Get accounts
                wallet = Wallet.objects.get(user=user)
                xysave_account = XySaveAccountService.get_xysave_account(user)
                
                # Validate withdrawal
                if amount.amount <= 0:
                    raise ValueError("Withdrawal amount must be positive")
                
                if not xysave_account.can_withdraw(amount):
                    raise ValueError("Insufficient XySave balance or account inactive")
                
                # Generate reference
                reference = f"XS_WTH_{uuid.uuid4().hex[:12].upper()}"
                
                # Record transaction
                xysave_transaction = XySaveTransaction.objects.create(
                    xysave_account=xysave_account,
                    transaction_type='withdrawal',
                    amount=amount,
                    balance_before=xysave_account.balance,
                    balance_after=xysave_account.balance - amount,
                    reference=reference,
                    description=description
                )
                
                # Update balances
                xysave_account.balance -= amount
                xysave_account.save()
                
                wallet.balance += amount
                wallet.save()
                
                logger.info(f"Withdrew {amount} from XySave account {xysave_account.account_number}")
                return xysave_transaction
                
        except Exception as e:
            logger.error(f"Error withdrawing from XySave for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def credit_interest(user, amount, description="Daily interest credit"):
        """Credit interest to XySave account"""
        try:
            with transaction.atomic():
                xysave_account = XySaveAccountService.get_xysave_account(user)
                
                # Generate reference
                reference = f"XS_INT_{uuid.uuid4().hex[:12].upper()}"
                
                # Record transaction
                xysave_transaction = XySaveTransaction.objects.create(
                    xysave_account=xysave_account,
                    transaction_type='interest_credit',
                    amount=amount,
                    balance_before=xysave_account.balance,
                    balance_after=xysave_account.balance + amount,
                    reference=reference,
                    description=description
                )
                
                # Update account
                xysave_account.balance += amount
                xysave_account.total_interest_earned += amount
                xysave_account.last_interest_calculation = timezone.now()
                xysave_account.save()
                
                logger.info(f"Credited interest {amount} to XySave account {xysave_account.account_number}")
                # Send notification (non-blocking)
                try:
                    from notification.models import Notification, NotificationType, NotificationLevel, NotificationStatus
                    Notification.objects.create(
                        recipient=user,
                        title="XySave Interest Credited",
                        message=(
                            f"Interest of ₦{amount.amount:,.2f} has been credited to your XySave account. "
                            f"Total interest earned: ₦{xysave_account.total_interest_earned.amount:,.2f}."
                        ),
                        notification_type=NotificationType.INTEREST_CREDITED,
                        level=NotificationLevel.SUCCESS,
                        status=NotificationStatus.PENDING,
                        source='xysave',
                        extra_data={
                            'interest_amount': float(amount.amount),
                            'total_interest': float(xysave_account.total_interest_earned.amount),
                            'account_number': xysave_account.account_number,
                        }
                    )
                except Exception as _:
                    pass
                return xysave_transaction
                
        except Exception as e:
            logger.error(f"Error crediting interest for user {user.username}: {str(e)}")
            raise


class XySaveAutoSaveService:
    """Service for managing auto-save functionality"""
    
    @staticmethod
    def enable_auto_save(user, percentage=10.0, min_amount=Money(100, 'NGN')):
        """Enable auto-save for user and sweep current wallet balance into XySave"""
        try:
            xysave_account = XySaveAccountService.get_xysave_account(user)
            
            xysave_account.auto_save_enabled = True
            xysave_account.auto_save_percentage = Decimal(str(percentage))
            xysave_account.auto_save_min_amount = min_amount
            xysave_account.save()
            
            # Immediately sweep current wallet balance into XySave
            wallet = Wallet.objects.get(user=user)
            if wallet.balance.amount > 0:
                XySaveTransactionService().deposit_to_xysave(
                    user,
                    Money(wallet.balance.amount, wallet.balance.currency),
                    description="Auto-save activation sweep"
                )
            
            logger.info(f"Enabled auto-save for user {user.username} at {percentage}% and swept wallet balance")
            return xysave_account
            
        except Exception as e:
            logger.error(f"Error enabling auto-save for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def disable_auto_save(user):
        """Disable auto-save for user"""
        try:
            xysave_account = XySaveAccountService.get_xysave_account(user)
            
            xysave_account.auto_save_enabled = False
            xysave_account.save()
            
            logger.info(f"Disabled auto-save for user {user.username}")
            return xysave_account
            
        except Exception as e:
            logger.error(f"Error disabling auto-save for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def process_auto_save(user, wallet_transaction_amount):
        """Process auto-save when wallet receives money"""
        try:
            xysave_account = XySaveAccountService.get_xysave_account(user)
            
            if not xysave_account.auto_save_enabled:
                return None
            
            # Calculate auto-save amount
            auto_save_amount = wallet_transaction_amount.amount * (xysave_account.auto_save_percentage / 100)
            
            # Check minimum amount
            if auto_save_amount < xysave_account.auto_save_min_amount.amount:
                return None
            
            auto_save_money = Money(auto_save_amount, wallet_transaction_amount.currency)
            
            # Process auto-save
            return XySaveTransactionService.deposit_to_xysave(
                user, 
                auto_save_money, 
                f"Auto-save ({xysave_account.auto_save_percentage}% of {wallet_transaction_amount})"
            )
            
        except Exception as e:
            logger.error(f"Error processing auto-save for user {user.username}: {str(e)}")
            return None


class XySaveGoalService:
    """Service for managing XySave goals"""
    
    @staticmethod
    def create_goal(user, name, target_amount, target_date=None):
        """Create a new savings goal"""
        try:
            goal = XySaveGoal.objects.create(
                user=user,
                name=name,
                target_amount=target_amount,
                target_date=target_date
            )
            
            logger.info(f"Created goal '{name}' for user {user.username}")
            return goal
            
        except Exception as e:
            logger.error(f"Error creating goal for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def update_goal_progress(user, goal_id, amount):
        """Update goal progress with amount"""
        try:
            with transaction.atomic():
                goal = XySaveGoal.objects.get(id=goal_id, user=user)
                
                goal.current_amount += amount
                goal.save()
                
                logger.info(f"Updated goal '{goal.name}' progress for user {user.username}")
                return goal
                
        except Exception as e:
            logger.error(f"Error updating goal progress for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def get_user_goals(user):
        """Get all goals for user"""
        try:
            return XySaveGoal.objects.filter(user=user).order_by('-created_at')
        except Exception as e:
            logger.error(f"Error getting goals for user {user.username}: {str(e)}")
            raise


class XySaveInvestmentService:
    """Service for managing XySave investments"""
    
    @staticmethod
    def create_investment(user, investment_type, amount_invested, expected_return_rate, maturity_date=None):
        """Create a new investment"""
        try:
            with transaction.atomic():
                xysave_account = XySaveAccountService.get_xysave_account(user)
                
                # Validate amount
                if amount_invested.amount > xysave_account.balance.amount:
                    raise ValueError("Insufficient XySave balance for investment")
                
                # Create investment
                investment = XySaveInvestment.objects.create(
                    xysave_account=xysave_account,
                    investment_type=investment_type,
                    amount_invested=amount_invested,
                    current_value=amount_invested,  # Initially same as invested
                    expected_return_rate=expected_return_rate,
                    maturity_date=maturity_date
                )
                
                # Deduct from XySave balance
                xysave_account.balance -= amount_invested
                xysave_account.save()
                
                # Record transaction
                XySaveTransaction.objects.create(
                    xysave_account=xysave_account,
                    transaction_type='transfer_out',
                    amount=amount_invested,
                    balance_before=xysave_account.balance + amount_invested,
                    balance_after=xysave_account.balance,
                    reference=f"XS_INV_{uuid.uuid4().hex[:12].upper()}",
                    description=f"Investment in {investment_type}"
                )
                
                logger.info(f"Created {investment_type} investment for user {user.username}")
                return investment
                
        except Exception as e:
            logger.error(f"Error creating investment for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def liquidate_investment(user, investment_id):
        """Liquidate an investment"""
        try:
            with transaction.atomic():
                investment = XySaveInvestment.objects.get(id=investment_id, xysave_account__user=user)
                
                if not investment.is_active:
                    raise ValueError("Investment is not active")
                
                # Calculate return
                return_amount = investment.current_value
                
                # Update investment
                investment.is_active = False
                investment.save()
                
                # Add to XySave balance
                xysave_account = investment.xysave_account
                xysave_account.balance += return_amount
                xysave_account.save()
                
                # Record transaction
                XySaveTransaction.objects.create(
                    xysave_account=xysave_account,
                    transaction_type='transfer_in',
                    amount=return_amount,
                    balance_before=xysave_account.balance - return_amount,
                    balance_after=xysave_account.balance,
                    reference=f"XS_LIQ_{uuid.uuid4().hex[:12].upper()}",
                    description=f"Liquidated {investment.investment_type} investment"
                )
                
                logger.info(f"Liquidated {investment.investment_type} investment for user {user.username}")
                return investment
                
        except Exception as e:
            logger.error(f"Error liquidating investment for user {user.username}: {str(e)}")
            raise


class XySaveInterestService:
    """Service for managing XySave interest calculations and payouts"""
    
    @staticmethod
    def calculate_daily_interest_for_all_accounts():
        """Calculate and credit daily interest for all active accounts"""
        try:
            active_accounts = XySaveAccount.objects.filter(is_active=True, balance__gt=0)
            
            for account in active_accounts:
                try:
                    daily_interest = account.calculate_daily_interest()
                    
                    if daily_interest.amount > 0:
                        XySaveTransactionService.credit_interest(
                            account.user,
                            daily_interest,
                            f"Daily interest credit ({account.get_annual_interest_rate():.2f}% p.a.)"
                        )
                        
                except Exception as e:
                    logger.error(f"Error calculating interest for account {account.account_number}: {str(e)}")
                    continue
            
            logger.info(f"Processed daily interest for {active_accounts.count()} accounts")
            
        except Exception as e:
            logger.error(f"Error in daily interest calculation: {str(e)}")
            raise
    
    @staticmethod
    def get_interest_forecast(user, days=30):
        """Get interest forecast for user"""
        try:
            account = XySaveAccountService.get_xysave_account(user)
            
            daily_interest = account.calculate_daily_interest()
            weekly_interest = daily_interest.amount * 7
            monthly_interest = daily_interest.amount * 30
            yearly_interest = daily_interest.amount * 365
            
            return {
                'daily_interest': daily_interest,
                'weekly_interest': Money(weekly_interest, daily_interest.currency),
                'monthly_interest': Money(monthly_interest, daily_interest.currency),
                'yearly_interest': Money(yearly_interest, daily_interest.currency),
                'annual_rate': account.get_annual_interest_rate(),
                'current_balance': account.balance,
                'total_interest_earned': account.total_interest_earned,
            }
            
        except Exception as e:
            logger.error(f"Error getting interest forecast for user {user.username}: {str(e)}")
            raise 