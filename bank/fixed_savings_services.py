import logging
import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from djmoney.money import Money
from .models import (
    FixedSavingsAccount, FixedSavingsTransaction, FixedSavingsSettings,
    FixedSavingsSource, FixedSavingsPurpose, Wallet, XySaveAccount
)
from notification.models import Notification, NotificationType, NotificationLevel

logger = logging.getLogger(__name__)

class FixedSavingsService:
    """
    Service class for Fixed Savings business logic
    """
    
    @staticmethod
    def create_fixed_savings(user, amount, source, purpose, purpose_description, 
                           start_date, payback_date, auto_renewal_enabled=False):
        """
        Create a new fixed savings account
        """
        try:
            with transaction.atomic():
                # Validate user has sufficient funds
                if not FixedSavingsService._validate_sufficient_funds(user, amount, source):
                    raise ValidationError("Insufficient funds for fixed savings")
                
                # Create fixed savings account
                fixed_savings = FixedSavingsAccount.objects.create(
                    user=user,
                    amount=amount,
                    source=source,
                    purpose=purpose,
                    purpose_description=purpose_description,
                    start_date=start_date,
                    payback_date=payback_date,
                    auto_renewal_enabled=auto_renewal_enabled
                )
                
                # Deduct funds from source accounts
                FixedSavingsService._deduct_funds(user, amount, source)
                
                # Create initial transaction
                FixedSavingsTransaction.objects.create(
                    fixed_savings_account=fixed_savings,
                    transaction_type='initial_deposit',
                    amount=amount,
                    balance_before=amount,  # This is the initial deposit
                    balance_after=amount,
                    reference=f"FS_INIT_{fixed_savings.id}",
                    description=f"Initial fixed savings deposit - {purpose_description or fixed_savings.get_purpose_display()}",
                    source_account=source,
                    interest_rate_applied=fixed_savings.interest_rate
                )
                
                # Send notifications
                FixedSavingsNotificationService.send_fixed_savings_created_notification(fixed_savings)
                
                return fixed_savings
                
        except Exception as e:
            logger.error(f"Error creating fixed savings for user {user.id}: {str(e)}")
            raise
    
    @staticmethod
    def _validate_sufficient_funds(user, amount, source):
        """Validate user has sufficient funds for fixed savings"""
        try:
            wallet = user.wallet
            
            if source == FixedSavingsSource.WALLET:
                return wallet.balance >= amount
            elif source == FixedSavingsSource.XYSAVE:
                try:
                    xysave_account = user.xysave_account
                    return xysave_account.balance >= amount
                except XySaveAccount.DoesNotExist:
                    logger.warning(f"User {user.id} has no XySave account for XySave-only fixed savings")
                    return False
            elif source == FixedSavingsSource.BOTH:
                try:
                    xysave_account = user.xysave_account
                    # Flexible validation: combined balances must cover the full amount
                    combined = wallet.balance.amount + xysave_account.balance.amount
                    return combined >= amount.amount
                except XySaveAccount.DoesNotExist:
                    logger.warning(f"User {user.id} has no XySave account for BOTH source fixed savings")
                    # If no XySave account, check if wallet has enough for the full amount
                    return wallet.balance >= amount
            return False
        except Exception as e:
            logger.error(f"Error validating funds for user {user.id}: {str(e)}")
            return False
    
    @staticmethod
    def _deduct_funds(user, amount, source):
        """Deduct funds from source accounts"""
        try:
            wallet = user.wallet
            
            if source == FixedSavingsSource.WALLET:
                wallet.balance -= amount
                wallet.save()
            elif source == FixedSavingsSource.XYSAVE:
                try:
                    xysave_account = user.xysave_account
                    xysave_account.balance -= amount
                    xysave_account.save()
                except XySaveAccount.DoesNotExist:
                    raise ValidationError("XySave account not found")
            elif source == FixedSavingsSource.BOTH:
                try:
                    xysave_account = user.xysave_account
                    # Flexible deduction: draw from wallet first, then XySave to cover the rest
                    remaining = amount.amount
                    if wallet.balance.amount > 0:
                        wallet_deduction = min(wallet.balance.amount, remaining)
                        if wallet_deduction > 0:
                            wallet_deduction_money = Money(amount=wallet_deduction, currency=amount.currency)
                            wallet.balance -= wallet_deduction_money
                            remaining -= wallet_deduction
                    if remaining > 0:
                        xysave_deduction_money = Money(amount=remaining, currency=amount.currency)
                        xysave_account.balance -= xysave_deduction_money
                        remaining = 0
                    wallet.save()
                    xysave_account.save()
                except XySaveAccount.DoesNotExist:
                    # If no XySave account, deduct full amount from wallet
                    logger.warning(f"User {user.id} has no XySave account, deducting full amount from wallet")
                    wallet.balance -= amount
                    wallet.save()
        except Exception as e:
            logger.error(f"Error deducting funds for user {user.id}: {str(e)}")
            raise
    
    @staticmethod
    def process_maturity_payout(fixed_savings):
        """
        Process maturity payout for fixed savings
        """
        try:
            with transaction.atomic():
                if not fixed_savings.can_be_paid_out:
                    raise ValidationError("Fixed savings cannot be paid out")
                
                # Mark as matured if not already
                if not fixed_savings.is_matured:
                    fixed_savings.mark_as_matured()
                
                # Pay out to xysave account
                success = fixed_savings.pay_out()
                if success:
                    # Send notifications
                    FixedSavingsNotificationService.send_fixed_savings_matured_notification(fixed_savings)
                    FixedSavingsNotificationService.send_fixed_savings_paid_out_notification(fixed_savings)
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error processing maturity payout for fixed savings {fixed_savings.id}: {str(e)}")
            raise
    
    @staticmethod
    def process_auto_renewal(fixed_savings):
        """
        Process auto-renewal for fixed savings
        """
        try:
            with transaction.atomic():
                if not fixed_savings.auto_renewal_enabled or not fixed_savings.is_mature:
                    return False
                
                # Calculate new dates
                duration_days = fixed_savings.duration_days
                new_start_date = fixed_savings.payback_date
                new_payback_date = new_start_date + timezone.timedelta(days=duration_days)
                
                # Create new fixed savings account
                new_fixed_savings = FixedSavingsAccount.objects.create(
                    user=fixed_savings.user,
                    amount=fixed_savings.maturity_amount,
                    source=FixedSavingsSource.XYSAVE,  # From xysave since that's where payout goes
                    purpose=fixed_savings.purpose,
                    purpose_description=f"Auto-renewal of {fixed_savings.purpose_description or fixed_savings.get_purpose_display()}",
                    start_date=new_start_date,
                    payback_date=new_payback_date,
                    auto_renewal_enabled=fixed_savings.auto_renewal_enabled
                )
                
                # Create auto-renewal transaction
                FixedSavingsTransaction.objects.create(
                    fixed_savings_account=new_fixed_savings,
                    transaction_type='auto_renewal',
                    amount=new_fixed_savings.amount,
                    balance_before=new_fixed_savings.amount,
                    balance_after=new_fixed_savings.amount,
                    reference=f"FS_RENEWAL_{new_fixed_savings.id}",
                    description=f"Auto-renewal of fixed savings - {new_fixed_savings.purpose_description}",
                    interest_rate_applied=new_fixed_savings.interest_rate
                )
                
                # Send notification
                FixedSavingsNotificationService.send_fixed_savings_auto_renewal_notification(new_fixed_savings)
                
                return new_fixed_savings
                
        except Exception as e:
            logger.error(f"Error processing auto-renewal for fixed savings {fixed_savings.id}: {str(e)}")
            raise
    
    @staticmethod
    def get_user_fixed_savings_summary(user):
        """
        Get summary of user's fixed savings
        """
        try:
            active_fixed_savings = FixedSavingsAccount.objects.filter(
                user=user, is_active=True
            )
            
            total_active_amount = sum(fs.amount.amount for fs in active_fixed_savings)
            total_maturity_amount = sum(fs.maturity_amount.amount for fs in active_fixed_savings)
            total_interest_earned = sum(fs.total_interest_earned.amount for fs in active_fixed_savings)
            
            matured_fixed_savings = FixedSavingsAccount.objects.filter(
                user=user, is_matured=True, is_paid_out=False
            )
            
            return {
                'total_active_fixed_savings': active_fixed_savings.count(),
                'total_active_amount': Money(amount=total_active_amount, currency='NGN'),
                'total_maturity_amount': Money(amount=total_maturity_amount, currency='NGN'),
                'total_interest_earned': Money(amount=total_interest_earned, currency='NGN'),
                'matured_unpaid_count': matured_fixed_savings.count(),
                'matured_unpaid_amount': sum(fs.maturity_amount.amount for fs in matured_fixed_savings)
            }
        except Exception as e:
            logger.error(f"Error getting fixed savings summary for user {user.id}: {str(e)}")
            return {}

class FixedSavingsNotificationService:
    """
    Service class for Fixed Savings notifications
    """
    
    @staticmethod
    def send_fixed_savings_created_notification(fixed_savings):
        """Send notification when fixed savings is created"""
        try:
            Notification.objects.create(
                recipient=fixed_savings.user,
                title="Fixed Savings Created",
                message=(
                    f"Your fixed savings of ₦{fixed_savings.amount.amount:,.2f} has been created successfully. "
                    f"Maturity date: {fixed_savings.payback_date.strftime('%B %d, %Y')}. "
                    f"Interest rate: {fixed_savings.interest_rate}% p.a."
                ),
                notification_type=NotificationType.FIXED_SAVINGS_CREATED,
                level=NotificationLevel.SUCCESS,
                source='fixed_savings',
                extra_data={
                    'fixed_savings_id': str(fixed_savings.id),
                    'amount': str(fixed_savings.amount),
                    'interest_rate': str(fixed_savings.interest_rate),
                    'maturity_date': fixed_savings.payback_date.isoformat(),
                    'purpose': fixed_savings.purpose,
                    'source': fixed_savings.source
                }
            )
        except Exception as e:
            logger.error(f"Error sending fixed savings created notification: {str(e)}")
    
    @staticmethod
    def send_fixed_savings_matured_notification(fixed_savings):
        """Send notification when fixed savings matures"""
        try:
            Notification.objects.create(
                recipient=fixed_savings.user,
                title="Fixed Savings Matured",
                message=(
                    f"Your fixed savings of ₦{fixed_savings.amount.amount:,.2f} has matured! "
                    f"Total maturity amount: ₦{fixed_savings.maturity_amount.amount:,.2f}. "
                    f"Interest earned: ₦{fixed_savings.total_interest_earned.amount:,.2f}."
                ),
                notification_type=NotificationType.FIXED_SAVINGS_MATURED,
                level=NotificationLevel.SUCCESS,
                source='fixed_savings',
                extra_data={
                    'fixed_savings_id': str(fixed_savings.id),
                    'original_amount': str(fixed_savings.amount),
                    'maturity_amount': str(fixed_savings.maturity_amount),
                    'interest_earned': str(fixed_savings.total_interest_earned),
                    'interest_rate': str(fixed_savings.interest_rate)
                }
            )
        except Exception as e:
            logger.error(f"Error sending fixed savings matured notification: {str(e)}")
    
    @staticmethod
    def send_fixed_savings_paid_out_notification(fixed_savings):
        """Send notification when fixed savings is paid out"""
        try:
            Notification.objects.create(
                recipient=fixed_savings.user,
                title="Fixed Savings Paid Out",
                message=(
                    f"Your matured fixed savings of ₦{fixed_savings.maturity_amount.amount:,.2f} "
                    f"has been credited to your XySave account successfully."
                ),
                notification_type=NotificationType.FIXED_SAVINGS_PAID_OUT,
                level=NotificationLevel.SUCCESS,
                source='fixed_savings',
                extra_data={
                    'fixed_savings_id': str(fixed_savings.id),
                    'maturity_amount': str(fixed_savings.maturity_amount),
                    'interest_earned': str(fixed_savings.total_interest_earned),
                    'destination': 'xysave_account'
                }
            )
        except Exception as e:
            logger.error(f"Error sending fixed savings paid out notification: {str(e)}")
    
    @staticmethod
    def send_fixed_savings_auto_renewal_notification(fixed_savings):
        """Send notification when fixed savings auto-renews"""
        try:
            Notification.objects.create(
                recipient=fixed_savings.user,
                title="Fixed Savings Auto-Renewed",
                message=(
                    f"Your fixed savings has been auto-renewed for ₦{fixed_savings.amount.amount:,.2f}. "
                    f"New maturity date: {fixed_savings.payback_date.strftime('%B %d, %Y')}. "
                    f"Interest rate: {fixed_savings.interest_rate}% p.a."
                ),
                notification_type=NotificationType.FIXED_SAVINGS_AUTO_RENEWAL,
                level=NotificationLevel.INFO,
                source='fixed_savings',
                extra_data={
                    'fixed_savings_id': str(fixed_savings.id),
                    'amount': str(fixed_savings.amount),
                    'interest_rate': str(fixed_savings.interest_rate),
                    'maturity_date': fixed_savings.payback_date.isoformat(),
                    'auto_renewal': True
                }
            )
        except Exception as e:
            logger.error(f"Error sending fixed savings auto-renewal notification: {str(e)}")
    
    @staticmethod
    def send_fixed_savings_maturity_reminder_notification(fixed_savings):
        """Send reminder notification before maturity"""
        try:
            days_remaining = fixed_savings.days_remaining
            if days_remaining <= 7:  # Send reminder 7 days before maturity
                Notification.objects.create(
                    recipient=fixed_savings.user,
                    title="Fixed Savings Maturity Reminder",
                    message=(
                        f"Your fixed savings of ₦{fixed_savings.amount.amount:,.2f} will mature in {days_remaining} days. "
                        f"Maturity amount: ₦{fixed_savings.maturity_amount.amount:,.2f}."
                    ),
                    notification_type=NotificationType.FIXED_SAVINGS_MATURITY_REMINDER,
                    level=NotificationLevel.WARNING,
                    source='fixed_savings',
                    extra_data={
                        'fixed_savings_id': str(fixed_savings.id),
                        'days_remaining': days_remaining,
                        'maturity_amount': str(fixed_savings.maturity_amount),
                        'maturity_date': fixed_savings.payback_date.isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"Error sending fixed savings maturity reminder notification: {str(e)}")
    
    @staticmethod
    def send_fixed_savings_interest_credited_notification(fixed_savings, interest_amount):
        """Send notification when interest is credited"""
        try:
            Notification.objects.create(
                recipient=fixed_savings.user,
                title="Fixed Savings Interest Credited",
                message=(
                    f"Interest of ₦{interest_amount.amount:,.2f} has been credited to your fixed savings. "
                    f"Current total: ₦{fixed_savings.maturity_amount.amount:,.2f}."
                ),
                notification_type=NotificationType.FIXED_SAVINGS_INTEREST_CREDITED,
                level=NotificationLevel.SUCCESS,
                source='fixed_savings',
                extra_data={
                    'fixed_savings_id': str(fixed_savings.id),
                    'interest_amount': str(interest_amount),
                    'total_amount': str(fixed_savings.maturity_amount),
                    'interest_rate': str(fixed_savings.interest_rate)
                }
            )
        except Exception as e:
            logger.error(f"Error sending fixed savings interest credited notification: {str(e)}")
    
    @staticmethod
    def send_fixed_savings_early_withdrawal_notification(fixed_savings, withdrawal_amount, penalty_amount):
        """Send notification for early withdrawal"""
        try:
            Notification.objects.create(
                recipient=fixed_savings.user,
                title="Fixed Savings Early Withdrawal",
                message=(
                    f"Early withdrawal processed: ₦{withdrawal_amount.amount:,.2f}. "
                    f"Penalty applied: ₦{penalty_amount.amount:,.2f}. "
                    f"Early withdrawal may affect your interest earnings."
                ),
                notification_type=NotificationType.FIXED_SAVINGS_EARLY_WITHDRAWAL,
                level=NotificationLevel.WARNING,
                source='fixed_savings',
                extra_data={
                    'fixed_savings_id': str(fixed_savings.id),
                    'withdrawal_amount': str(withdrawal_amount),
                    'penalty_amount': str(penalty_amount),
                    'original_amount': str(fixed_savings.amount)
                }
            )
        except Exception as e:
            logger.error(f"Error sending fixed savings early withdrawal notification: {str(e)}") 