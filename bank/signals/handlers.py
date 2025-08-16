"""
Standardized signal handlers for bank transactions and operations.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from bank.models import BankTransfer, Transaction, Wallet, GeneralStatusChoices
from bank.utils import safe_money_calculation, handle_service_error

logger = logging.getLogger(__name__)


class StandardizedErrorCodes:
    """Standardized error codes for transaction processing."""
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


class BaseSignalHandler:
    """
    Base signal handler providing common functionality for transaction processing.
    """
    
    @staticmethod
    def validate_transfer(sender, instance, **kwargs):
        """
        Standard validation for bank transfers.
        """
        # Skip validation for bulk transfers during processing
        if getattr(instance, '_skip_validation', False):
            return True
            
        # Check if this is an existing transfer being updated
        if instance.pk:
            original = sender.objects.get(pk=instance.pk)
            # If status hasn't changed to a final state, skip validation
            if original.status in [GeneralStatusChoices.SUCCESSFUL, GeneralStatusChoices.COMPLETED, GeneralStatusChoices.FAILED]:
                return True
                
        # Validate transfer details
        errors = []
        
        # Check for self-transfer
        if hasattr(instance.user, 'wallet') and instance.account_number == instance.user.wallet.account_number:
            errors.append("Cannot transfer to own account")
            instance.status = GeneralStatusChoices.FAILED
            instance.failure_reason = StandardizedErrorCodes.SELF_TRANSFER_ATTEMPT
            instance.save()
            return False
            
        # Check amount is positive
        if instance.amount and instance.amount.amount <= 0:
            errors.append("Transfer amount must be positive")
            instance.status = GeneralStatusChoices.FAILED
            instance.failure_reason = StandardizedErrorCodes.VALIDATION_ERROR
            instance.save()
            return False
            
        return True
    
    @staticmethod
    def process_successful_transfer(transfer):
        """
        Process actions that should occur when a transfer is successful.
        """
        try:
            # Update wallet balance
            if hasattr(transfer.user, 'wallet'):
                wallet = transfer.user.wallet
                wallet.balance -= transfer.amount
                if transfer.fee:
                    wallet.balance -= transfer.fee
                if transfer.vat:
                    wallet.balance -= transfer.vat
                if transfer.levy:
                    wallet.balance -= transfer.levy
                wallet.save()
                
            return True
        except Exception as e:
            logger.error(f"Error processing successful transfer {transfer.id}: {str(e)}")
            handle_service_error("process_successful_transfer", e)
            return False
    
    @staticmethod
    def handle_transfer_failure(transfer, error_code, error_message=""):
        """
        Standardized handling of transfer failures.
        """
        try:
            transfer.status = GeneralStatusChoices.FAILED
            transfer.failure_reason = error_code
            if error_message:
                # Append to existing failure reason if it exists
                if transfer.failure_reason:
                    transfer.failure_reason += f"; {error_message}"
                else:
                    transfer.failure_reason = error_message
            transfer.save()
            
            logger.warning(f"Transfer {transfer.id} failed: {error_code} - {error_message}")
            return True
        except Exception as e:
            logger.error(f"Error handling transfer failure for {transfer.id}: {str(e)}")
            return False