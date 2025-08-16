import uuid
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from djmoney.money import Money
from .models import (
    SpendAndSaveAccount, SpendAndSaveTransaction, SpendAndSaveSettings,
    Wallet, XySaveAccount, Transaction, calculate_tiered_interest_rate,
    GeneralStatusChoices
)
from .spend_and_save_notifications import SpendAndSaveNotificationService

logger = logging.getLogger(__name__)


class SpendAndSaveService:
    """
    Service for managing Spend and Save functionality
    """
    
    @staticmethod
    def create_account(user):
        """Create a new Spend and Save account for a user"""
        try:
            with transaction.atomic():
                # Generate unique account number
                account_number = SpendAndSaveService._generate_account_number()
                
                # Create the account
                account = SpendAndSaveAccount.objects.create(
                    user=user,
                    account_number=account_number,
                    balance=Money(0, 'NGN'),
                    total_interest_earned=Money(0, 'NGN'),
                    total_saved_from_spending=Money(0, 'NGN')
                )
                
                # Create default settings
                SpendAndSaveSettings.objects.create(
                    user=user,
                    preferred_savings_percentage=Decimal('5.00'),
                    min_transaction_threshold=Money(100, 'NGN'),
                    default_withdrawal_destination='wallet'
                )
                
                logger.info(f"Created Spend and Save account for user {user.username}")
                return account
                
        except Exception as e:
            logger.error(f"Error creating Spend and Save account for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def _generate_account_number():
        """Generate a unique account number for Spend and Save"""
        import random
        import string
        
        while True:
            # Generate a 10-digit number starting with '8' to distinguish from regular accounts
            number = '8' + ''.join(random.choices(string.digits, k=9))
            if not SpendAndSaveAccount.objects.filter(account_number=number).exists():
                return number
    
    @staticmethod
    def _transfer_initial_funds(user, account, fund_source, amount, wallet_amount=None, xysave_amount=None):
        """Transfer initial funds from the specified source to Spend and Save account"""
        try:
            if fund_source == 'wallet':
                # Transfer from wallet
                wallet = Wallet.objects.get(user=user)
                if wallet.balance.amount < amount.amount:
                    raise ValidationError(f"Insufficient wallet balance. Available: {wallet.balance}, Required: {amount}")
                
                # Deduct from wallet
                wallet.balance -= amount
                wallet.save()
                
                # Create wallet transaction
                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    type='debit',
                    status='success',
                    description=f'Initial transfer to Spend and Save account {account.account_number}',
                    balance_after=wallet.balance
                )
                
            elif fund_source == 'xysave':
                # Transfer from XySave account
                xysave_account = XySaveAccount.objects.get(user=user)
                if xysave_account.balance.amount < amount.amount:
                    raise ValidationError(f"Insufficient XySave balance. Available: {xysave_account.balance}, Required: {amount}")
                
                # Deduct from XySave account
                xysave_account.balance -= amount
                xysave_account.save()
                
                # Create XySave transaction (if XySaveTransaction model exists)
                try:
                    from .models import XySaveTransaction
                    XySaveTransaction.objects.create(
                        xysave_account=xysave_account,
                        amount=amount,
                        transaction_type='withdrawal',
                        balance_before=xysave_account.balance + amount,
                        balance_after=xysave_account.balance,
                        reference=f"XYS-{uuid.uuid4().hex[:8].upper()}",
                        description=f'Initial transfer to Spend and Save account {account.account_number}'
                    )
                except ImportError:
                    # XySaveTransaction model might not exist, skip
                    pass
            
            elif fund_source == 'both':
                total_transferred = Money(0, 'NGN')
                
                # Transfer from wallet if amount specified
                if wallet_amount and wallet_amount > 0:
                    wallet = Wallet.objects.get(user=user)
                    wallet_money = Money(wallet_amount, 'NGN')
                    
                    if wallet.balance.amount < wallet_money.amount:
                        raise ValidationError(f"Insufficient wallet balance. Available: {wallet.balance}, Required: {wallet_money}")
                    
                    # Deduct from wallet
                    wallet.balance -= wallet_money
                    wallet.save()
                    
                    # Create wallet transaction
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=wallet_money,
                        type='debit',
                        status='success',
                        description=f'Initial transfer to Spend and Save account {account.account_number}',
                        balance_after=wallet.balance
                    )
                    
                    total_transferred += wallet_money
                
                # Transfer from XySave if amount specified
                if xysave_amount and xysave_amount > 0:
                    xysave_account = XySaveAccount.objects.get(user=user)
                    xysave_money = Money(xysave_amount, 'NGN')
                    
                    if xysave_account.balance.amount < xysave_money.amount:
                        raise ValidationError(f"Insufficient XySave balance. Available: {xysave_account.balance}, Required: {xysave_money}")
                    
                    # Deduct from XySave account
                    xysave_account.balance -= xysave_money
                    xysave_account.save()
                    
                    # Create XySave transaction (if XySaveTransaction model exists)
                    try:
                        from .models import XySaveTransaction
                        XySaveTransaction.objects.create(
                            xysave_account=xysave_account,
                            amount=xysave_money,
                            transaction_type='withdrawal',
                            balance_before=xysave_account.balance + xysave_money,
                            balance_after=xysave_account.balance,
                            reference=f"XYS-{uuid.uuid4().hex[:8].upper()}",
                            description=f'Initial transfer to Spend and Save account {account.account_number}'
                        )
                    except ImportError:
                        # XySaveTransaction model might not exist, skip
                        pass
                    
                    total_transferred += xysave_money
                
                # Use total_transferred as the amount to credit
                amount = total_transferred
            
            # Credit to Spend and Save account
            account.balance += amount
            account.save()
            
            # Create Spend and Save transaction
            SpendAndSaveTransaction.objects.create(
                spend_and_save_account=account,
                transaction_type='initial_funding',
                amount=amount,
                balance_before=account.balance - amount,
                balance_after=account.balance,
                reference=f"SAS-{uuid.uuid4().hex[:8].upper()}",
                description=f'Initial funding from {fund_source}',
                withdrawal_destination=None,
                destination_account=None
            )
            
            logger.info(f"Transferred {amount} from {fund_source} to Spend and Save account {account.account_number}")
            
        except Exception as e:
            logger.error(f"Error transferring initial funds from {fund_source}: {str(e)}")
            raise
    
    @staticmethod
    def activate_spend_and_save(user, savings_percentage, fund_source='wallet', initial_amount=None, wallet_amount=None, xysave_amount=None):
        """Activate Spend and Save for a user with specified percentage and fund source"""
        try:
            with transaction.atomic():
                account, created = SpendAndSaveAccount.objects.get_or_create(
                    user=user,
                    defaults={
                        'account_number': SpendAndSaveService._generate_account_number(),
                        'balance': Money(0, 'NGN'),
                        'total_interest_earned': Money(0, 'NGN'),
                        'total_saved_from_spending': Money(0, 'NGN')
                    }
                )
                
                if created:
                    # Create default settings
                    SpendAndSaveSettings.objects.create(
                        user=user,
                        preferred_savings_percentage=savings_percentage,
                        min_transaction_threshold=Money(100, 'NGN'),
                        default_withdrawal_destination='wallet'
                    )
                
                # Handle initial fund transfer if amount is provided
                if fund_source == 'both':
                    if (wallet_amount and wallet_amount > 0) or (xysave_amount and xysave_amount > 0):
                        SpendAndSaveService._transfer_initial_funds(
                            user=user,
                            account=account,
                            fund_source=fund_source,
                            amount=Money(0, 'NGN'),  # Will be calculated in the method
                            wallet_amount=wallet_amount,
                            xysave_amount=xysave_amount
                        )
                elif initial_amount and initial_amount > 0:
                    SpendAndSaveService._transfer_initial_funds(
                        user=user,
                        account=account,
                        fund_source=fund_source,
                        amount=Money(initial_amount, 'NGN')
                    )
                
                account.activate(savings_percentage)
                
                # Send activation notification
                SpendAndSaveNotificationService.send_account_activated_notification(
                    user, account, savings_percentage
                )
                
                logger.info(f"Activated Spend and Save for user {user.username} with {savings_percentage}% from {fund_source}")
                return account
                
        except Exception as e:
            logger.error(f"Error activating Spend and Save for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def deactivate_spend_and_save(user):
        """Deactivate Spend and Save for a user"""
        try:
            account = SpendAndSaveAccount.objects.get(user=user)
            account.deactivate()
            
            # Send deactivation notification
            SpendAndSaveNotificationService.send_account_deactivated_notification(user, account)
            
            logger.info(f"Deactivated Spend and Save for user {user.username}")
            return account
            
        except SpendAndSaveAccount.DoesNotExist:
            raise ValidationError("Spend and Save account not found")
        except Exception as e:
            logger.error(f"Error deactivating Spend and Save for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def process_spending_transaction(transaction_instance):
        """
        Process a spending transaction and automatically save a percentage
        This should be called when a user makes a debit transaction
        """
        logger.info(f"🔍 process_spending_transaction called for transaction {transaction_instance.id}")
        logger.info(f"  Transaction type: {transaction_instance.type}")
        logger.info(f"  Transaction status: {transaction_instance.status}")
        logger.info(f"  Transaction amount: {transaction_instance.amount}")
        logger.info(f"  User: {transaction_instance.wallet.user.username}")
        
        try:
            # Only process debit transactions
            if transaction_instance.type != GeneralStatusChoices.DEBIT:
                logger.info(f"⏭️ Skipping - not a debit transaction (type: {transaction_instance.type})")
                return None
            
            # Get user's Spend and Save account
            try:
                account = SpendAndSaveAccount.objects.get(user=transaction_instance.wallet.user)
                logger.info(f"✅ Found Spend and Save account: {account.account_number}")
                logger.info(f"  Is active: {account.is_active}")
                logger.info(f"  Savings percentage: {account.savings_percentage}%")
                logger.info(f"  Current balance: {account.balance}")
            except SpendAndSaveAccount.DoesNotExist:
                logger.info(f"❌ No Spend and Save account found for user {transaction_instance.wallet.user.username}")
                return None
            
            # Check if Spend and Save is active
            if not account.is_active:
                logger.info(f"⏭️ Skipping - Spend and Save account is not active")
                return None
            
            # Calculate auto-save amount
            logger.info(f"🔢 Calculating auto-save amount...")
            
            # Get the wallet balance after the transfer
            wallet_balance_after_transfer = transaction_instance.balance_after
            logger.info(f"  Wallet balance after transfer: {wallet_balance_after_transfer}")
            
            # Calculate auto-save based on transfer amount
            auto_save_amount = account.process_spending_transaction(transaction_instance.amount)
            logger.info(f"  Calculated auto-save amount: {auto_save_amount}")
            
            if auto_save_amount.amount <= 0:
                logger.info(f"⏭️ Skipping - auto-save amount is 0 or negative")
                return None
            
            logger.info(f"✅ Proceeding with auto-save of {auto_save_amount}")
            
            with transaction.atomic():
                # Determine funding source per user settings and transaction context
                funding_source = 'wallet'
                prefer_xysave_due_to_prefund = False
                try:
                    tx_metadata = getattr(transaction_instance, 'metadata', None) or {}
                    prefer_xysave_due_to_prefund = bool(tx_metadata.get('prefunded_from_xysave'))
                except Exception:
                    prefer_xysave_due_to_prefund = False
                # Load per-user funding preference
                try:
                    user_settings = SpendAndSaveSettings.objects.get(user=account.user)
                    funding_pref = getattr(user_settings, 'funding_preference', 'auto')
                except SpendAndSaveSettings.DoesNotExist:
                    funding_pref = 'auto'
                xysave_account = None
                try:
                    xysave_account = XySaveAccount.objects.get(user=account.user)
                except XySaveAccount.DoesNotExist:
                    xysave_account = None

                def can_use_xysave():
                    return (
                        xysave_account is not None
                        and xysave_account.is_active
                        and xysave_account.balance.amount >= auto_save_amount.amount
                    )

                if funding_pref == 'xysave':
                    if can_use_xysave():
                        funding_source = 'xysave'
                elif funding_pref == 'wallet':
                    funding_source = 'wallet'
                else:  # auto
                    if prefer_xysave_due_to_prefund and can_use_xysave():
                        funding_source = 'xysave'
                    elif can_use_xysave():
                        funding_source = 'xysave'

                if funding_source == 'xysave':
                    # Deduct from XySave account and record a corresponding XySave transaction
                    balance_before_xs = xysave_account.balance
                    xysave_account.balance -= auto_save_amount
                    xysave_account.save()

                    try:
                        from .models import XySaveTransaction
                        XySaveTransaction.objects.create(
                            xysave_account=xysave_account,
                            transaction_type='transfer_out',
                            amount=auto_save_amount,
                            balance_before=balance_before_xs,
                            balance_after=xysave_account.balance,
                            reference=f"XS_XFER_{uuid.uuid4().hex[:12].upper()}",
                            description=f"Auto-save funding to Spend & Save from transaction {transaction_instance.reference}",
                            metadata={'source': 'spend_and_save', 'original_transaction_id': str(transaction_instance.id)}
                        )
                    except Exception:
                        logger.warning("Failed to create XySaveTransaction record for auto-save funding", exc_info=True)
                else:
                    # Fallback: deduct from wallet
                    wallet = transaction_instance.wallet
                    if wallet.balance.amount < auto_save_amount.amount:
                        logger.warning(
                            f"Insufficient wallet balance for auto-save. Required: {auto_save_amount}, Available: {wallet.balance}"
                        )
                        return None
                    wallet.balance -= auto_save_amount
                    wallet.save()
                    logger.info(f"  Deducted {auto_save_amount} from wallet. New balance: {wallet.balance}")
                
                # Create auto-save transaction
                auto_save_tx = SpendAndSaveTransaction.objects.create(
                    spend_and_save_account=account,
                    transaction_type='auto_save',
                    amount=auto_save_amount,
                    balance_before=account.balance,
                    balance_after=account.balance + auto_save_amount,
                    reference=str(uuid.uuid4()),
                    description=f"Auto-save from spending transaction {transaction_instance.reference}",
                    original_transaction_id=transaction_instance.id,
                    original_transaction_amount=transaction_instance.amount,
                    savings_percentage_applied=account.savings_percentage,
                    metadata={'funding_source': funding_source}
                )
                
                # Update account balance
                account.balance += auto_save_amount
                account.total_saved_from_spending += auto_save_amount
                account.total_transactions_processed += 1
                account.last_auto_save_date = timezone.now().date()
                account.save()
                
                # Send spending save notification
                SpendAndSaveNotificationService.send_spending_save_notification(
                    user=account.user,
                    account=account,
                    transaction_amount=transaction_instance.amount.amount,
                    saved_amount=auto_save_amount.amount,
                    total_saved=account.total_saved_from_spending.amount
                )
                
                # Check for milestone notifications
                SpendAndSaveNotificationService.check_and_send_milestone_notifications(account.user, account)
                
                logger.info(f"✅ Successfully processed auto-save of {auto_save_amount} for user {account.user.username}")
                if funding_source == 'wallet':
                    logger.info(f"  Wallet balance after auto-save deduction: {wallet.balance}")
                else:
                    logger.info(f"  XySave balance after auto-save deduction: {xysave_account.balance}")
                logger.info(f"  Spend and Save balance after auto-save: {account.balance}")
                return auto_save_tx
                
        except Exception as e:
            logger.error(f"❌ Error processing spending transaction for auto-save: {str(e)}")
            return None
    
    @staticmethod
    def withdraw_from_spend_and_save(user, amount, destination='wallet'):
        """
        Withdraw from Spend and Save account to specified destination
        """
        try:
            with transaction.atomic():
                account = SpendAndSaveAccount.objects.get(user=user)
                
                if not account.can_withdraw(amount):
                    raise ValidationError("Insufficient balance or account not active")
                
                # Create withdrawal transaction
                withdrawal_tx = SpendAndSaveTransaction.objects.create(
                    spend_and_save_account=account,
                    transaction_type='withdrawal',
                    amount=amount,
                    balance_before=account.balance,
                    balance_after=account.balance - amount,
                    reference=str(uuid.uuid4()),
                    description=f"Withdrawal to {destination}",
                    withdrawal_destination=destination,
                    destination_account=destination
                )
                
                # Update account balance
                account.balance -= amount
                account.save()
                
                # Transfer to destination
                if destination == 'wallet':
                    wallet = Wallet.objects.get(user=user)
                    wallet.balance += amount
                    wallet.save()
                    
                    # Create wallet transaction
                    Transaction.objects.create(
                        wallet=wallet,
                        type='credit',
                        channel='transfer',
                        amount=amount,
                        description=f"Withdrawal from Spend and Save account",
                        status='success',
                        balance_after=wallet.balance
                    )
                    
                elif destination == 'xysave':
                    xysave_account = XySaveAccount.objects.get(user=user)
                    xysave_account.balance += amount
                    xysave_account.save()
                    
                    # Create XySave transaction
                    from .models import XySaveTransaction
                    XySaveTransaction.objects.create(
                        xysave_account=xysave_account,
                        transaction_type='transfer_in',
                        amount=amount,
                        balance_before=xysave_account.balance - amount,
                        balance_after=xysave_account.balance,
                        reference=str(uuid.uuid4()),
                        description=f"Withdrawal from Spend and Save account"
                    )
                
                # Send withdrawal notification
                SpendAndSaveNotificationService.send_withdrawal_notification(
                    user, account, amount, destination
                )
                
                logger.info(f"Withdrew {amount} from Spend and Save account for user {user.username}")
                return withdrawal_tx
                
        except SpendAndSaveAccount.DoesNotExist:
            raise ValidationError("Spend and Save account not found")
        except Exception as e:
            logger.error(f"Error withdrawing from Spend and Save for user {user.username}: {str(e)}")
            raise
    
    @staticmethod
    def calculate_and_credit_interest(user):
        """
        Calculate and credit daily interest to Spend and Save account
        """
        try:
            with transaction.atomic():
                account = SpendAndSaveAccount.objects.get(user=user)
                
                if account.balance.amount <= 0:
                    return None
                
                # Calculate interest using tiered rates
                interest_amount = account.calculate_tiered_interest()
                interest_breakdown = account.get_interest_breakdown()
                
                if interest_amount.amount <= 0:
                    return None
                
                # Create interest credit transaction
                interest_tx = SpendAndSaveTransaction.objects.create(
                    spend_and_save_account=account,
                    transaction_type='interest_credit',
                    amount=interest_amount,
                    balance_before=account.balance,
                    balance_after=account.balance + interest_amount,
                    reference=str(uuid.uuid4()),
                    description="Daily interest credit",
                    interest_earned=interest_amount,
                    interest_breakdown=interest_breakdown
                )
                
                # Update account
                account.balance += interest_amount
                account.total_interest_earned += interest_amount
                account.last_interest_calculation = timezone.now()
                account.save()
                
                # Send interest credited notification
                SpendAndSaveNotificationService.send_interest_credited_notification(
                    user, account, interest_amount.amount, account.total_interest_earned.amount
                )
                
                logger.info(f"Credited {interest_amount} interest to Spend and Save account for user {user.username}")
                return interest_tx
                
        except SpendAndSaveAccount.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error calculating interest for user {user.username}: {str(e)}")
            return None
    
    @staticmethod
    def get_account_summary(user):
        """
        Get comprehensive summary of user's Spend and Save account
        """
        try:
            account = SpendAndSaveAccount.objects.get(user=user)
            settings = SpendAndSaveSettings.objects.get(user=user)
            
            # Calculate current interest breakdown
            interest_breakdown = account.get_interest_breakdown()
            
            # Get recent transactions
            recent_transactions = account.transactions.all()[:10]
            
            return {
                'account': {
                    'account_number': account.account_number,
                    'balance': account.balance,
                    'is_active': account.is_active,
                    'savings_percentage': account.savings_percentage,
                    'total_interest_earned': account.total_interest_earned,
                    'total_saved_from_spending': account.total_saved_from_spending,
                    'total_transactions_processed': account.total_transactions_processed,
                    'last_auto_save_date': account.last_auto_save_date,
                    'default_withdrawal_destination': account.default_withdrawal_destination,
                    'created_at': account.created_at,
                    'updated_at': account.updated_at
                },
                'settings': {
                    'auto_save_notifications': settings.auto_save_notifications,
                    'interest_notifications': settings.interest_notifications,
                    'withdrawal_notifications': settings.withdrawal_notifications,
                    'preferred_savings_percentage': settings.preferred_savings_percentage,
                    'min_transaction_threshold': settings.min_transaction_threshold,
                    'default_withdrawal_destination': settings.default_withdrawal_destination,
                    'interest_payout_frequency': settings.interest_payout_frequency
                },
                'interest_breakdown': interest_breakdown,
                'recent_transactions': [
                    {
                        'id': str(tx.id),
                        'transaction_type': tx.transaction_type,
                        'amount': tx.amount,
                        'description': tx.description,
                        'created_at': tx.created_at,
                        'balance_after': tx.balance_after
                    }
                    for tx in recent_transactions
                ]
            }
            
        except SpendAndSaveAccount.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting account summary for user {user.username}: {str(e)}")
            return None
    
    @staticmethod
    def update_settings(user, **kwargs):
        """
        Update Spend and Save settings
        """
        try:
            settings = SpendAndSaveSettings.objects.get(user=user)
            
            for field, value in kwargs.items():
                if hasattr(settings, field):
                    setattr(settings, field, value)
            
            settings.save()
            
            logger.info(f"Updated Spend and Save settings for user {user.username}")
            return settings
            
        except SpendAndSaveSettings.DoesNotExist:
            raise ValidationError("Spend and Save settings not found")
        except Exception as e:
            logger.error(f"Error updating settings for user {user.username}: {str(e)}")
            raise


class SpendAndSaveInterestService:
    """
    Service for handling interest calculations and payouts
    """
    
    @staticmethod
    def process_daily_interest_payout():
        """
        Process daily interest payout for all active Spend and Save accounts
        This should be called by a scheduled task (e.g., cron job)
        """
        try:
            active_accounts = SpendAndSaveAccount.objects.filter(is_active=True)
            processed_count = 0
            
            for account in active_accounts:
                try:
                    interest_tx = SpendAndSaveService.calculate_and_credit_interest(account.user)
                    if interest_tx:
                        processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing interest for account {account.id}: {str(e)}")
                    continue
            
            logger.info(f"Processed daily interest payout for {processed_count} accounts")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing daily interest payout: {str(e)}")
            return 0
    
    @staticmethod
    def get_interest_forecast(user, days=30):
        """
        Get interest forecast for the next specified number of days
        """
        try:
            account = SpendAndSaveAccount.objects.get(user=user)
            
            if account.balance.amount <= 0:
                return {
                    'daily_interest': Money(0, 'NGN'),
                    'monthly_interest': Money(0, 'NGN'),
                    'annual_interest': Money(0, 'NGN'),
                    'forecast_days': days
                }
            
            # Calculate daily interest
            daily_interest = account.calculate_tiered_interest()
            
            # Calculate monthly and annual
            monthly_interest = daily_interest * 30
            annual_interest = daily_interest * 365
            
            return {
                'daily_interest': daily_interest,
                'monthly_interest': monthly_interest,
                'annual_interest': annual_interest,
                'forecast_days': days,
                'current_balance': account.balance,
                'interest_breakdown': account.get_interest_breakdown()
            }
            
        except SpendAndSaveAccount.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting interest forecast for user {user.username}: {str(e)}")
            return None 