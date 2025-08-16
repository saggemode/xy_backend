import logging
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from bank.models import BankTransfer, Transaction, Wallet, TransferFailure, GeneralStatusChoices, XySaveTransaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from bank.spend_and_save_services import SpendAndSaveService
from bank.xysave_services import (
    XySaveAutoSaveService,
    XySaveAccountService,
    XySaveTransactionService,
)
from bank.security_services import NightGuardService, LargeTransactionShieldService, LocationGuardService

logger = logging.getLogger(__name__)

# Define standardized error codes for better failure tracking
class TransferErrorCodes:
    INSUFFICIENT_FUNDS = 'INSUFFICIENT_FUNDS'
    SELF_TRANSFER_ATTEMPT = 'SELF_TRANSFER_ATTEMPT'
    WALLET_NOT_FOUND = 'WALLET_NOT_FOUND'
    PROCESSING_ERROR = 'PROCESSING_ERROR'
    DATABASE_ERROR = 'DATABASE_ERROR'
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    EXTERNAL_SERVICE_ERROR = 'EXTERNAL_SERVICE_ERROR'
    FRAUD_DETECTION = 'FRAUD_DETECTION'
    LIMIT_EXCEEDED = 'LIMIT_EXCEEDED'
    KYC_REQUIRED = 'KYC_REQUIRED'
    ACCOUNT_BLOCKED = 'ACCOUNT_BLOCKED'
    INVALID_ACCOUNT = 'INVALID_ACCOUNT'
    BANK_SERVICE_UNAVAILABLE = 'BANK_SERVICE_UNAVAILABLE'
    TIMEOUT_ERROR = 'TIMEOUT_ERROR'
    DUPLICATE_TRANSACTION = 'DUPLICATE_TRANSACTION'


def create_transaction_records(sender_wallet, receiver_wallet, amount, transfer_instance, description):
    """Create transaction records for both sender and receiver."""
    try:
        # Get content type for BankTransfer
        content_type = ContentType.objects.get_for_model(BankTransfer)
        
        # Create sender transaction (DEBIT)
        sender_transaction = Transaction.objects.create(
            wallet=sender_wallet,
            receiver=receiver_wallet,
            reference=f"TXN-{uuid.uuid4().hex[:8].upper()}",
            amount=amount,
            type=GeneralStatusChoices.DEBIT,
            channel=GeneralStatusChoices.TRANSFER,
            description=description,
            status=GeneralStatusChoices.SUCCESS,
            balance_after=sender_wallet.balance,
            content_type=content_type,
            object_id=str(transfer_instance.id),
            metadata={
                'transfer_id': str(transfer_instance.id),
                'transfer_type': 'internal',
                'recipient_account': receiver_wallet.account_number,
                'recipient_name': receiver_wallet.user.get_full_name() or receiver_wallet.user.username
            }
        )
        
        # Create receiver transaction (CREDIT)
        receiver_transaction = Transaction.objects.create(
            wallet=receiver_wallet,
            receiver=None,  # No receiver for credit transactions
            reference=f"TXN-{uuid.uuid4().hex[:8].upper()}",
            amount=amount,
            type=GeneralStatusChoices.CREDIT,
            channel=GeneralStatusChoices.TRANSFER,
            description=f"Received {amount} from {sender_wallet.account_number}",
            status=GeneralStatusChoices.SUCCESS,
            balance_after=receiver_wallet.balance,
            content_type=content_type,
            object_id=str(transfer_instance.id),
            metadata={
                'transfer_id': str(transfer_instance.id),
                'transfer_type': 'internal',
                'sender_account': sender_wallet.account_number,
                'sender_name': sender_wallet.user.get_full_name() or sender_wallet.user.username
            }
        )
        
        logger.info(f"Created transaction records - Sender: {sender_transaction.id}, Receiver: {receiver_transaction.id}")
        return sender_transaction, receiver_transaction
        
    except Exception as e:
        logger.error(f"Error creating transaction records: {str(e)}")
        raise


def send_transfer_notifications(sender_wallet, receiver_wallet, amount, transfer_instance):
    """Send email and SMS notifications for successful transfer."""
    try:
        # Email notification for sender
        sender_email = sender_wallet.user.email
        if sender_email:
            # TODO: Implement email sending logic
            logger.info(f"Would send email to sender {sender_email} for transfer {transfer_instance.id}")
            # Example: send_email_notification(sender_email, 'transfer_sent', {
            #     'amount': amount,
            #     'recipient': receiver_wallet.account_number,
            #     'reference': transfer_instance.reference
            # })
        
        # SMS notification for sender
        sender_phone = getattr(sender_wallet.user, 'phone', None)
        if sender_phone:
            # TODO: Implement SMS sending logic
            logger.info(f"Would send SMS to sender {sender_phone} for transfer {transfer_instance.id}")
            # Example: send_sms_notification(sender_phone, 'transfer_sent', {
            #     'amount': amount,
            #     'recipient': receiver_wallet.account_number
            # })
        
        # Email notification for receiver
        receiver_email = receiver_wallet.user.email
        if receiver_email:
            # TODO: Implement email sending logic
            logger.info(f"Would send email to receiver {receiver_email} for transfer {transfer_instance.id}")
            # Example: send_email_notification(receiver_email, 'transfer_received', {
            #     'amount': amount,
            #     'sender': sender_wallet.account_number,
            #     'reference': transfer_instance.reference
            # })
        
        # SMS notification for receiver
        receiver_phone = getattr(receiver_wallet.user, 'phone', None)
        if receiver_phone:
            # TODO: Implement SMS sending logic
            logger.info(f"Would send SMS to receiver {receiver_phone} for transfer {transfer_instance.id}")
            # Example: send_sms_notification(receiver_phone, 'transfer_received', {
            #     'amount': amount,
            #     'sender': sender_wallet.account_number
            # })
        
        logger.info(f"Notifications logged for transfer {transfer_instance.id}")
        
    except Exception as e:
        logger.error(f"Error sending notifications for transfer {transfer_instance.id}: {str(e)}")
        # Don't fail the transfer if notifications fail


@receiver(post_save, sender=BankTransfer)
def handle_bank_transfer(sender, instance, created, **kwargs):
    """Handle bank transfer processing with comprehensive failure tracking."""
    if not created or instance.status != GeneralStatusChoices.PENDING:
        return
    
    logger.info(f"Processing bank transfer {instance.id} - amount: {instance.amount}, account: {instance.account_number}")
    
    try:
        # Night Guard: If required and not yet verified, don't process further
        ng = NightGuardService.apply_night_guard(instance)
        if ng.get('required'):
            status = (instance.metadata or {}).get('night_guard_status')
            if status not in {'face_passed', 'fallback_passed'}:
                logger.info(f"Night Guard active for transfer {instance.id}; awaiting verification. status={status}")
                return

        # Large Transaction Shield: gate if required and not verified
        lts = LargeTransactionShieldService.apply_shield(instance)
        if lts.get('required'):
            lts_status = (instance.metadata or {}).get('large_tx_shield_status')
            if lts_status not in {'face_passed', 'fallback_passed'}:
                logger.info(f"Large Transaction Shield active for transfer {instance.id}; awaiting verification. status={lts_status}")
                return

        # Location Guard: gate if required and not verified
        lg = LocationGuardService.apply_guard(instance)
        if lg.get('required'):
            lg_status = (instance.metadata or {}).get('location_guard_status')
            if lg_status not in {'face_passed', 'fallback_passed'}:
                logger.info(f"Location Guard active for transfer {instance.id}; awaiting verification. status={lg_status}")
                return

        # Find sender wallet
        sender_wallet = Wallet.objects.filter(user=instance.user).first()
        if not sender_wallet:
            logger.error(f"Sender wallet not found for user {instance.user.id}")
            instance.mark_as_failed(
                reason='Sender wallet not found',
                error_code=TransferErrorCodes.WALLET_NOT_FOUND,
                technical_details={
                    'user_id': instance.user.id,
                    'transfer_id': str(instance.id)
                }
            )
            return
        
        logger.info(f"Found sender wallet: {sender_wallet.account_number}, balance: {sender_wallet.balance}")

        # Prefer funding from XySave if enabled and sufficient, then proceed with normal wallet transfer
        prefunded_from_xysave = False
        try:
            xysave_account = XySaveAccountService.get_xysave_account(instance.user)
            if getattr(xysave_account, 'is_active', True) and xysave_account.balance.amount >= instance.amount.amount:
                logger.info(
                    f"Using XySave to fund transfer {instance.id}. Moving {instance.amount} from XySave to wallet"
                )
                # Move funds from XySave to wallet to fund the transfer
                XySaveTransactionService.withdraw_from_xysave(
                    instance.user,
                    instance.amount,
                    description=f"Funding wallet for transfer {instance.account_number}"
                )
                # Refresh wallet after top-up
                sender_wallet.refresh_from_db()
                prefunded_from_xysave = True
        except Exception as e:
            logger.warning(f"Could not prefund from XySave for transfer {instance.id}: {str(e)}")
        
        # Check for self-transfer
        if instance.account_number == sender_wallet.account_number:
            logger.warning(f"Self-transfer attempt detected for user {instance.user.id}")
            instance.mark_as_failed(
                reason='Self-transfer is not allowed',
                error_code=TransferErrorCodes.SELF_TRANSFER_ATTEMPT,
                technical_details={
                    'sender_account': sender_wallet.account_number,
                    'recipient_account': instance.account_number,
                    'user_id': instance.user.id
                }
            )
            return
        
        # Check sufficient balance (after potential XySave top-up)
        if sender_wallet.balance < instance.amount:
            logger.warning(f"Insufficient funds in sender wallet {sender_wallet.account_number}. Balance: {sender_wallet.balance}, Required: {instance.amount}")
            instance.mark_as_failed(
                reason='Insufficient funds in sender wallet',
                error_code=TransferErrorCodes.INSUFFICIENT_FUNDS,
                technical_details={
                    'sender_account': sender_wallet.account_number,
                    'available_balance': float(sender_wallet.balance.amount) if hasattr(sender_wallet.balance, 'amount') else float(sender_wallet.balance),
                    'required_amount': float(instance.amount.amount) if hasattr(instance.amount, 'amount') else float(instance.amount),
                    'shortfall': float(instance.amount.amount - sender_wallet.balance.amount) if hasattr(instance.amount, 'amount') and hasattr(sender_wallet.balance, 'amount') else float(instance.amount - sender_wallet.balance)
                }
            )
            return
        
        # Find receiver wallet (internal transfer) - check both primary and alternative account numbers
        receiver_wallet = Wallet.objects.filter(
            models.Q(account_number=instance.account_number) | 
            models.Q(alternative_account_number=instance.account_number)
        ).first()
        
        if receiver_wallet:
            account_type = "primary" if receiver_wallet.account_number == instance.account_number else "alternative"
            logger.info(f"Found internal receiver by {account_type} account: {instance.account_number}")
            # Internal transfer
            try:
                # Deduct from sender
                sender_wallet.balance -= instance.amount
                sender_wallet.save()
                
                # Add to receiver
                receiver_wallet.balance += instance.amount
                receiver_wallet.save()
                
                # Create transaction records
                description = f"Transfer to {receiver_wallet.account_number}"
                sender_transaction, receiver_transaction = create_transaction_records(
                    sender_wallet, receiver_wallet, instance.amount, instance, description
                )
                # Mark that this debit was prefunded from XySave to help downstream logic
                if prefunded_from_xysave:
                    try:
                        metadata = sender_transaction.metadata or {}
                        metadata['prefunded_from_xysave'] = True
                        sender_transaction.metadata = metadata
                        sender_transaction.save(update_fields=['metadata'])
                    except Exception as e:
                        logger.warning(f"Failed to annotate transaction {sender_transaction.id} with XySave prefund flag: {str(e)}")
                
                # Send notifications
                send_transfer_notifications(sender_wallet, receiver_wallet, instance.amount, instance)
                
                # Mark as successful
                instance.status = GeneralStatusChoices.SUCCESSFUL
                instance.processing_completed_at = timezone.now()
                instance.save(update_fields=['status', 'processing_completed_at', 'updated_at'])
                
                logger.info(f"Internal transfer completed successfully: {instance.id}")
                logger.info(f"Created transactions - Sender: {sender_transaction.id}, Receiver: {receiver_transaction.id}")
                
            except Exception as e:
                logger.error(f"Error processing internal transfer {instance.id}: {str(e)}")
                instance.mark_as_failed(
                    reason=f'Processing error: {str(e)}',
                    error_code=TransferErrorCodes.PROCESSING_ERROR,
                    technical_details={
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'transfer_id': str(instance.id),
                        'user_id': instance.user.id,
                        'amount': float(instance.amount.amount) if hasattr(instance.amount, 'amount') else float(instance.amount),
                        'account_number': instance.account_number
                    }
                )
        else:
            # External transfer - mark as pending for external processing
            logger.info(f"External transfer initiated: {instance.id}")
            instance.status = GeneralStatusChoices.PROCESSING
            instance.save(update_fields=['status', 'updated_at'])
            
    except Exception as e:
        logger.error(f"Error processing bank transfer {instance.id}: {str(e)}")
        instance.mark_as_failed(
            reason=f'Processing error: {str(e)}',
            error_code=TransferErrorCodes.PROCESSING_ERROR,
            technical_details={
                'error_type': type(e).__name__,
                'error_message': str(e),
                'transfer_id': str(instance.id),
                'user_id': instance.user.id,
                'amount': float(instance.amount.amount) if hasattr(instance.amount, 'amount') else float(instance.amount),
                'account_number': instance.account_number
            }
        ) 


@receiver(post_save, sender=Transaction)
def process_spend_and_save_on_transaction(sender, instance, created, **kwargs):
    """
    Automatically process Spend and Save when a debit transaction is created.
    This signal will trigger the automatic saving functionality.
    """
    logger.info(f"🔍 Signal triggered for transaction {instance.id} - created: {created}, type: {instance.type}, status: {instance.status}")
    
    if not created:
        logger.info(f"⏭️ Skipping - not a new transaction")
        return
    
    # Only process debit transactions (spending transactions)
    if instance.type != GeneralStatusChoices.DEBIT:
        logger.info(f"⏭️ Skipping - not a debit transaction (type: {instance.type})")
        return
    
    # Only process successful transactions
    if instance.status != GeneralStatusChoices.SUCCESS:
        logger.info(f"⏭️ Skipping - not a successful transaction (status: {instance.status})")
        return
    
    try:
        logger.info(f"✅ Processing Spend and Save for transaction {instance.id} - amount: {instance.amount}")
        
        # Process the spending transaction for auto-save
        auto_save_tx = SpendAndSaveService.process_spending_transaction(instance)
        
        if auto_save_tx:
            logger.info(f"✅ Successfully processed auto-save for transaction {instance.id}. Auto-save amount: {auto_save_tx.amount}")
        else:
            logger.info(f"⚠️ No auto-save processed for transaction {instance.id} (user may not have active Spend and Save account)")
            
    except Exception as e:
        logger.error(f"❌ Error processing Spend and Save for transaction {instance.id}: {str(e)}")
        # Don't fail the transaction if Spend and Save processing fails 


@receiver(post_save, sender=Transaction)
def auto_sweep_to_xysave_on_credit(sender, instance, created, **kwargs):
    """Auto-sweep wallet credits to XySave when enabled."""
    if not created:
        return
    if instance.type != GeneralStatusChoices.CREDIT:
        return
    if instance.status != GeneralStatusChoices.SUCCESS:
        return

    try:
        # Ensure account exists and is enabled
        xysave_account = XySaveAccountService.get_xysave_account(instance.wallet.user)
        if not getattr(xysave_account, 'auto_save_enabled', False):
            return

        logger.info(
            f"Auto-sweeping {instance.amount} from wallet {instance.wallet.account_number} to XySave for user {instance.wallet.user.id}"
        )
        # Deposit full credited amount to XySave (sweeps from wallet)
        XySaveTransactionService().deposit_to_xysave(
            instance.wallet.user,
            instance.amount,
            description=f"Auto-sweep from wallet credit {instance.reference}"
        )
    except Exception as e:
        logger.error(f"Failed to auto-sweep credit to XySave for transaction {instance.id}: {str(e)}")


@receiver(post_save, sender=XySaveTransaction)
def process_spend_and_save_for_xysave_transaction(sender, instance, created, **kwargs):
    """
    Process Spend and Save when a withdrawal or transfer_out transaction occurs in XySave account.
    This ensures that when money is removed from XySave account, the Spend and Save percentage
    is also automatically deducted and sent to the Spend and Save account.
    """
    if not created:
        return
    
    # Only process withdrawal or transfer_out transactions
    if instance.transaction_type not in ['withdrawal', 'transfer_out']:
        return
    
    try:
        from .spend_and_save_services import SpendAndSaveService
        from djmoney.money import Money
        from bank.models import GeneralStatusChoices
        from bank.models import GeneralStatusChoices
        
        # Create a mock transaction object to pass to SpendAndSaveService
        # This mimics a wallet transaction but uses XySave account data
        class MockTransaction:
            def __init__(self, xysave_transaction):
                self.id = xysave_transaction.id
                self.type = GeneralStatusChoices.DEBIT
                self.status = GeneralStatusChoices.SUCCESS
                self.amount = xysave_transaction.amount
                self.description = xysave_transaction.description
                # For balance after, we approximate it as the balance after the transaction
                self.balance_after = xysave_transaction.balance_after
                # Create a mock wallet that points to the user
                self.wallet = type('MockWallet', (), {})()
                self.wallet.user = xysave_transaction.xysave_account.user
                self.reference = xysave_transaction.reference
                self.timestamp = xysave_transaction.created_at
                
        # Create the mock transaction
        mock_transaction = MockTransaction(instance)
        
        # Process this through SpendAndSaveService
        # Add metadata to indicate this is prefunded from XySave
        mock_transaction.metadata = getattr(mock_transaction, 'metadata', {})
        mock_transaction.metadata['prefunded_from_xysave'] = True
        
        # Process the spending transaction
        SpendAndSaveService.process_spending_transaction(mock_transaction)
        
    except Exception as e:
        logger.error(f"Error processing Spend and Save for XySave transaction {instance.id}: {str(e)}")
