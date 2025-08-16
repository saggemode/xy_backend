"""
Enhanced transfer services for bulk transfers, scheduled transfers, escrow, and retry mechanisms.
"""
import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.core.exceptions import ValidationError
from djmoney.money import Money
from .models import (
    BankTransfer, BulkTransfer, BulkTransferItem, ScheduledTransfer,
    EscrowService, TransferReversal, TransferLimit, Wallet, Transaction
)
from .constants import (
    TransferStatus, TransferType, ResponseCodes, RetryConfig,
    CircuitBreakerConfig
)
from .security_services import (
    FraudDetectionService, SecurityAlertService, TransferLimitService,
    TwoFactorAuthService
)

logger = logging.getLogger(__name__)

class BulkTransferService:
    """Service for handling bulk transfer operations."""
    
    @staticmethod
    def create_bulk_transfer(user, title: str, description: str, transfers_data: List[Dict]) -> BulkTransfer:
        """Create a bulk transfer with multiple recipients."""
        try:
            with transaction.atomic():
                # Calculate total amount
                total_amount = sum(Money(transfer['amount'], 'NGN') for transfer in transfers_data)
                
                # Create bulk transfer
                bulk_transfer = BulkTransfer.objects.create(
                    user=user,
                    title=title,
                    description=description,
                    total_amount=total_amount,
                    total_count=len(transfers_data)
                )
                
                # Create individual transfer items
                for index, transfer_data in enumerate(transfers_data):
                    BulkTransferItem.objects.create(
                        bulk_transfer=bulk_transfer,
                        account_number=transfer_data['account_number'],
                        account_name=transfer_data['account_name'],
                        bank_code=transfer_data['bank_code'],
                        bank_name=transfer_data['bank_name'],
                        amount=Money(transfer_data['amount'], 'NGN'),
                        description=transfer_data.get('description', ''),
                        bulk_index=index
                    )
                
                logger.info(f"Bulk transfer created: {bulk_transfer.id} with {len(transfers_data)} items")
                return bulk_transfer
                
        except Exception as e:
            logger.error(f"Error creating bulk transfer: {str(e)}")
            raise
    
    @staticmethod
    def process_bulk_transfer(bulk_transfer: BulkTransfer) -> Dict:
        """Process all items in a bulk transfer."""
        try:
            with transaction.atomic():
                items = bulk_transfer.items.all().order_by('bulk_index')
                completed_count = 0
                failed_count = 0
                
                for item in items:
                    try:
                        # Create individual bank transfer
                        transfer = BankTransfer.objects.create(
                            user=bulk_transfer.user,
                            bank_name=item.bank_name,
                            bank_code=item.bank_code,
                            account_number=item.account_number,
                            amount=item.amount,
                            description=item.description,
                            transfer_type='inter',
                            status='pending',
                            is_bulk=True,
                            bulk_transfer_id=bulk_transfer.id,
                            bulk_index=item.bulk_index
                        )
                        
                        # Process the transfer
                        result = TransferProcessingService.process_transfer(transfer)
                        
                        if result['success']:
                            item.status = TransferStatus.COMPLETED
                            completed_count += 1
                        else:
                            item.status = TransferStatus.FAILED
                            item.error_message = result['error']
                            failed_count += 1
                        
                        item.transfer = transfer
                        item.save()
                        
                    except Exception as e:
                        logger.error(f"Error processing bulk transfer item {item.id}: {str(e)}")
                        item.status = TransferStatus.FAILED
                        item.error_message = str(e)
                        item.save()
                        failed_count += 1
                
                # Update bulk transfer status
                if failed_count == 0:
                    bulk_transfer.status = 'completed'
                elif completed_count == 0:
                    bulk_transfer.status = 'failed'
                else:
                    bulk_transfer.status = 'partial_completed'
                
                bulk_transfer.completed_count = completed_count
                bulk_transfer.failed_count = failed_count
                bulk_transfer.save()
                
                return {
                    'success': True,
                    'completed_count': completed_count,
                    'failed_count': failed_count,
                    'status': bulk_transfer.status
                }
                
        except Exception as e:
            logger.error(f"Error processing bulk transfer: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class ScheduledTransferService:
    """Service for handling scheduled and recurring transfers."""
    
    @staticmethod
    def create_scheduled_transfer(user, transfer_data: Dict) -> ScheduledTransfer:
        """Create a scheduled transfer."""
        try:
            scheduled_transfer = ScheduledTransfer.objects.create(
                user=user,
                transfer_type=transfer_data['transfer_type'],
                amount=Money(transfer_data['amount'], 'NGN'),
                recipient_account=transfer_data['account_number'],
                recipient_bank_code=transfer_data['bank_code'],
                recipient_name=transfer_data['account_name'],
                description=transfer_data.get('description', ''),
                frequency=transfer_data['frequency'],
                start_date=transfer_data['start_date'],
                end_date=transfer_data.get('end_date'),
                next_execution=transfer_data['start_date']
            )
            
            logger.info(f"Scheduled transfer created: {scheduled_transfer.id}")
            return scheduled_transfer
            
        except Exception as e:
            logger.error(f"Error creating scheduled transfer: {str(e)}")
            raise
    
    @staticmethod
    def process_scheduled_transfers() -> Dict:
        """Process all due scheduled transfers."""
        try:
            now = timezone.now()
            due_transfers = ScheduledTransfer.objects.filter(
                next_execution__lte=now,
                is_active=True,
                status=TransferStatus.PENDING
            )
            
            processed_count = 0
            failed_count = 0
            
            for scheduled_transfer in due_transfers:
                try:
                    # Create bank transfer
                    transfer = BankTransfer.objects.create(
                        user=scheduled_transfer.user,
                        bank_name=scheduled_transfer.recipient_bank_code,  # You might want to get actual bank name
                        bank_code=scheduled_transfer.recipient_bank_code,
                        account_number=scheduled_transfer.recipient_account,
                        amount=scheduled_transfer.amount,
                        description=scheduled_transfer.description,
                        transfer_type=scheduled_transfer.transfer_type,
                        status='pending',
                        is_scheduled=True
                    )
                    
                    # Process the transfer
                    result = TransferProcessingService.process_transfer(transfer)
                    
                    if result['success']:
                        # Update next execution
                        ScheduledTransferService._update_next_execution(scheduled_transfer)
                        processed_count += 1
                    else:
                        failed_count += 1
                        logger.error(f"Scheduled transfer failed: {result['error']}")
                    
                except Exception as e:
                    logger.error(f"Error processing scheduled transfer {scheduled_transfer.id}: {str(e)}")
                    failed_count += 1
            
            return {
                'processed_count': processed_count,
                'failed_count': failed_count,
                'total_due': due_transfers.count()
            }
            
        except Exception as e:
            logger.error(f"Error processing scheduled transfers: {str(e)}")
            return {
                'processed_count': 0,
                'failed_count': 0,
                'error': str(e)
            }
    
    @staticmethod
    def _update_next_execution(scheduled_transfer: ScheduledTransfer) -> None:
        """Update the next execution date for a scheduled transfer."""
        try:
            current_next = scheduled_transfer.next_execution
            
            if scheduled_transfer.frequency == 'once':
                scheduled_transfer.is_active = False
                scheduled_transfer.status = TransferStatus.COMPLETED
            elif scheduled_transfer.frequency == 'daily':
                next_execution = current_next + timedelta(days=1)
            elif scheduled_transfer.frequency == 'weekly':
                next_execution = current_next + timedelta(weeks=1)
            elif scheduled_transfer.frequency == 'monthly':
                # Simple monthly calculation
                next_execution = current_next + timedelta(days=30)
            elif scheduled_transfer.frequency == 'yearly':
                next_execution = current_next + timedelta(days=365)
            else:
                return
            
            # Check if we've reached the end date
            if scheduled_transfer.end_date and next_execution > scheduled_transfer.end_date:
                scheduled_transfer.is_active = False
                scheduled_transfer.status = TransferStatus.COMPLETED
            else:
                scheduled_transfer.next_execution = next_execution
            
            scheduled_transfer.save()
            
        except Exception as e:
            logger.error(f"Error updating next execution: {str(e)}")

class EscrowService:
    """Service for handling escrow transfers."""
    
    @staticmethod
    def create_escrow(sender, recipient, amount, description: str, expires_in_hours: int = 24) -> 'EscrowService':
        """Create an escrow transfer."""
        try:
            expires_at = timezone.now() + timedelta(hours=expires_in_hours)
            
            escrow = EscrowService.objects.create(
                sender=sender,
                recipient=recipient,
                amount=Money(amount, 'NGN'),
                description=description,
                expires_at=expires_at
            )
            
            logger.info(f"Escrow created: {escrow.id}")
            return escrow
            
        except Exception as e:
            logger.error(f"Error creating escrow: {str(e)}")
            raise
    
    @staticmethod
    def fund_escrow(escrow: 'EscrowService') -> bool:
        """Fund an escrow transfer."""
        try:
            with transaction.atomic():
                # Check if sender has sufficient balance
                sender_wallet = Wallet.objects.get(user=escrow.sender)
                if sender_wallet.balance < escrow.amount:
                    raise ValidationError('Insufficient balance to fund escrow')
                
                # Deduct amount from sender
                sender_wallet.balance = sender_wallet.balance - escrow.amount
                sender_wallet.save()
                
                # Update escrow status
                escrow.status = 'funded'
                escrow.funded_at = timezone.now()
                escrow.save()
                
                logger.info(f"Escrow funded: {escrow.id}")
                return True
                
        except Exception as e:
            logger.error(f"Error funding escrow: {str(e)}")
            return False
    
    @staticmethod
    def release_escrow(escrow: 'EscrowService') -> bool:
        """Release escrow funds to recipient."""
        try:
            with transaction.atomic():
                if escrow.status != 'funded':
                    raise ValidationError('Escrow must be funded before release')
                
                # Credit recipient
                recipient_wallet = Wallet.objects.get(user=escrow.recipient)
                recipient_wallet.balance = recipient_wallet.balance + escrow.amount
                recipient_wallet.save()
                
                # Update escrow status
                escrow.status = 'released'
                escrow.released_at = timezone.now()
                escrow.save()
                
                logger.info(f"Escrow released: {escrow.id}")
                return True
                
        except Exception as e:
            logger.error(f"Error releasing escrow: {str(e)}")
            return False
    
    @staticmethod
    def refund_escrow(escrow: 'EscrowService') -> bool:
        """Refund escrow funds to sender."""
        try:
            with transaction.atomic():
                if escrow.status != 'funded':
                    raise ValidationError('Escrow must be funded before refund')
                
                # Refund sender
                sender_wallet = Wallet.objects.get(user=escrow.sender)
                sender_wallet.balance = sender_wallet.balance + escrow.amount
                sender_wallet.save()
                
                # Update escrow status
                escrow.status = 'refunded'
                escrow.refunded_at = timezone.now()
                escrow.save()
                
                logger.info(f"Escrow refunded: {escrow.id}")
                return True
                
        except Exception as e:
            logger.error(f"Error refunding escrow: {str(e)}")
            return False

class TransferReversalService:
    """Service for handling transfer reversals and refunds."""
    
    @staticmethod
    def create_reversal(original_transfer: BankTransfer, reason: str, description: str, initiated_by) -> TransferReversal:
        """Create a transfer reversal."""
        try:
            reversal = TransferReversal.objects.create(
                original_transfer=original_transfer,
                reason=reason,
                description=description,
                amount=original_transfer.amount,
                initiated_by=initiated_by
            )
            
            logger.info(f"Transfer reversal created: {reversal.id}")
            return reversal
            
        except Exception as e:
            logger.error(f"Error creating transfer reversal: {str(e)}")
            raise
    
    @staticmethod
    def process_reversal(reversal: TransferReversal, approved_by=None) -> bool:
        """Process a transfer reversal."""
        try:
            with transaction.atomic():
                original_transfer = reversal.original_transfer
                
                # Create reversal transfer
                reversal_transfer = BankTransfer.objects.create(
                    user=original_transfer.user,
                    bank_name=original_transfer.bank_name,
                    bank_code=original_transfer.bank_code,
                    account_number=original_transfer.account_number,
                    amount=original_transfer.amount,
                    description=f"Reversal: {reversal.description}",
                    transfer_type=original_transfer.transfer_type,
                    status='pending'
                )
                
                # Process the reversal transfer
                result = TransferProcessingService.process_transfer(reversal_transfer)
                
                if result['success']:
                    reversal.status = TransferStatus.COMPLETED
                    reversal.reversal_transfer = reversal_transfer
                    reversal.processed_at = timezone.now()
                    if approved_by:
                        reversal.approved_by = approved_by
                    reversal.save()
                    
                    logger.info(f"Transfer reversal processed: {reversal.id}")
                    return True
                else:
                    reversal.status = TransferStatus.FAILED
                    reversal.save()
                    
                    logger.error(f"Transfer reversal failed: {result['error']}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error processing transfer reversal: {str(e)}")
            return False

class TransferProcessingService:
    """Service for processing transfers with retry mechanisms and circuit breakers."""
    
    @staticmethod
    def process_transfer(transfer: BankTransfer) -> Dict:
        """Process a transfer with retry logic and circuit breaker."""
        try:
            # Enforce Night Guard if applicable (app-only, time-windowed, face + fallback)
            try:
                from .security_services import NightGuardService
                ng = NightGuardService.apply_night_guard(transfer)
                if ng.get('required'):
                    # Expect client to complete face verification first. If client marks
                    # face failure, fallback (e.g., 2FA) is already flagged via requires_2fa.
                    metadata = transfer.metadata or {}
                    if metadata.get('night_guard_status') not in {'face_passed', 'fallback_passed'}:
                        return {
                            'success': False,
                            'error': 'Night Guard verification required',
                            'night_guard': ng,
                        }
            except Exception as _:
                # Do not block transfers if Night Guard check fails; proceed normally
                pass

            # Enforce Large Transaction Shield if thresholds exceeded (app-only)
            try:
                from .security_services import LargeTransactionShieldService
                lts = LargeTransactionShieldService.apply_shield(transfer)
                if lts.get('required'):
                    metadata = transfer.metadata or {}
                    if metadata.get('large_tx_shield_status') not in {'face_passed', 'fallback_passed'}:
                        return {
                            'success': False,
                            'error': 'Large Transaction Shield verification required',
                            'large_tx_shield': lts,
                        }
            except Exception as _:
                pass

            # Enforce Location Guard (app-only, out-of-allowed states)
            try:
                from .security_services import LocationGuardService
                lg = LocationGuardService.apply_guard(transfer)
                if lg.get('required'):
                    metadata = transfer.metadata or {}
                    if metadata.get('location_guard_status') not in {'face_passed', 'fallback_passed'}:
                        return {
                            'success': False,
                            'error': 'Location Guard verification required',
                            'location_guard': lg,
                        }
            except Exception as _:
                pass

            # Check circuit breaker
            if transfer.circuit_breaker_tripped:
                return {
                    'success': False,
                    'error': 'Circuit breaker is tripped'
                }
            
            # Check retry limits
            if transfer.retry_count >= transfer.max_retries:
                transfer.mark_as_failed('Maximum retry attempts exceeded')
                return {
                    'success': False,
                    'error': 'Maximum retry attempts exceeded'
                }
            
            # Process the transfer
            result = TransferProcessingService._execute_transfer(transfer)
            
            if result['success']:
                transfer.mark_as_completed()
                transfer.processing_completed_at = timezone.now()
                transfer.save()
                
                return {'success': True}
            else:
                # Increment retry count
                transfer.retry_count += 1
                transfer.last_retry_at = timezone.now()
                transfer.save()
                
                # Check if we should trip circuit breaker
                if transfer.retry_count >= CircuitBreakerConfig.FAILURE_THRESHOLD:
                    transfer.circuit_breaker_tripped = True
                    transfer.save()
                
                return {
                    'success': False,
                    'error': result['error'],
                    'retry_count': transfer.retry_count
                }
                
        except Exception as e:
            logger.error(f"Error processing transfer {transfer.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _execute_transfer(transfer: BankTransfer) -> Dict:
        """Execute the actual transfer logic."""
        try:
            with transaction.atomic():
                # Get sender wallet
                sender_wallet = Wallet.objects.get(user=transfer.user)
                
                # Calculate total deduction (amount + fees)
                total_deduction = transfer.amount + transfer.fee + transfer.vat + transfer.levy
                
                # Check balance
                if sender_wallet.balance < total_deduction:
                    return {
                        'success': False,
                        'error': 'Insufficient balance'
                    }
                
                # Deduct from sender
                sender_wallet.balance = sender_wallet.balance - total_deduction
                sender_wallet.save()
                
                # Check if internal transfer
                try:
                    receiver_wallet = Wallet.objects.get(account_number=transfer.account_number)
                    # Credit receiver
                    receiver_wallet.balance = receiver_wallet.balance + transfer.amount
                    receiver_wallet.save()
                    
                    # Create transaction records
                    TransferProcessingService._create_transaction_records(transfer, sender_wallet, receiver_wallet)
                    
                except Wallet.DoesNotExist:
                    # External transfer - just create transaction records
                    TransferProcessingService._create_transaction_records(transfer, sender_wallet)
                
                return {'success': True}
                
        except Exception as e:
            logger.error(f"Error executing transfer: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _create_transaction_records(transfer: BankTransfer, sender_wallet: Wallet, receiver_wallet: Wallet = None):
        """Create transaction records for the transfer."""
        try:
            # Debit transaction for sender
            Transaction.objects.create(
                wallet=sender_wallet,
                amount=transfer.amount,
                type='debit',
                channel='transfer',
                description=f"Transfer to {transfer.account_number}",
                status='success',
                balance_after=sender_wallet.balance
            )
            
            # Credit transaction for receiver (if internal)
            if receiver_wallet:
                Transaction.objects.create(
                    wallet=receiver_wallet,
                    amount=transfer.amount,
                    type='credit',
                    channel='transfer',
                    description=f"Transfer from {sender_wallet.account_number}",
                    status='success',
                    balance_after=receiver_wallet.balance
                )
                
        except Exception as e:
            logger.error(f"Error creating transaction records: {str(e)}")
            raise

class IdempotencyService:
    """Service for handling idempotency to prevent duplicate transfers."""
    
    @staticmethod
    def generate_idempotency_key(user_id: int, transfer_data: Dict) -> str:
        """Generate an idempotency key for a transfer."""
        try:
            # Create a unique key based on user and transfer data
            key_data = {
                'user_id': user_id,
                'amount': str(transfer_data.get('amount', '')),
                'account_number': transfer_data.get('account_number', ''),
                'bank_code': transfer_data.get('bank_code', ''),
                'timestamp': int(timezone.now().timestamp())
            }
            
            import hashlib
            key_string = json.dumps(key_data, sort_keys=True)
            return hashlib.sha256(key_string.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error generating idempotency key: {str(e)}")
            return str(uuid.uuid4())
    
    @staticmethod
    def check_idempotency_key(key: str) -> Optional[BankTransfer]:
        """Check if an idempotency key already exists."""
        try:
            return BankTransfer.objects.filter(idempotency_key=key).first()
        except Exception as e:
            logger.error(f"Error checking idempotency key: {str(e)}")
            return None 