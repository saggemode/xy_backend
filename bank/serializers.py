from rest_framework import serializers
from .models import (
    KYCProfile, Wallet, Transaction, BankTransfer, BillPayment, VirtualCard, Bank,
    StaffRole, StaffProfile, TransactionApproval, CustomerEscalation, StaffActivity,
    TransferFeeRule, SavedBeneficiary, TransferReversal, TransferFailure, NightGuardSettings, LargeTransactionShieldSettings, LocationGuardSettings, PaymentIntent, PayoutRequest, MerchantSettlementAccount
)
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from accounts.kyc_serializers import KYCProfileSerializer, KYCProfileDetailSerializer, KYCLevelUpdateSerializer

class WalletSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    balance = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = ['id', 'user', 'account_number', 'alternative_account_number', 'balance', 'currency', 'created_at']
        read_only_fields = ['id', 'user', 'account_number', 'alternative_account_number', 'created_at']
    
    def get_balance(self, obj):
        return str(obj.balance) if obj.balance else None

class TransactionSerializer(serializers.ModelSerializer):
    wallet = serializers.StringRelatedField()
    amount = serializers.SerializerMethodField()
    balance_after = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'wallet', 'receiver', 'reference', 'amount', 'type', 'channel', 
            'description', 'timestamp', 'status', 'balance_after', 'parent', 
            'currency', 'metadata'
        ]
        read_only_fields = ['id', 'reference', 'timestamp', 'balance_after']
    
    def get_amount(self, obj):
        return str(obj.amount) if obj.amount else None
    
    def get_balance_after(self, obj):
        return str(obj.balance_after) if obj.balance_after else None

class BankTransferSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    amount = serializers.SerializerMethodField()
    fee = serializers.SerializerMethodField()
    vat = serializers.SerializerMethodField()
    levy = serializers.SerializerMethodField()
    
    class Meta:
        model = BankTransfer
        fields = [
            'id', 'user', 'bank_name', 'bank_code', 'account_number', 'amount', 
            'fee', 'vat', 'levy', 'reference', 'status', 'transfer_type', 
            'description', 'failure_reason', 'requires_approval', 'approved_by', 
            'approved_at', 'created_at', 'updated_at', 'nibss_reference'
        ]
        read_only_fields = ['id', 'reference', 'created_at', 'updated_at', 'approved_by', 'approved_at']
    
    def get_amount(self, obj):
        return str(obj.amount) if obj.amount else None
    
    def get_fee(self, obj):
        return str(obj.fee) if obj.fee else None
    
    def get_vat(self, obj):
        return str(obj.vat) if obj.vat else None
    
    def get_levy(self, obj):
        return str(obj.levy) if obj.levy else None

class BillPaymentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    amount = serializers.SerializerMethodField()
    
    class Meta:
        model = BillPayment
        fields = ['id', 'user', 'service_type', 'account_or_meter', 'amount', 'status', 'reference', 'timestamp']
        read_only_fields = ['id', 'reference', 'timestamp']
    
    def get_amount(self, obj):
        return str(obj.amount) if obj.amount else None

class VirtualCardSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    
    class Meta:
        model = VirtualCard
        fields = ['id', 'user', 'card_number', 'expiry', 'cvv', 'provider', 'status', 'issued_at']
        read_only_fields = ['id', 'issued_at']

class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ['id', 'name', 'code', 'slug', 'ussd', 'logo']

class StaffRoleSerializer(serializers.ModelSerializer):
    staff_count = serializers.SerializerMethodField()
    permissions_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = StaffRole
        fields = '__all__'
    
    def get_staff_count(self, obj):
        return obj.staff_members.count()
    
    def get_permissions_summary(self, obj):
        perms = []
        if obj.can_approve_kyc:
            perms.append('KYC')
        if obj.can_manage_staff:
            perms.append('Staff')
        if obj.can_view_reports:
            perms.append('Reports')
        if obj.can_override_transactions:
            perms.append('Override')
        if obj.can_handle_escalations:
            perms.append('Escalations')
        return ', '.join(perms) if perms else 'None'


class StaffProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    role = StaffRoleSerializer(read_only=True)
    supervisor = serializers.SerializerMethodField()
    subordinates_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StaffProfile
        fields = '__all__'
    
    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'full_name': obj.user.get_full_name(),
        }
    
    def get_supervisor(self, obj):
        if obj.supervisor:
            return {
                'id': obj.supervisor.id,
                'name': str(obj.supervisor),
                'role': obj.supervisor.role.name,
            }
        return None
    
    def get_subordinates_count(self, obj):
        return obj.get_subordinates().count()


class TransactionApprovalSerializer(serializers.ModelSerializer):
    transaction = serializers.SerializerMethodField()
    requested_by = StaffProfileSerializer(read_only=True)
    approved_by = StaffProfileSerializer(read_only=True)
    escalated_to = StaffProfileSerializer(read_only=True)
    
    class Meta:
        model = TransactionApproval
        fields = '__all__'
    
    def get_transaction(self, obj):
        return {
            'id': obj.transaction.id,
            'reference': obj.transaction.reference,
            'amount': obj.transaction.amount,
            'type': obj.transaction.type,
            'status': obj.transaction.status,
        }


class CustomerEscalationSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    created_by = StaffProfileSerializer(read_only=True)
    assigned_to = StaffProfileSerializer(read_only=True)
    
    class Meta:
        model = CustomerEscalation
        fields = '__all__'
    
    def get_customer(self, obj):
        return {
            'id': obj.customer.id,
            'username': obj.customer.username,
            'email': obj.customer.email,
            'full_name': obj.customer.get_full_name(),
        }


class StaffActivitySerializer(serializers.ModelSerializer):
    staff = StaffProfileSerializer(read_only=True)
    
    class Meta:
        model = StaffActivity
        fields = '__all__'


class TransferFeeRuleSerializer(serializers.ModelSerializer):
    min_amount = serializers.SerializerMethodField()
    max_amount = serializers.SerializerMethodField()
    fee_fixed = serializers.SerializerMethodField()
    
    class Meta:
        model = TransferFeeRule
        fields = '__all__'
    
    def get_min_amount(self, obj):
        return str(obj.min_amount) if obj.min_amount else None
    
    def get_max_amount(self, obj):
        return str(obj.max_amount) if obj.max_amount else None
    
    def get_fee_fixed(self, obj):
        return str(obj.fee_fixed) if obj.fee_fixed else None


class SavedBeneficiarySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    
    class Meta:
        model = SavedBeneficiary
        fields = [
            'id', 'user', 'name', 'account_number', 'bank_code', 'bank_name',
            'nickname', 'is_verified', 'verification_method', 'last_used',
            'usage_count', 'is_favorite', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'last_used', 'usage_count', 'created_at', 'updated_at']


class TransferReversalSerializer(serializers.ModelSerializer):
    original_transfer = serializers.SerializerMethodField()
    reversal_amount = serializers.SerializerMethodField()
    initiated_by = serializers.StringRelatedField()
    approved_by = serializers.StringRelatedField()
    
    class Meta:
        model = TransferReversal
        fields = [
            'id', 'original_transfer', 'reversal_reason', 'reversal_amount',
            'status', 'initiated_by', 'approved_by', 'failure_reason',
            'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'processed_at']
    
    def get_original_transfer(self, obj):
        return {
            'id': str(obj.original_transfer.id),
            'reference': obj.original_transfer.reference,
            'amount': str(obj.original_transfer.amount),
            'status': obj.original_transfer.status
        }
    
    def get_reversal_amount(self, obj):
        return str(obj.reversal_amount) if obj.reversal_amount else None

class TransferFailureSerializer(serializers.ModelSerializer):
    """Serializer for TransferFailure model."""
    transfer_reference = serializers.CharField(source='transfer.reference', read_only=True)
    user_email = serializers.CharField(source='transfer.user.email', read_only=True)
    failure_summary = serializers.ReadOnlyField()
    
    class Meta:
        model = TransferFailure
        fields = [
            'id', 'transfer', 'transfer_reference', 'user_email',
            'error_code', 'error_category', 'failure_reason', 
            'technical_details', 'stack_trace', 'user_id',
            'ip_address', 'user_agent', 'device_fingerprint',
            'transfer_amount', 'recipient_account', 'recipient_bank_code',
            'failed_at', 'processing_duration', 'is_resolved',
            'resolution_notes', 'resolved_by', 'resolved_at',
            'retry_count', 'last_retry_at', 'max_retries',
            'created_at', 'updated_at', 'failure_summary'
        ]
        read_only_fields = [
            'id', 'transfer', 'transfer_reference', 'user_email',
            'user_id', 'failed_at', 'created_at', 'updated_at',
            'failure_summary'
        ]
    
    def to_representation(self, instance):
        """Custom representation to include additional context."""
        data = super().to_representation(instance)
        
        # Add transfer context
        if instance.transfer:
            data['transfer_context'] = {
                'reference': instance.transfer.reference,
                'status': instance.transfer.status,
                'created_at': instance.transfer.created_at.isoformat(),
                'bank_name': instance.transfer.bank_name,
                'description': instance.transfer.description
            }
        
        # Add user context (masked for security)
        if instance.user_id:
            data['user_context'] = {
                'user_id': str(instance.user_id),
                'masked_email': self._mask_email(instance.transfer.user.email) if instance.transfer else None
            }
        
        return data
    
    def _mask_email(self, email):
        """Mask email for security."""
        if not email:
            return None
        parts = email.split('@')
        if len(parts) == 2:
            username, domain = parts
            masked_username = username[0] + '*' * (len(username) - 2) + username[-1] if len(username) > 2 else username
            return f"{masked_username}@{domain}"
        return email


class NightGuardSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NightGuardSettings
        fields = [
            'enabled', 'start_time', 'end_time', 'primary_method',
            'fallback_method', 'applies_to', 'face_registered_at'
        ]


class LargeTransactionShieldSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LargeTransactionShieldSettings
        fields = [
            'enabled', 'per_transaction_limit', 'daily_limit', 'monthly_limit', 'face_registered_at'
        ]


class LocationGuardSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationGuardSettings
        fields = [
            'enabled', 'allowed_states', 'face_registered_at'
        ]


class PaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = [
            'id', 'user', 'order_id', 'merchant_id', 'amount', 'currency', 'status',
            'description', 'reference', 'escrowed', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'reference', 'created_at', 'updated_at']


class PaymentIntentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = ['order_id', 'merchant_id', 'amount', 'currency', 'description', 'metadata']


class PayoutRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutRequest
        fields = [
            'id', 'merchant_id', 'amount', 'destination_bank_code', 'destination_account_number',
            'description', 'status', 'reference', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'reference', 'created_at', 'updated_at']


class MerchantSettlementAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantSettlementAccount
        fields = [
            'merchant_id', 'bank_code', 'account_number', 'account_name',
            'is_verified', 'verification_method', 'preferred_schedule',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['is_verified', 'verification_method', 'created_at', 'updated_at']
