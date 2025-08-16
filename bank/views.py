from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
import logging
import hashlib
import uuid
from typing import Dict, Any
from .models import (
    Wallet, Transaction, BankTransfer, BillPayment, VirtualCard, Bank, CBNLevy,
    StaffRole, StaffProfile, TransactionApproval, CustomerEscalation, StaffActivity,
    TransferFeeRule, SavedBeneficiary, TransferReversal, TransactionCharge, TransferFailure
)
from .serializers import (
    WalletSerializer, TransactionSerializer, BankTransferSerializer, BillPaymentSerializer, 
    BankSerializer, StaffRoleSerializer, StaffProfileSerializer, TransactionApprovalSerializer, 
    CustomerEscalationSerializer, StaffActivitySerializer, TransferFeeRuleSerializer,
    SavedBeneficiarySerializer, TransferReversalSerializer, KYCProfileDetailSerializer,
    TransferFailureSerializer, NightGuardSettingsSerializer, LargeTransactionShieldSettingsSerializer, LocationGuardSettingsSerializer, PaymentIntentSerializer, PaymentIntentCreateSerializer, PayoutRequestSerializer
)
from .security_services import NightGuardService
from .security_services import TwoFactorAuthService as Security2FAService
from .security_services import LargeTransactionShieldService, LocationGuardService
from djmoney.money import Money
from accounts.utils import log_audit_event, get_client_ip, get_user_agent
from accounts.models import KYCProfile
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.db.models import Q, Count
from .fees import calculate_transfer_fees, get_active_vat_rate
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
# from weasyprint import HTML
from django.http import HttpResponse
from decimal import Decimal
from .nibss import NIBSSClient
from .services import (
    BankAccountService, TransferValidationService, FraudDetectionService,
    TwoFactorAuthService, DeviceFingerprintService, IdempotencyService,
    BiometricService
)
from .constants import TransferStatus, TransferType, SecurityLevel, ErrorCodes

logger = logging.getLogger(__name__)

# Remove KYCProfileViewSet and related KYC views from this file.
# Update imports to use from accounts.views if needed.


class WalletViewSet(ReadOnlyModelViewSet):
    """ViewSet for Wallet operations (read-only)."""
    permission_classes = [IsAuthenticated]
    serializer_class = WalletSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['balance', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return wallets based on user permissions."""
        if self.request.user.is_staff:
            return Wallet.objects.all()
        return Wallet.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_wallet(self, request):
        """Get current user's wallet."""
        try:
            wallet = Wallet.objects.get(user=request.user)
            serializer = self.get_serializer(wallet)
            return Response(serializer.data)
        except Wallet.DoesNotExist:
            return Response({
                'detail': 'Wallet not found. Complete KYC verification first.'
            }, status=status.HTTP_404_NOT_FOUND)


class TransactionViewSet(ReadOnlyModelViewSet):
    """ViewSet for Transaction operations (read-only)."""
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'channel', 'status', 'timestamp']
    search_fields = ['reference', 'description']
    ordering_fields = ['amount', 'timestamp']
    ordering = ['-timestamp']

    def get_queryset(self):
        """Return transactions based on user permissions."""
        if self.request.user.is_staff:
            return Transaction.objects.all()
        try:
            wallet = Wallet.objects.get(user=self.request.user)
            return Transaction.objects.filter(wallet=wallet)
        except Wallet.DoesNotExist:
            return Transaction.objects.none()

    @action(detail=False, methods=['get'])
    def my_transactions(self, request):
        """Get current user's transactions."""
        try:
            wallet = Wallet.objects.get(user=request.user)
            transactions = Transaction.objects.filter(wallet=wallet).order_by('-timestamp')
            serializer = self.get_serializer(transactions, many=True)
            return Response(serializer.data)
        except Wallet.DoesNotExist:
            return Response({
                'detail': 'Wallet not found. Complete KYC verification first.'
            }, status=status.HTTP_404_NOT_FOUND)


class BankTransferViewSet(ModelViewSet):
    """ViewSet for Bank Transfer operations."""
    permission_classes = [IsAuthenticated]
    serializer_class = BankTransferSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'bank_name', 'created_at']
    search_fields = ['recipient_name', 'account_number', 'reference']
    ordering_fields = ['amount', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return bank transfers based on user permissions."""
        if self.request.user.is_staff:
            return BankTransfer.objects.all()
        return BankTransfer.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='validate-account')
    def validate_account(self, request):
        """
        Validate account number and return bank info and account holder name.
        This simulates NIBSS account validation.
        """
        account_number = request.data.get('account_number')
        
        if not account_number:
            return Response(
                {'error': 'Account number is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate account number format (10 digits for Nigerian banks)
        if not account_number.isdigit() or len(account_number) != 10:
            return Response(
                {'error': 'Invalid account number format. Must be 10 digits.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # First check if it's an internal account
            internal_wallet = Wallet.objects.get(account_number=account_number)
            return Response({
                'account_number': account_number,
                'account_name': f"{internal_wallet.user.first_name} {internal_wallet.user.last_name}".strip(),
                'bank_name': 'XYPay Bank',
                'bank_code': '880',
                'is_internal': True,
                'status': 'valid'
            })
        except Wallet.DoesNotExist:
            # Check external banks (simulated)
            nibss_client = NIBSSClient()
            validation_result = nibss_client.validate_account_number(account_number)
            
            if validation_result['valid']:
                return Response({
                    'account_number': account_number,
                    'account_name': validation_result['account_name'],
                    'bank_name': validation_result['bank_name'],
                    'bank_code': validation_result['bank_code'],
                    'is_internal': False,
                    'status': 'valid'
                })
            else:
                return Response({
                    'account_number': account_number,
                    'error': validation_result['error'],
                    'status': 'invalid'
                }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='banks')
    def get_banks(self, request):
        """
        Get list of all available banks for transfer.
        """
        banks = Bank.objects.all().order_by('name')
        bank_list = []
        
        for bank in banks:
            bank_list.append({
                'id': bank.id,
                'name': bank.name,
                'code': bank.code,
                'slug': bank.slug,
                'ussd': bank.ussd,
                'logo': bank.logo
            })
        
        return Response({
            'banks': bank_list,
            'count': len(bank_list)
        })

    # Payments: Payment Intents
    @action(detail=False, methods=['post'], url_path='payment-intents')
    def create_payment_intent(self, request):
        """Create a payment intent for marketplace/social checkout using wallet."""
        try:
            serializer = PaymentIntentCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            intent = serializer.save(user=request.user, status='requires_confirmation')
            return Response(PaymentIntentSerializer(intent).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            return Response({'error': 'Failed to create payment intent'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='confirm-payment')
    def confirm_payment(self, request, pk=None):
        """Confirm a payment intent: debit wallet, move to escrow, or mark succeeded."""
        from .models import PaymentIntent, Wallet, Transaction
        try:
            intent = get_object_or_404(PaymentIntent, id=pk, user=request.user)
            if intent.status not in ['requires_confirmation', 'processing']:
                return Response({'error': 'Intent not in confirmable state'}, status=status.HTTP_400_BAD_REQUEST)

            # Simple PIN/2FA check
            pin = request.data.get('transaction_pin')
            two_fa = request.data.get('two_fa_code')
            if not pin and not two_fa:
                return Response({'error': 'Provide transaction_pin or two_fa_code'}, status=status.HTTP_400_BAD_REQUEST)
            if pin and not request.user.profile.check_transaction_pin(pin):
                return Response({'error': 'Invalid transaction PIN'}, status=status.HTTP_400_BAD_REQUEST)
            if two_fa and not TwoFactorAuthService.verify_2fa_code(transfer=None, code=two_fa):
                return Response({'error': 'Invalid 2FA code'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                if wallet.balance < intent.amount:
                    return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
                # Debit wallet
                wallet.balance -= intent.amount
                wallet.save()
                # Record transaction
                Transaction.objects.create(
                    wallet=wallet,
                    receiver=None,
                    reference=f"TXN-{uuid.uuid4().hex[:8].upper()}",
                    amount=intent.amount,
                    type='debit',
                    channel='payment',
                    description=f"Payment for order {intent.order_id}",
                    status='success',
                    balance_after=wallet.balance,
                    metadata={'payment_intent_id': str(intent.id), 'merchant_id': intent.merchant_id}
                )
                # Mark escrowed for marketplace release
                intent.status = 'succeeded'
                intent.escrowed = True
                intent.save(update_fields=['status', 'escrowed', 'updated_at'])
            return Response(PaymentIntentSerializer(intent).data)
        except Exception as e:
            logger.error(f"Error confirming payment intent: {str(e)}")
            return Response({'error': 'Payment confirmation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Payments: Escrow release
    @action(detail=True, methods=['post'], url_path='escrow-release')
    def escrow_release(self, request, pk=None):
        """Release escrowed funds to merchant (mark for settlement)."""
        from .models import PaymentIntent
        try:
            intent = get_object_or_404(PaymentIntent, id=pk)
            if not intent.escrowed or intent.status != 'succeeded':
                return Response({'error': 'Intent not in escrowed state'}, status=status.HTTP_400_BAD_REQUEST)
            # In production, credit merchant balance; here we just flag metadata
            meta = intent.metadata or {}
            meta['escrow_released_at'] = timezone.now().isoformat()
            intent.metadata = meta
            intent.save(update_fields=['metadata', 'updated_at'])
            return Response({'status': 'released', 'intent_id': str(intent.id)})
        except Exception as e:
            logger.error(f"Error releasing escrow: {str(e)}")
            return Response({'error': 'Escrow release failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Payouts for merchants
    @action(detail=False, methods=['post'], url_path='payouts')
    def create_payout(self, request):
        """Create a payout request to merchant bank account."""
        from .models import PayoutRequest
        try:
            serializer = PayoutRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            payout = serializer.save(status='pending')
            return Response(PayoutRequestSerializer(payout).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating payout: {str(e)}")
            return Response({'error': 'Failed to create payout'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get', 'post'], url_path='night-guard-settings')
    def night_guard_settings(self, request):
        """Get or update the current user's Night Guard settings."""
        from .models import NightGuardSettings
        if request.method.lower() == 'get':
            try:
                settings_obj = NightGuardSettings.objects.get(user=request.user)
            except NightGuardSettings.DoesNotExist:
                return Response({'enabled': False}, status=status.HTTP_200_OK)
            return Response(NightGuardSettingsSerializer(settings_obj).data)
        else:
            try:
                settings_obj, _ = NightGuardSettings.objects.get_or_create(user=request.user)
                serializer = NightGuardSettingsSerializer(settings_obj, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error updating Night Guard settings: {str(e)}")
                return Response({'error': 'Failed to update settings'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='night-guard-enroll-face')
    def night_guard_enroll_face(self, request):
        """Enroll user's face for Night Guard. Expects raw bytes in 'face_sample' (base64)."""
        try:
            import base64
            b64 = request.data.get('face_sample')
            if not b64:
                return Response({'error': 'face_sample is required (base64).'}, status=status.HTTP_400_BAD_REQUEST)
            face_bytes = base64.b64decode(b64)
            ok = NightGuardService.enroll_face(request.user, face_bytes)
            if not ok:
                return Response({'error': 'Failed to enroll face'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'message': 'Face enrolled for Night Guard'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error enrolling Night Guard face: {str(e)}")
            return Response({'error': 'Enrollment failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'post'], url_path='large-tx-shield-settings')
    def large_tx_shield_settings(self, request):
        """Get or update the current user's Large Transaction Shield settings."""
        from .models import LargeTransactionShieldSettings
        if request.method.lower() == 'get':
            try:
                settings_obj = LargeTransactionShieldSettings.objects.get(user=request.user)
            except LargeTransactionShieldSettings.DoesNotExist:
                return Response({'enabled': False}, status=status.HTTP_200_OK)
            return Response(LargeTransactionShieldSettingsSerializer(settings_obj).data)
        else:
            try:
                settings_obj, _ = LargeTransactionShieldSettings.objects.get_or_create(user=request.user)
                serializer = LargeTransactionShieldSettingsSerializer(settings_obj, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error updating LTS settings: {str(e)}")
                return Response({'error': 'Failed to update settings'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='large-tx-shield-enroll-face')
    def large_tx_shield_enroll_face(self, request):
        """Enroll user's face for Large Transaction Shield. Expects 'face_sample' (base64)."""
        try:
            import base64
            b64 = request.data.get('face_sample')
            if not b64:
                return Response({'error': 'face_sample is required (base64).'}, status=status.HTTP_400_BAD_REQUEST)
            face_bytes = base64.b64decode(b64)
            ok = LargeTransactionShieldService.enroll_face(request.user, face_bytes)
            if not ok:
                return Response({'error': 'Failed to enroll face'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'message': 'Face enrolled for Large Transaction Shield'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error enrolling LTS face: {str(e)}")
            return Response({'error': 'Enrollment failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='night-guard-deactivate')
    def night_guard_deactivate(self, request):
        """Deactivate Night Guard; requires face_sample (base64) or two_fa_token."""
        from .models import NightGuardSettings
        try:
            import base64
            # Basic throttle simulation: deny if too many attempts in a short window
            from django.core.cache import cache
            cache_key = f"ng_deactivate:{request.user.id}:{get_client_ip(request)}"
            attempts = cache.get(cache_key, 0)
            if attempts >= 5:
                return Response({'error': 'Too many attempts. Try later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            # Try face verification first
            b64 = request.data.get('face_sample')
            token = request.data.get('two_fa_token')
            token_type = request.data.get('token_type', 'sms')

            verified = False
            if b64:
                face_bytes = base64.b64decode(b64)
                verified = NightGuardService.verify_face(request.user, face_bytes)
            elif token:
                verified = Security2FAService.verify_token(request.user, token, token_type)

            if not verified:
                cache.set(cache_key, attempts + 1, timeout=900)
                return Response({'error': 'Verification failed'}, status=status.HTTP_400_BAD_REQUEST)

            settings_obj, _ = NightGuardSettings.objects.get_or_create(user=request.user)
            settings_obj.enabled = False
            settings_obj.save(update_fields=['enabled', 'updated_at'])
            cache.delete(cache_key)
            return Response({'message': 'Night Guard deactivated'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error deactivating Night Guard: {str(e)}")
            return Response({'error': 'Deactivation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='large-tx-shield-deactivate')
    def large_tx_shield_deactivate(self, request):
        """Deactivate Large Transaction Shield; requires face_sample (base64) or two_fa_token."""
        from .models import LargeTransactionShieldSettings
        try:
            import base64
            from django.core.cache import cache
            cache_key = f"lts_deactivate:{request.user.id}:{get_client_ip(request)}"
            attempts = cache.get(cache_key, 0)
            if attempts >= 5:
                return Response({'error': 'Too many attempts. Try later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            b64 = request.data.get('face_sample')
            token = request.data.get('two_fa_token')
            token_type = request.data.get('token_type', 'sms')

            verified = False
            if b64:
                face_bytes = base64.b64decode(b64)
                verified = LargeTransactionShieldService.verify_face(request.user, face_bytes)
            elif token:
                verified = Security2FAService.verify_token(request.user, token, token_type)

            if not verified:
                cache.set(cache_key, attempts + 1, timeout=900)
                return Response({'error': 'Verification failed'}, status=status.HTTP_400_BAD_REQUEST)

            settings_obj, _ = LargeTransactionShieldSettings.objects.get_or_create(user=request.user)
            settings_obj.enabled = False
            settings_obj.save(update_fields=['enabled', 'updated_at'])
            cache.delete(cache_key)
            return Response({'message': 'Large Transaction Shield deactivated'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error deactivating Large Transaction Shield: {str(e)}")
            return Response({'error': 'Deactivation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify-large-tx-shield-face')
    def verify_large_tx_shield_face(self, request, pk=None):
        """Verify face for Large Transaction Shield on a transfer."""
        try:
            import base64
            transfer = self.get_object()
            # Challenge validation
            challenge = request.data.get('challenge')
            from .security_services import FaceChallengeService
            if challenge and not FaceChallengeService.validate(transfer, 'large_tx_shield', challenge):
                return Response({'error': 'Invalid or expired challenge'}, status=status.HTTP_400_BAD_REQUEST)
            result = LargeTransactionShieldService.apply_shield(transfer)
            if not result.get('required'):
                return Response({'message': 'Large Transaction Shield not required.'}, status=status.HTTP_200_OK)

            b64 = request.data.get('face_sample')
            if not b64:
                return Response({'error': 'face_sample is required (base64).'}, status=status.HTTP_400_BAD_REQUEST)
            face_bytes = base64.b64decode(b64)
            if not LargeTransactionShieldService.verify_face(request.user, face_bytes):
                metadata = transfer.metadata or {}
                metadata['large_tx_shield_status'] = 'face_failed'
                transfer.metadata = metadata
                transfer.save(update_fields=['metadata', 'updated_at'])
                return Response({'error': 'Face verification failed'}, status=status.HTTP_400_BAD_REQUEST)

            metadata = transfer.metadata or {}
            metadata['large_tx_shield_status'] = 'face_passed'
            transfer.metadata = metadata
            transfer.save(update_fields=['metadata', 'updated_at'])
            return Response({'message': 'Large Transaction Shield face verification recorded.'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error verifying LTS face: {str(e)}")
            return Response({'error': 'Failed to record face verification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify-large-tx-shield-fallback')
    def verify_large_tx_shield_fallback(self, request, pk=None):
        """Fallback verification for Large Transaction Shield: 2FA or PIN."""
        try:
            transfer = self.get_object()
            result = LargeTransactionShieldService.apply_shield(transfer)
            if not result.get('required'):
                return Response({'message': 'Large Transaction Shield not required.'}, status=status.HTTP_200_OK)

            two_fa_code = request.data.get('two_fa_code')
            tx_pin = request.data.get('transaction_pin')
            if two_fa_code:
                is_valid = TwoFactorAuthService.verify_2fa_code(transfer=transfer, code=two_fa_code)
                if not is_valid:
                    return Response({'error': 'Invalid or expired 2FA code'}, status=status.HTTP_400_BAD_REQUEST)
                transfer.two_fa_verified = True
                transfer.save(update_fields=['two_fa_verified', 'updated_at'])
            elif tx_pin:
                if not request.user.profile.check_transaction_pin(tx_pin):
                    return Response({'error': 'Invalid transaction PIN'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'Provide two_fa_code or transaction_pin'}, status=status.HTTP_400_BAD_REQUEST)

            metadata = transfer.metadata or {}
            metadata['large_tx_shield_status'] = 'fallback_passed'
            transfer.metadata = metadata
            transfer.save(update_fields=['metadata', 'updated_at'])
            return Response({'message': 'Large Transaction Shield fallback verification recorded.'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error verifying LTS fallback: {str(e)}")
            return Response({'error': 'Failed to record fallback verification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='search-banks-by-account')
    def search_banks_by_account(self, request):
        """
        Search for banks that have a specific account number.
        This allows frontend to show bank options when user enters account number.
        """
        account_number = request.query_params.get('account_number', '').strip()
        
        if not account_number:
            return Response({
                'error': 'Account number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate account number format (basic validation)
        if not account_number.isdigit() or len(account_number) < 10:
            return Response({
                'error': 'Invalid account number format. Must be at least 10 digits.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Use the service to search for banks
            matching_banks = BankAccountService.search_banks_by_account_number(account_number)
            
            # If no banks found, return empty list
            if not matching_banks:
                return Response({
                    'message': 'No banks found for this account number',
                    'account_number': account_number,
                    'banks': []
                }, status=status.HTTP_200_OK)
            
            return Response({
                'message': f'Found {len(matching_banks)} banks for account number {account_number}',
                'account_number': account_number,
                'banks': matching_banks
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error searching banks by account number: {str(e)}")
            return Response({
                'error': 'Failed to search banks. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='validate-transfer')
    def validate_transfer(self, request):
        """
        Validate a transfer request before creating it.
        This allows frontend to validate transfer details before submission.
        """
        try:
            amount = request.data.get('amount')
            recipient_account = request.data.get('account_number', '').strip()
            recipient_bank_code = request.data.get('bank_code', '').strip()
            
            if not all([amount, recipient_account, recipient_bank_code]):
                return Response({
                    'error': 'Amount, account number, and bank code are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate amount
            try:
                amount = float(amount)
                if amount <= 0:
                    return Response({
                        'error': 'Amount must be greater than 0'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid amount format'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate account number
            if not recipient_account.isdigit() or len(recipient_account) < 10:
                return Response({
                    'error': 'Invalid account number format'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use the service to validate the transfer
            validation_result = TransferValidationService.validate_transfer_request(
                user=request.user,
                amount=amount,
                recipient_account=recipient_account,
                recipient_bank_code=recipient_bank_code
            )
            
            if validation_result['is_valid']:
                return Response({
                    'is_valid': True,
                    'message': 'Transfer validation successful',
                    'recipient_name': validation_result['recipient_name'],
                    'bank_name': validation_result['bank_name'],
                    'verification_method': validation_result['verification_method']
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'is_valid': False,
                    'error': validation_result['error'],
                    'details': validation_result
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error validating transfer: {str(e)}")
            return Response({
                'error': 'Validation failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify-2fa')
    def verify_2fa(self, request, pk=None):
        """
        Verify 2FA code for a transfer that requires 2FA.
        """
        try:
            transfer = self.get_object()
            two_fa_code = request.data.get('two_fa_code')
            
            if not two_fa_code:
                return Response({
                    'error': '2FA code is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify 2FA code
            is_valid = TwoFactorAuthService.verify_2fa_code(
                transfer=transfer,
                code=two_fa_code
            )
            
            if is_valid:
                # Mark 2FA as verified and process the transfer
                transfer.two_fa_verified = True
                transfer.save()
                
                # Process the transfer (signal will handle the actual processing)
                logger.info(f"2FA verified for transfer {transfer.id}. Processing transfer.")
                
                return Response({
                    'message': '2FA verification successful. Transfer is being processed.',
                    'transfer_id': str(transfer.id),
                    'status': transfer.status
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid or expired 2FA code'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except BankTransfer.DoesNotExist:
            return Response({
                'error': 'Transfer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error verifying 2FA: {str(e)}")
            return Response({
                'error': '2FA verification failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify-night-guard-face')
    def verify_night_guard_face(self, request, pk=None):
        """Verify face sample against enrolled Night Guard template and mark success."""
        try:
            import base64
            transfer = self.get_object()
            # Challenge validation
            challenge = request.data.get('challenge')
            from .security_services import FaceChallengeService
            if challenge and not FaceChallengeService.validate(transfer, 'night_guard', challenge):
                return Response({'error': 'Invalid or expired challenge'}, status=status.HTTP_400_BAD_REQUEST)
            result = NightGuardService.apply_night_guard(transfer)
            if not result.get('required'):
                return Response({'message': 'Night Guard not required for this transfer.'}, status=status.HTTP_200_OK)

            b64 = request.data.get('face_sample')
            if not b64:
                return Response({'error': 'face_sample is required (base64).'}, status=status.HTTP_400_BAD_REQUEST)
            face_bytes = base64.b64decode(b64)
            if not NightGuardService.verify_face(request.user, face_bytes):
                NightGuardService.mark_face_failed(transfer)
                return Response({'error': 'Face verification failed'}, status=status.HTTP_400_BAD_REQUEST)

            metadata = transfer.metadata or {}
            metadata['night_guard_status'] = 'face_passed'
            transfer.metadata = metadata
            transfer.save(update_fields=['metadata', 'updated_at'])

            return Response({'message': 'Face verification recorded.'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error verifying Night Guard face: {str(e)}")
            return Response({'error': 'Failed to record face verification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'post'], url_path='location-guard-settings')
    def location_guard_settings(self, request):
        """Get or update Location Guard settings (allowed states up to 6)."""
        from .models import LocationGuardSettings
        if request.method.lower() == 'get':
            try:
                settings_obj = LocationGuardSettings.objects.get(user=request.user)
            except LocationGuardSettings.DoesNotExist:
                return Response({'enabled': False, 'allowed_states': []}, status=status.HTTP_200_OK)
            return Response(LocationGuardSettingsSerializer(settings_obj).data)
        else:
            try:
                settings_obj, _ = LocationGuardSettings.objects.get_or_create(user=request.user)
                data = request.data.copy()
                states = data.get('allowed_states', [])
                if isinstance(states, str):
                    # allow comma-separated
                    states = [s.strip() for s in states.split(',') if s.strip()]
                if len(states) > 6:
                    return Response({'error': 'Maximum 6 states allowed'}, status=status.HTTP_400_BAD_REQUEST)
                data['allowed_states'] = states
                serializer = LocationGuardSettingsSerializer(settings_obj, data=data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error updating Location Guard settings: {str(e)}")
                return Response({'error': 'Failed to update settings'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='location-guard-enroll-face')
    def location_guard_enroll_face(self, request):
        """Enroll user's face for Location Guard. Expects 'face_sample' (base64)."""
        try:
            import base64
            b64 = request.data.get('face_sample')
            if not b64:
                return Response({'error': 'face_sample is required (base64).'}, status=status.HTTP_400_BAD_REQUEST)
            face_bytes = base64.b64decode(b64)
            ok = LocationGuardService.enroll_face(request.user, face_bytes)
            if not ok:
                return Response({'error': 'Failed to enroll face'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'message': 'Face enrolled for Location Guard'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error enrolling Location Guard face: {str(e)}")
            return Response({'error': 'Enrollment failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify-location-guard-face')
    def verify_location_guard_face(self, request, pk=None):
        """Verify face for Location Guard on a transfer."""
        try:
            import base64
            transfer = self.get_object()
            # Challenge validation
            challenge = request.data.get('challenge')
            from .security_services import FaceChallengeService
            if challenge and not FaceChallengeService.validate(transfer, 'location_guard', challenge):
                return Response({'error': 'Invalid or expired challenge'}, status=status.HTTP_400_BAD_REQUEST)
            result = LocationGuardService.apply_guard(transfer)
            if not result.get('required'):
                return Response({'message': 'Location Guard not required.'}, status=status.HTTP_200_OK)

            b64 = request.data.get('face_sample')
            if not b64:
                return Response({'error': 'face_sample is required (base64).'}, status=status.HTTP_400_BAD_REQUEST)
            face_bytes = base64.b64decode(b64)
            if not LocationGuardService.verify_face(request.user, face_bytes):
                metadata = transfer.metadata or {}
                metadata['location_guard_status'] = 'face_failed'
                transfer.metadata = metadata
                transfer.save(update_fields=['metadata', 'updated_at'])
                return Response({'error': 'Face verification failed'}, status=status.HTTP_400_BAD_REQUEST)

            metadata = transfer.metadata or {}
            metadata['location_guard_status'] = 'face_passed'
            transfer.metadata = metadata
            transfer.save(update_fields=['metadata', 'updated_at'])
            return Response({'message': 'Location Guard face verification recorded.'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error verifying Location Guard face: {str(e)}")
            return Response({'error': 'Failed to record face verification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify-location-guard-fallback')
    def verify_location_guard_fallback(self, request, pk=None):
        """Fallback verification for Location Guard: 2FA or PIN."""
        try:
            transfer = self.get_object()
            result = LocationGuardService.apply_guard(transfer)
            if not result.get('required'):
                return Response({'message': 'Location Guard not required.'}, status=status.HTTP_200_OK)

            two_fa_code = request.data.get('two_fa_code')
            tx_pin = request.data.get('transaction_pin')
            if two_fa_code:
                is_valid = TwoFactorAuthService.verify_2fa_code(transfer=transfer, code=two_fa_code)
                if not is_valid:
                    return Response({'error': 'Invalid or expired 2FA code'}, status=status.HTTP_400_BAD_REQUEST)
                transfer.two_fa_verified = True
                transfer.save(update_fields=['two_fa_verified', 'updated_at'])
            elif tx_pin:
                if not request.user.profile.check_transaction_pin(tx_pin):
                    return Response({'error': 'Invalid transaction PIN'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'Provide two_fa_code or transaction_pin'}, status=status.HTTP_400_BAD_REQUEST)

            metadata = transfer.metadata or {}
            metadata['location_guard_status'] = 'fallback_passed'
            transfer.metadata = metadata
            transfer.save(update_fields=['metadata', 'updated_at'])
            return Response({'message': 'Location Guard fallback verification recorded.'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error verifying Location Guard fallback: {str(e)}")
            return Response({'error': 'Failed to record fallback verification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify-night-guard-fallback')
    def verify_night_guard_fallback(self, request, pk=None):
        """Record successful fallback verification (e.g., 2FA/PIN) for Night Guard window."""
        try:
            transfer = self.get_object()
            result = NightGuardService.apply_night_guard(transfer)
            if not result.get('required'):
                return Response({'message': 'Night Guard not required for this transfer.'}, status=status.HTTP_200_OK)

            # Validate fallback: prefer 2FA, else allow PIN
            two_fa_code = request.data.get('two_fa_code')
            tx_pin = request.data.get('transaction_pin')

            if two_fa_code:
                is_valid = TwoFactorAuthService.verify_2fa_code(transfer=transfer, code=two_fa_code)
                if not is_valid:
                    return Response({'error': 'Invalid or expired 2FA code'}, status=status.HTTP_400_BAD_REQUEST)
                transfer.two_fa_verified = True
                transfer.save(update_fields=['two_fa_verified', 'updated_at'])
            elif tx_pin:
                if not request.user.profile.check_transaction_pin(tx_pin):
                    return Response({'error': 'Invalid transaction PIN'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'Provide two_fa_code or transaction_pin'}, status=status.HTTP_400_BAD_REQUEST)

            metadata = transfer.metadata or {}
            metadata['night_guard_status'] = 'fallback_passed'
            transfer.metadata = metadata
            transfer.save(update_fields=['metadata', 'updated_at'])

            return Response({'message': 'Fallback verification recorded.'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error marking Night Guard fallback verification: {str(e)}")
            return Response({'error': 'Failed to record fallback verification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='fraud-analysis')
    def fraud_analysis(self, request):
        """
        Get fraud analysis for the current user's recent transfers.
        """
        try:
            # Get user's recent transfers
            recent_transfers = BankTransfer.objects.filter(
                user=request.user
            ).order_by('-created_at')[:10]
            
            fraud_analysis = []
            for transfer in recent_transfers:
                analysis = {
                    'transfer_id': str(transfer.id),
                    'amount': str(transfer.amount),
                    'fraud_score': transfer.fraud_score,
                    'is_suspicious': transfer.is_suspicious,
                    'fraud_flags': transfer.fraud_flags,
                    'created_at': transfer.created_at.isoformat(),
                    'status': transfer.status
                }
                fraud_analysis.append(analysis)
            
            return Response({
                'fraud_analysis': fraud_analysis,
                'total_transfers': len(fraud_analysis)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting fraud analysis: {str(e)}")
            return Response({
                'error': 'Failed to get fraud analysis'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='bulk-transfer')
    def bulk_transfer(self, request):
        """
        Create multiple transfers in a single request.
        """
        try:
            transfers_data = request.data.get('transfers', [])
            
            if not transfers_data or len(transfers_data) == 0:
                return Response({
                    'error': 'No transfers provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if len(transfers_data) > 50:  # Limit to 50 transfers per bulk request
                return Response({
                    'error': 'Maximum 50 transfers allowed per bulk request'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate bulk transfer ID
            bulk_transfer_id = str(uuid.uuid4())
            
            created_transfers = []
            failed_transfers = []
            
            with transaction.atomic():
                for index, transfer_data in enumerate(transfers_data):
                    try:
                        # Validate each transfer
                        serializer = self.get_serializer(data=transfer_data)
                        if serializer.is_valid():
                            # Create transfer with bulk metadata
                            transfer = serializer.save(
                                user=request.user,
                                is_bulk=True,
                                bulk_transfer_id=bulk_transfer_id,
                                bulk_index=index,
                                metadata={
                                    **transfer_data.get('metadata', {}),
                                    'bulk_transfer_id': bulk_transfer_id,
                                    'bulk_index': index
                                }
                            )
                            created_transfers.append({
                                'index': index,
                                'transfer_id': str(transfer.id),
                                'status': transfer.status
                            })
                        else:
                            failed_transfers.append({
                                'index': index,
                                'errors': serializer.errors
                            })
                    except Exception as e:
                        failed_transfers.append({
                            'index': index,
                            'error': str(e)
                        })
            
            return Response({
                'bulk_transfer_id': bulk_transfer_id,
                'total_transfers': len(transfers_data),
                'created_transfers': created_transfers,
                'failed_transfers': failed_transfers,
                'success_count': len(created_transfers),
                'failure_count': len(failed_transfers)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error creating bulk transfers: {str(e)}")
            return Response({
                'error': 'Bulk transfer creation failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='transfer-limits')
    def transfer_limits(self, request):
        """
        Get current user's transfer limits based on KYC level.
        """
        try:
            kyc_profile = KYCProfile.objects.get(user=request.user)
            
            limits = {
                'daily_transaction_limit': kyc_profile.get_daily_transaction_limit(),
                'max_balance_limit': kyc_profile.get_max_balance_limit(),
                'kyc_level': kyc_profile.kyc_level,
                'is_approved': kyc_profile.is_approved
            }
            
            return Response(limits, status=status.HTTP_200_OK)
            
        except KYCProfile.DoesNotExist:
            return Response({
                'error': 'KYC profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting transfer limits: {str(e)}")
            return Response({
                'error': 'Failed to get transfer limits'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def perform_create(self, serializer):
        """Create bank transfer with enhanced security, fraud detection, and idempotency."""
        try:
            # Generate idempotency key to prevent duplicate transfers
            idempotency_key = IdempotencyService.generate_idempotency_key(
                user_id=self.request.user.id,
                data=self.request.data
            )
            
            # Check for existing transfer with same idempotency key
            existing_transfer = BankTransfer.objects.filter(idempotency_key=idempotency_key).first()
            if existing_transfer:
                logger.info(f"Duplicate transfer request detected with idempotency key: {idempotency_key}")
                raise serializers.ValidationError({
                    'message': 'Transfer already processed',
                    'transfer_id': str(existing_transfer.id),
                    'status': existing_transfer.status,
                    'error_code': 'DUPLICATE_TRANSFER'
                })

            wallet = Wallet.objects.get(user=self.request.user)
            amount = float(self.request.data.get('amount', 0))
            recipient_bank_code = self.request.data.get('bank_code')
            description = self.request.data.get('description', '')

            # Generate device fingerprint for security
            device_fingerprint = DeviceFingerprintService.generate_device_fingerprint(self.request)
            ip_address = get_client_ip(self.request)
            user_agent = get_user_agent(self.request)

            # Determine sender's bank code (if available)
            sender_bank_code = None
            if hasattr(wallet.user, 'profile') and hasattr(wallet.user.profile, 'bank_name'):
                sender_bank = Bank.objects.filter(name=wallet.user.profile.bank_name).first()
                if sender_bank:
                    sender_bank_code = sender_bank.code

            # Check if recipient is internal (check both account numbers)
            receiver_wallet = None
            transfer_type = TransferType.INTERNAL
            
            # First try primary account number
            try:
                receiver_wallet = Wallet.objects.get(account_number=serializer.validated_data['account_number'])
                # Check if user is trying to transfer to their own account
                if receiver_wallet.user == self.request.user:
                    raise serializers.ValidationError('You cannot transfer money to your own account.')
                transfer_type = TransferType.INTERNAL
            except Wallet.DoesNotExist:
                # If not found, try alternative account number
                try:
                    receiver_wallet = Wallet.objects.get(alternative_account_number=serializer.validated_data['account_number'])
                    # Check if user is trying to transfer to their own account
                    if receiver_wallet.user == self.request.user:
                        raise serializers.ValidationError('You cannot transfer money to your own account.')
                    transfer_type = TransferType.INTERNAL
                except Wallet.DoesNotExist:
                    # External transfer - Also check if it's user's own account number in external bank
                    if serializer.validated_data['account_number'] == wallet.account_number or \
                       serializer.validated_data['account_number'] == wallet.alternative_account_number:
                        raise serializers.ValidationError('You cannot transfer money to your own account.')

            # Calculate fees and total deduction
            fee, vat, levy = calculate_transfer_fees(amount, transfer_type=transfer_type)
            total_deduction = amount + float(fee)  # Only deduct amount + fee from sender
            
            # EARLY BALANCE VALIDATION - Check balance before any processing
            if wallet.balance < total_deduction:
                logger.warning(f"Insufficient balance for user {self.request.user.username}. "
                             f"Required: {total_deduction}, Available: {wallet.balance}")
                
                # Return clean error response without creating any database records
                return Response({
                    'error': 'Insufficient balance',
                    'error_code': 'INSUFFICIENT_FUNDS',
                    'message': f'Insufficient balance for transfer including fees. Required: ₦{total_deduction:,.2f}, Available: ₦{wallet.balance:,.2f}',
                    'required_amount': total_deduction,
                    'available_balance': float(wallet.balance.amount) if hasattr(wallet.balance, 'amount') else float(wallet.balance),
                    'shortfall': total_deduction - float(wallet.balance.amount) if hasattr(wallet.balance, 'amount') else total_deduction - float(wallet.balance),
                    'transfer_amount': amount,
                    'fee': float(fee),
                    'vat': float(vat),
                    'levy': float(levy),
                    'technical_details': {
                        'user_id': self.request.user.id,
                        'wallet_account': wallet.account_number,
                        'total_deduction': total_deduction,
                        'available_balance': float(wallet.balance.amount) if hasattr(wallet.balance, 'amount') else float(wallet.balance),
                        'shortfall': total_deduction - float(wallet.balance.amount) if hasattr(wallet.balance, 'amount') else total_deduction - float(wallet.balance)
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check KYC level transaction limits
            try:
                kyc_profile = KYCProfile.objects.get(user=self.request.user)
                can_transact, message = kyc_profile.can_transact_amount(amount)
                if not can_transact:
                    # Return clean error response without creating any database records
                    return Response({
                        'error': 'Transaction limit exceeded',
                        'error_code': 'LIMIT_EXCEEDED',
                        'message': message,
                        'transfer_amount': amount,
                        'kyc_level': kyc_profile.kyc_level,
                        'technical_details': {
                            'user_id': self.request.user.id,
                            'kyc_level': kyc_profile.kyc_level,
                            'transfer_amount': amount,
                            'limit_details': message
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)
            except KYCProfile.DoesNotExist:
                # Return clean error response without creating any database records
                return Response({
                    'error': 'KYC verification required',
                    'error_code': 'KYC_REQUIRED',
                    'message': 'KYC profile not found. Complete KYC verification first.',
                    'transfer_amount': amount,
                    'technical_details': {
                        'user_id': self.request.user.id,
                        'kyc_status': 'not_found',
                        'transfer_amount': amount
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate transaction PIN
            pin = self.request.data.get('transaction_pin')
            if not pin or not self.request.user.profile.check_transaction_pin(pin):
                # Return clean error response without creating any database records
                return Response({
                    'error': 'Invalid transaction PIN',
                    'error_code': 'INVALID_PIN',
                    'message': 'Invalid or missing transaction PIN.',
                    'transfer_amount': amount,
                    'technical_details': {
                        'user_id': self.request.user.id,
                        'pin_provided': bool(pin),
                        'pin_length': len(pin) if pin else 0,
                        'transfer_amount': amount
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            # Fraud detection and risk assessment
            fraud_score = FraudDetectionService.calculate_fraud_score(
                user=self.request.user,
                amount=amount,
                recipient_account=serializer.validated_data['account_number'],
                recipient_bank_code=recipient_bank_code,
                device_fingerprint=device_fingerprint,
                ip_address=ip_address
            )
            
            # Determine if 2FA is required
            requires_2fa = FraudDetectionService.should_require_2fa(
                user=self.request.user,
                amount=amount,
                fraud_score=fraud_score
            )
            
            # Determine if staff approval is required
            requires_approval = FraudDetectionService.should_require_approval(
                user=self.request.user,
                amount=amount,
                fraud_score=fraud_score
            )

            # If 2FA is required, generate and send code
            two_fa_code = None
            two_fa_expires_at = None
            if requires_2fa:
                two_fa_code = TwoFactorAuthService.generate_2fa_code()
                two_fa_expires_at = timezone.now() + timezone.timedelta(minutes=10)
                
                # Send 2FA code via SMS/Email
                TwoFactorAuthService.send_2fa_code(
                    user=self.request.user,
                    code=two_fa_code,
                    transfer_amount=amount,
                    recipient_account=serializer.validated_data['account_number']
                )

            # Create the transfer with enhanced fields
            transfer_data = {
                'user': self.request.user,
                'fee': fee,
                'vat': vat,
                'levy': levy,
                'bank_code': recipient_bank_code,
                'transfer_type': transfer_type,
                'description': description,
                'status': TransferStatus.PENDING,
                'idempotency_key': idempotency_key,
                'device_fingerprint': device_fingerprint,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'fraud_score': fraud_score,
                'requires_2fa': requires_2fa,
                'two_fa_code': two_fa_code,
                'two_fa_expires_at': two_fa_expires_at,
                'is_suspicious': fraud_score > 70,  # Flag as suspicious if fraud score > 70
                'metadata': {
                    'created_via': 'api',
                    'user_agent': user_agent,
                    'ip_address': ip_address,
                    'device_fingerprint': device_fingerprint,
                    'fraud_detection': {
                        'score': fraud_score,
                        'requires_2fa': requires_2fa,
                        'requires_approval': requires_approval,
                        'flags': FraudDetectionService._get_fraud_flags(
                            user=self.request.user,
                            amount=amount,
                            recipient_account=serializer.validated_data['account_number']
                        )
                    }
                }
            }

            # Strict Location Guard: require state when feature enabled
            try:
                from .models import LocationGuardSettings
                lg_settings = LocationGuardSettings.objects.filter(user=self.request.user, enabled=True).first()
                if lg_settings and transfer_data.get('metadata', {}).get('created_via') == 'api':
                    # we expect location_data in request
                    location_data = self.request.data.get('location_data') or {}
                    if isinstance(location_data, str):
                        import json as _json
                        try:
                            location_data = _json.loads(location_data)
                        except Exception:
                            location_data = {}
                    state = (location_data.get('state') or '').strip()
                    if not state:
                        return Response({
                            'error': 'Location required',
                            'error_code': 'LOCATION_REQUIRED',
                            'message': 'Location Guard is enabled. Provide location_data.state for app transfers.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    # attach to transfer
                    transfer_data['location_data'] = location_data
            except Exception:
                pass

            # Use atomic transaction for data consistency
            with transaction.atomic():
                transfer = serializer.save(**transfer_data)

                # If staff approval is required, create approval request
                if requires_approval:
                    transfer.mark_as_pending('Transfer requires staff approval due to amount or risk factors.')
                    TransactionApproval.objects.create(
                        transaction=transfer,
                        requested_by=self.request.user,
                        reason=f'High-value transfer ({amount}) or suspicious activity (fraud score: {fraud_score})',
                        amount=amount,
                        status='pending'
                    )
                    logger.info(f"Transfer {transfer.id} requires staff approval. Fraud score: {fraud_score}")

                # Create transaction charge record
                TransactionCharge.objects.create(
                    transfer=transfer,
                    vat_amount=vat,
                    vat_rate=get_active_vat_rate(),
                    charge_status='calculated'
                )

                # Log audit event with enhanced details
                log_audit_event(
                    user=self.request.user,
                    action='bank_transfer_created',
                    description=f'Bank transfer created: {transfer.amount} to {transfer.bank_name} - Status: {transfer.status} - Fraud Score: {fraud_score}',
                    severity='medium' if fraud_score < 50 else 'high',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    content_object=transfer,
                    extra_data={
                        'fraud_score': fraud_score,
                        'requires_2fa': requires_2fa,
                        'requires_approval': requires_approval,
                        'device_fingerprint': device_fingerprint
                    }
                )

                logger.info(f"Transfer {transfer.id} created successfully. Fraud score: {fraud_score}, 2FA required: {requires_2fa}")

        except Wallet.DoesNotExist:
            logger.error(f"Wallet not found for user {self.request.user.id}")
            raise serializers.ValidationError({
                'error': 'Wallet not found',
                'error_code': 'WALLET_NOT_FOUND',
                'message': 'Wallet not found. Complete KYC verification first.',
                'technical_details': {
                    'user_id': self.request.user.id,
                    'error_type': 'Wallet.DoesNotExist'
                }
            })
        except Exception as e:
            logger.error(f"Error creating bank transfer: {str(e)}")
            raise serializers.ValidationError({
                'error': 'Transfer creation failed',
                'error_code': 'PROCESSING_ERROR',
                'message': f'Transfer creation failed: {str(e)}',
                'technical_details': {
                    'user_id': self.request.user.id,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'amount': amount if 'amount' in locals() else None,
                    'account_number': serializer.validated_data.get('account_number') if 'serializer' in locals() else None
                }
            })


class BillPaymentViewSet(ModelViewSet):
    """ViewSet for Bill Payment operations."""
    permission_classes = [IsAuthenticated]
    serializer_class = BillPaymentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'service_type', 'timestamp']
    search_fields = ['customer_id', 'reference', 'description']
    ordering_fields = ['amount', 'timestamp']
    ordering = ['-timestamp']

    def get_queryset(self):
        """Return bill payments based on user permissions."""
        if self.request.user.is_staff:
            return BillPayment.objects.all()
        return BillPayment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create bill payment with balance and KYC level validation."""
        try:
            wallet = Wallet.objects.get(user=self.request.user)
            
            # Check if user has sufficient balance
            amount = float(self.request.data.get('amount', 0))
            if wallet.balance < amount:
                raise serializers.ValidationError('Insufficient balance for payment.')
            
            # Check KYC level transaction limits
            try:
                kyc_profile = KYCProfile.objects.get(user=self.request.user)
                can_transact, message = kyc_profile.can_transact_amount(amount)
                if not can_transact:
                    raise serializers.ValidationError(message)
            except KYCProfile.DoesNotExist:
                raise serializers.ValidationError('KYC profile not found. Complete KYC verification first.')
            
            pin = self.request.data.get('transaction_pin')
            if not pin or not self.request.user.profile.check_transaction_pin(pin):
                raise serializers.ValidationError('Invalid or missing transaction PIN.')

            payment = serializer.save(user=self.request.user)
            
            # Log audit event
            log_audit_event(
                user=self.request.user,
                action='bill_payment_created',
                description=f'Bill payment created: {payment.amount} for {payment.service_type}',
                severity='medium',
                ip_address=get_client_ip(self.request),
                user_agent=get_user_agent(self.request),
                content_object=payment
            )
            
        except Wallet.DoesNotExist:
            raise serializers.ValidationError('Wallet not found. Complete KYC verification first.')


class BiometricAuthViewSet(ModelViewSet):
    """ViewSet for Biometric Authentication operations."""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='register')
    def register_biometric(self, request):
        """
        Register a new biometric identifier for authentication.
        Supports fingerprint, face, and voice biometrics.
        """
        try:
            biometric_type = request.data.get('type')
            biometric_data = request.data.get('data')
            
            if not biometric_type or not biometric_data:
                return Response({
                    'error': 'Biometric type and data are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Register biometric
            result = BiometricService.register_biometric(
                user=request.user,
                biometric_type=biometric_type,
                biometric_data=biometric_data
            )
            
            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error registering biometric: {str(e)}")
            return Response({
                'error': 'Biometric registration failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='verify')
    def verify_biometric(self, request):
        """
        Verify a biometric against stored template.
        Used for authentication and transaction authorization.
        """
        try:
            biometric_type = request.data.get('type')
            biometric_data = request.data.get('data')
            
            if not biometric_type or not biometric_data:
                return Response({
                    'error': 'Biometric type and data are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify biometric
            result = BiometricService.verify_biometric(
                user=request.user,
                biometric_type=biometric_type,
                biometric_data=biometric_data
            )
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': result['error']
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except Exception as e:
            logger.error(f"Error verifying biometric: {str(e)}")
            return Response({
                'error': 'Biometric verification failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='registered')
    def get_registered_biometrics(self, request):
        """
        Get list of registered biometrics for the current user.
        """
        try:
            result = BiometricService.get_registered_biometrics(request.user)
            return Response(result, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Error getting registered biometrics: {str(e)}")
            return Response({
                'error': 'Failed to get registered biometrics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Additional utility views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_status(request):
    """Get comprehensive user status including verification and KYC."""
    user = request.user
    response_data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'is_verified': False,
            'has_kyc': False,
            'kyc_approved': False,
            'has_wallet': False,
        }
    }
    
    # Check user verification
    if hasattr(user, 'profile'):
        response_data['user']['is_verified'] = user.profile.is_verified
        response_data['user']['phone'] = str(user.profile.phone) if user.profile.phone else None
    
    # Check KYC status
    try:
        kyc_profile = KYCProfile.objects.get(user=user)
        response_data['user']['has_kyc'] = True
        response_data['user']['kyc_approved'] = kyc_profile.is_approved
        response_data['kyc_profile'] = KYCProfileDetailSerializer(kyc_profile).data
    except KYCProfile.DoesNotExist:
        pass
    
    # Check wallet status
    try:
        wallet = Wallet.objects.get(user=user)
        response_data['user']['has_wallet'] = True
        response_data['wallet'] = WalletSerializer(wallet).data
    except Wallet.DoesNotExist:
        pass
    
    return Response(response_data)


class BankViewSet(ReadOnlyModelViewSet):
    """ViewSet for Bank operations (read-only)."""
    permission_classes = [IsAuthenticated]
    serializer_class = BankSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['code']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'code']
    ordering = ['name']
    queryset = Bank.objects.all()

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search banks by name or code."""
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'detail': 'Query parameter "q" is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        banks = Bank.objects.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        ).order_by('name')[:20]  # Limit to 20 results
        
        serializer = self.get_serializer(banks, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_pdf_statement(request):
    """
    Download a PDF statement for the authenticated user.
    Query params:
      - date_from (YYYY-MM-DD, required)
      - date_to (YYYY-MM-DD, required)
      - min_amount (optional)
      - max_amount (optional)
      - channel (optional)
      - status (optional)
      - meta_key/meta_value (optional, filter by metadata key/value)
    """
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    channel = request.GET.get('channel')
    status_ = request.GET.get('status')
    meta_key = request.GET.get('meta_key')
    meta_value = request.GET.get('meta_value')
    if not date_from or not date_to:
        return Response({'detail': 'date_from and date_to are required (YYYY-MM-DD).', 'doc': download_pdf_statement.__doc__}, status=status.HTTP_400_BAD_REQUEST)
    try:
        from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
        to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
    except Exception:
        return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.', 'doc': download_pdf_statement.__doc__}, status=status.HTTP_400_BAD_REQUEST)
    try:
        wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        return Response({'detail': 'Wallet not found.'}, status=status.HTTP_404_NOT_FOUND)
    txs = Transaction.objects.filter(wallet=wallet, timestamp__date__gte=from_date, timestamp__date__lte=to_date)
    if min_amount:
        txs = txs.filter(amount__gte=float(min_amount))
    if max_amount:
        txs = txs.filter(amount__lte=float(max_amount))
    if channel:
        txs = txs.filter(channel=channel)
    if status_:
        txs = txs.filter(status=status_)
    if meta_key and meta_value:
        txs = txs.filter(metadata__contains={meta_key: meta_value})
    txs = txs.order_by('timestamp')
    if not txs.exists():
        return Response({'detail': 'No transactions in selected range.'}, status=status.HTTP_404_NOT_FOUND)
    opening_balance = txs.first().balance_after - txs.first().amount if txs.first().balance_after is not None else 0
    closing_balance = txs.last().balance_after if txs.last().balance_after is not None else 0
    total_credits = sum(t.amount for t in txs if t.type == 'credit')
    total_debits = sum(t.amount for t in txs if t.type == 'debit')
    html = render_to_string('bank/statement_pdf.html', {
        'user': request.user,
        'wallet': wallet,
        'transactions': txs,
        'date_from': from_date,
        'date_to': to_date,
        'opening_balance': opening_balance,
        'closing_balance': closing_balance,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'now': timezone.now(),
    })
    try:
        # Try to generate PDF if weasyprint is available
        from weasyprint import HTML
        pdf_file = HTML(string=html).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=statement_{wallet.account_number}_{from_date}_{to_date}.pdf'
        return response
    except ImportError:
        # Fallback if weasyprint is not available
        return Response({
            'detail': 'PDF generation is not available. Please contact support.',
            'html_content': html  # Return HTML content as fallback
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class StaffRoleViewSet(ReadOnlyModelViewSet):
    """ViewSet for Staff Role operations (read-only)."""
    permission_classes = [IsAuthenticated]
    serializer_class = StaffRoleSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['level', 'can_approve_kyc', 'can_manage_staff']
    search_fields = ['name', 'description']
    ordering_fields = ['level', 'name']
    ordering = ['level']
    queryset = StaffRole.objects.all()


class StaffProfileViewSet(ModelViewSet):
    """ViewSet for Staff Profile operations."""
    permission_classes = [IsAuthenticated]
    serializer_class = StaffProfileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['role', 'branch', 'department', 'is_active']
    search_fields = ['user__username', 'user__email', 'employee_id']
    ordering_fields = ['role__level', 'user__username', 'hire_date']
    ordering = ['role__level', 'user__username']

    def get_queryset(self):
        """Return staff profiles based on user permissions."""
        if self.request.user.is_staff:
            return StaffProfile.objects.all()
        # Staff can only see their own profile and subordinates
        try:
            staff_profile = StaffProfile.objects.get(user=self.request.user)
            if staff_profile.can_manage_staff():
                return StaffProfile.objects.filter(
                    Q(id=staff_profile.id) | Q(supervisor=staff_profile)
                )
            return StaffProfile.objects.filter(id=staff_profile.id)
        except StaffProfile.DoesNotExist:
            return StaffProfile.objects.none()

    def perform_create(self, serializer):
        """Create staff profile with permission checks."""
        if not self.request.user.is_staff:
            raise serializers.ValidationError('Only admin users can create staff profiles.')
        serializer.save()

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current user's staff profile."""
        try:
            profile = StaffProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except StaffProfile.DoesNotExist:
            return Response({
                'detail': 'Staff profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def my_subordinates(self, request):
        """Get current user's subordinates."""
        try:
            profile = StaffProfile.objects.get(user=request.user)
            if not profile.can_manage_staff():
                return Response({
                    'detail': 'You do not have permission to view subordinates.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            subordinates = profile.get_subordinates()
            serializer = self.get_serializer(subordinates, many=True)
            return Response(serializer.data)
        except StaffProfile.DoesNotExist:
            return Response({
                'detail': 'Staff profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class TransactionApprovalViewSet(ModelViewSet):
    """ViewSet for Transaction Approval operations."""
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionApprovalSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'requested_by__role']
    search_fields = ['transaction__reference', 'reason']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return approvals based on user permissions."""
        if self.request.user.is_staff:
            return TransactionApproval.objects.all()
        
        try:
            staff_profile = StaffProfile.objects.get(user=self.request.user)
            # Staff can see approvals they requested or are assigned to handle
            return TransactionApproval.objects.filter(
                Q(requested_by=staff_profile) | 
                Q(escalated_to=staff_profile) |
                Q(approved_by=staff_profile)
            )
        except StaffProfile.DoesNotExist:
            return TransactionApproval.objects.none()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a transaction."""
        approval = self.get_object()
        try:
            staff_profile = StaffProfile.objects.get(user=request.user)
            
            # Check if user can approve this transaction
            if not staff_profile.can_approve_transaction(approval.transaction.amount):
                return Response({
                    'detail': 'You do not have permission to approve this transaction amount.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            pin = request.data.get('transaction_pin')
            if not pin or not request.user.profile.check_transaction_pin(pin):
                return Response({'detail': 'Invalid or missing transaction PIN.'}, status=status.HTTP_400_BAD_REQUEST)

            approval.status = 'approved'
            approval.approved_by = staff_profile
            approval.reason = request.data.get('reason', '')
            approval.save()
            
            # Update transaction status
            approval.transaction.status = 'success'
            approval.transaction.save()
            
            # Log activity
            StaffActivity.objects.create(
                staff=staff_profile,
                activity_type='transaction_processed',
                description=f'Approved transaction {approval.transaction.reference}',
                related_object=approval.transaction
            )
            
            serializer = self.get_serializer(approval)
            return Response(serializer.data)
        except StaffProfile.DoesNotExist:
            return Response({
                'detail': 'Staff profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a transaction."""
        approval = self.get_object()
        try:
            staff_profile = StaffProfile.objects.get(user=request.user)
            
            pin = request.data.get('transaction_pin')
            if not pin or not request.user.profile.check_transaction_pin(pin):
                return Response({'detail': 'Invalid or missing transaction PIN.'}, status=status.HTTP_400_BAD_REQUEST)

            approval.status = 'rejected'
            approval.approved_by = staff_profile
            approval.reason = request.data.get('reason', '')
            approval.save()
            
            # Update transaction status
            approval.transaction.status = 'failed'
            approval.transaction.save()
            
            serializer = self.get_serializer(approval)
            return Response(serializer.data)
        except StaffProfile.DoesNotExist:
            return Response({
                'detail': 'Staff profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate a transaction to a higher authority."""
        approval = self.get_object()
        escalated_to_id = request.data.get('escalated_to')
        escalation_reason = request.data.get('escalation_reason', '')
        
        try:
            escalated_to = StaffProfile.objects.get(id=escalated_to_id)
            staff_profile = StaffProfile.objects.get(user=request.user)
            
            pin = request.data.get('transaction_pin')
            if not pin or not request.user.profile.check_transaction_pin(pin):
                return Response({'detail': 'Invalid or missing transaction PIN.'}, status=status.HTTP_400_BAD_REQUEST)

            approval.status = 'escalated'
            approval.escalated_to = escalated_to
            approval.escalation_reason = escalation_reason
            approval.save()
            
            serializer = self.get_serializer(approval)
            return Response(serializer.data)
        except StaffProfile.DoesNotExist:
            return Response({
                'detail': 'Staff profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class CustomerEscalationViewSet(ModelViewSet):
    """ViewSet for Customer Escalation operations."""
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerEscalationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['priority', 'status', 'created_by__role']
    search_fields = ['subject', 'customer__username', 'description']
    ordering_fields = ['priority', 'created_at', 'status']
    ordering = ['-priority', '-created_at']

    def get_queryset(self):
        """Return escalations based on user permissions."""
        if self.request.user.is_staff:
            return CustomerEscalation.objects.all()
        
        try:
            staff_profile = StaffProfile.objects.get(user=self.request.user)
            # Staff can see escalations they created, are assigned to, or can handle
            if staff_profile.role.can_handle_escalations:
                return CustomerEscalation.objects.filter(
                    Q(created_by=staff_profile) | 
                    Q(assigned_to=staff_profile) |
                    Q(assigned_to__isnull=True)
                )
            return CustomerEscalation.objects.filter(
                Q(created_by=staff_profile) | 
                Q(assigned_to=staff_profile)
            )
        except StaffProfile.DoesNotExist:
            return CustomerEscalation.objects.none()

    @action(detail=True, methods=['post'])
    def assign_to_self(self, request, pk=None):
        """Assign escalation to current user."""
        escalation = self.get_object()
        try:
            staff_profile = StaffProfile.objects.get(user=request.user)
            
            escalation.assigned_to = staff_profile
            escalation.status = 'in_progress'
            escalation.save()
            
            # Log activity
            StaffActivity.objects.create(
                staff=staff_profile,
                activity_type='escalation_handled',
                description=f'Assigned escalation: {escalation.subject}',
                related_object=escalation
            )
            
            serializer = self.get_serializer(escalation)
            return Response(serializer.data)
        except StaffProfile.DoesNotExist:
            return Response({
                'detail': 'Staff profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an escalation."""
        escalation = self.get_object()
        resolution = request.data.get('resolution', '')
        
        try:
            staff_profile = StaffProfile.objects.get(user=request.user)
            
            escalation.status = 'resolved'
            escalation.resolution = resolution
            escalation.resolved_at = timezone.now()
            escalation.save()
            
            # Log activity
            StaffActivity.objects.create(
                staff=staff_profile,
                activity_type='escalation_handled',
                description=f'Resolved escalation: {escalation.subject}',
                related_object=escalation
            )
            
            serializer = self.get_serializer(escalation)
            return Response(serializer.data)
        except StaffProfile.DoesNotExist:
            return Response({
                'detail': 'Staff profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class StaffActivityViewSet(ReadOnlyModelViewSet):
    """ViewSet for Staff Activity operations (read-only)."""
    permission_classes = [IsAuthenticated]
    serializer_class = StaffActivitySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['activity_type', 'staff__role']
    search_fields = ['staff__user__username', 'description']
    ordering_fields = ['timestamp', 'activity_type']
    ordering = ['-timestamp']

    def get_queryset(self):
        """Return activities based on user permissions."""
        if self.request.user.is_staff:
            return StaffActivity.objects.all()
        
        try:
            staff_profile = StaffProfile.objects.get(user=self.request.user)
            # Staff can see their own activities and subordinates' activities if they can manage staff
            if staff_profile.can_manage_staff():
                return StaffActivity.objects.filter(
                    Q(staff=staff_profile) | 
                    Q(staff__supervisor=staff_profile)
                )
            return StaffActivity.objects.filter(staff=staff_profile)
        except StaffProfile.DoesNotExist:
            return StaffActivity.objects.none()

    @action(detail=False, methods=['get'])
    def my_activities(self, request):
        """Get current user's activities."""
        try:
            staff_profile = StaffProfile.objects.get(user=request.user)
            activities = StaffActivity.objects.filter(staff=staff_profile)
            serializer = self.get_serializer(activities, many=True)
            return Response(serializer.data)
        except StaffProfile.DoesNotExist:
            return Response({
                'detail': 'Staff profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)


class TransferFeeRuleViewSet(ModelViewSet):
    """ViewSet for Transfer Fee Rule operations."""
    permission_classes = [IsAuthenticated]
    serializer_class = TransferFeeRuleSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['bank_type', 'kyc_level', 'is_active']
    search_fields = ['name']
    ordering_fields = ['priority', 'created_at']
    ordering = ['-priority', '-created_at']

    def get_queryset(self):
        """Return fee rules based on user permissions."""
        if self.request.user.is_staff:
            return TransferFeeRule.objects.all()
        return TransferFeeRule.objects.filter(is_active=True)

    @action(detail=False, methods=['post'], url_path='calculate-fee')
    def calculate_fee(self, request):
        """Calculate fee for a given amount and transfer type."""
        try:
            amount = float(request.data.get('amount', 0))
            transfer_type = request.data.get('transfer_type', 'external')
            kyc_level = request.data.get('kyc_level')
            
            if amount <= 0:
                return Response({
                    'error': 'Amount must be greater than 0'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get applicable fee rules
            applicable_rules = TransferFeeRule.objects.filter(
                is_active=True,
                bank_type__in=['both', transfer_type]
            )
            
            if kyc_level:
                applicable_rules = applicable_rules.filter(
                    kyc_level__in=[kyc_level, None]
                )
            
            # Sort by priority (highest first)
            applicable_rules = applicable_rules.order_by('-priority')
            
            total_fee = Money(0, 'NGN')
            applied_rules = []
            
            for rule in applicable_rules:
                if rule.is_applicable(amount, transfer_type, kyc_level):
                    fee = rule.calculate_fee(amount)
                    total_fee += fee
                    applied_rules.append({
                        'rule_name': rule.name,
                        'fee_percent': rule.fee_percent,
                        'fee_fixed': str(rule.fee_fixed),
                        'calculated_fee': str(fee)
                    })
            
            return Response({
                'amount': amount,
                'transfer_type': transfer_type,
                'kyc_level': kyc_level,
                'total_fee': str(total_fee),
                'applied_rules': applied_rules
            }, status=status.HTTP_200_OK)
            
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid amount format'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error calculating fee: {str(e)}")
            return Response({
                'error': 'Failed to calculate fee'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SavedBeneficiaryViewSet(ModelViewSet):
    """ViewSet for Saved Beneficiary operations."""
    permission_classes = [IsAuthenticated]
    serializer_class = SavedBeneficiarySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['bank_code', 'is_verified', 'is_favorite']
    search_fields = ['name', 'account_number', 'nickname']
    ordering_fields = ['last_used', 'usage_count', 'created_at']
    ordering = ['-is_favorite', '-last_used', '-usage_count']

    def get_queryset(self):
        """Return beneficiaries for the current user."""
        return SavedBeneficiary.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create beneficiary for the current user."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='mark-favorite')
    def mark_favorite(self, request, pk=None):
        """Mark/unmark beneficiary as favorite."""
        beneficiary = self.get_object()
        beneficiary.is_favorite = not beneficiary.is_favorite
        beneficiary.save(update_fields=['is_favorite'])
        
        serializer = self.get_serializer(beneficiary)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='verify')
    def verify_beneficiary(self, request, pk=None):
        """Verify beneficiary account."""
        beneficiary = self.get_object()
        verification_method = request.data.get('verification_method', 'api')
        
        try:
            # Mock verification - in production, call actual verification service
            beneficiary.verify_beneficiary(verification_method)
            serializer = self.get_serializer(beneficiary)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error verifying beneficiary: {str(e)}")
            return Response({
                'error': 'Failed to verify beneficiary'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='favorites')
    def favorites(self, request):
        """Get user's favorite beneficiaries."""
        favorites = SavedBeneficiary.objects.filter(
            user=request.user,
            is_favorite=True
        ).order_by('-last_used')
        
        serializer = self.get_serializer(favorites, many=True)
        return Response(serializer.data)


class TransferReversalViewSet(ModelViewSet):
    """ViewSet for Transfer Reversal operations."""
    permission_classes = [IsAuthenticated]
    serializer_class = TransferReversalSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'reversal_reason']
    search_fields = ['original_transfer__reference']
    ordering_fields = ['created_at', 'processed_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return reversals based on user permissions."""
        if self.request.user.is_staff:
            return TransferReversal.objects.all()
        return TransferReversal.objects.filter(
            initiated_by=self.request.user
        )

    def perform_create(self, serializer):
        """Create reversal for the current user."""
        serializer.save(initiated_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_reversal(self, request, pk=None):
        """Approve a reversal (staff only)."""
        if not request.user.is_staff:
            return Response({
                'error': 'Only staff can approve reversals'
            }, status=status.HTTP_403_FORBIDDEN)
        
        reversal = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            reversal.mark_as_processing()
            # In production, implement actual reversal logic here
            reversal.mark_as_completed(processed_by=request.user)
            
            serializer = self.get_serializer(reversal)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error approving reversal: {str(e)}")
            reversal.mark_as_failed(str(e))
            return Response({
                'error': 'Failed to approve reversal'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject_reversal(self, request, pk=None):
        """Reject a reversal (staff only)."""
        if not request.user.is_staff:
            return Response({
                'error': 'Only staff can reject reversals'
            }, status=status.HTTP_403_FORBIDDEN)
        
        reversal = self.get_object()
        reason = request.data.get('reason', '')
        
        reversal.mark_as_failed(f'Rejected by {request.user.username}: {reason}')
        
        serializer = self.get_serializer(reversal)
        return Response(serializer.data)


class TransferFailureViewSet(ReadOnlyModelViewSet):
    """ViewSet for Transfer Failure operations (read-only for monitoring)."""
    permission_classes = [IsAuthenticated]
    serializer_class = TransferFailureSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['error_code', 'error_category', 'is_resolved', 'user_id']
    search_fields = ['failure_reason', 'recipient_account', 'error_code']
    ordering_fields = ['failed_at', 'error_code', 'transfer_amount']
    ordering = ['-failed_at']

    def get_queryset(self):
        """Return transfer failures based on user permissions."""
        if self.request.user.is_staff:
            return TransferFailure.objects.all()
        # Regular users can only see their own failures
        return TransferFailure.objects.filter(user_id=self.request.user.id)

    @action(detail=False, methods=['get'], url_path='summary')
    def failure_summary(self, request):
        """Get summary statistics of transfer failures."""
        queryset = self.get_queryset()
        
        # Get failure statistics
        total_failures = queryset.count()
        resolved_failures = queryset.filter(is_resolved=True).count()
        unresolved_failures = total_failures - resolved_failures
        
        # Get failure breakdown by error code
        error_code_stats = queryset.values('error_code').annotate(
            count=Count('id'),
            resolved_count=Count('id', filter=Q(is_resolved=True)),
            unresolved_count=Count('id', filter=Q(is_resolved=False))
        ).order_by('-count')
        
        # Get failure breakdown by category
        category_stats = queryset.values('error_category').annotate(
            count=Count('id'),
            resolved_count=Count('id', filter=Q(is_resolved=True)),
            unresolved_count=Count('id', filter=Q(is_resolved=False))
        ).order_by('-count')
        
        # Get recent failures (last 7 days)
        recent_failures = queryset.filter(
            failed_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
        
        return Response({
            'summary': {
                'total_failures': total_failures,
                'resolved_failures': resolved_failures,
                'unresolved_failures': unresolved_failures,
                'resolution_rate': (resolved_failures / total_failures * 100) if total_failures > 0 else 0,
                'recent_failures_7_days': recent_failures
            },
            'error_code_breakdown': list(error_code_stats),
            'category_breakdown': list(category_stats)
        })

    @action(detail=True, methods=['post'], url_path='mark-resolved')
    def mark_resolved(self, request, pk=None):
        """Mark a failure as resolved."""
        failure = self.get_object()
        
        # Only staff can mark failures as resolved
        if not request.user.is_staff:
            return Response({
                'error': 'Permission denied',
                'message': 'Only staff can mark failures as resolved.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        resolution_notes = request.data.get('resolution_notes', '')
        
        failure.mark_resolved(resolved_by=request.user, notes=resolution_notes)
        
        return Response({
            'message': 'Failure marked as resolved',
            'failure_id': str(failure.id),
            'resolved_at': failure.resolved_at.isoformat(),
            'resolved_by': request.user.username
        })

    @action(detail=True, methods=['post'], url_path='retry')
    def retry_transfer(self, request, pk=None):
        """Retry a failed transfer."""
        failure = self.get_object()
        
        # Check if retry is allowed
        if not failure.can_retry():
            return Response({
                'error': 'Retry not allowed',
                'message': 'This failure cannot be retried (max retries reached or already resolved).'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Only staff can retry transfers
        if not request.user.is_staff:
            return Response({
                'error': 'Permission denied',
                'message': 'Only staff can retry failed transfers.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Increment retry count
            failure.increment_retry()
            
            # Reset transfer status to pending for retry
            transfer = failure.transfer
            transfer.status = 'pending'
            transfer.failure_reason = None
            transfer.save(update_fields=['status', 'failure_reason', 'updated_at'])
            
            return Response({
                'message': 'Transfer queued for retry',
                'transfer_id': str(transfer.id),
                'retry_count': failure.retry_count,
                'max_retries': failure.max_retries
            })
            
        except Exception as e:
            return Response({
                'error': 'Retry failed',
                'message': f'Failed to retry transfer: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
