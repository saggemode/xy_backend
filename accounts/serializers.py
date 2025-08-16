
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from .models import UserProfile, KYCProfile, KYCLevelChoices
from .utils import set_otp, send_otp_email, send_otp_sms
from dj_rest_auth.serializers import LoginSerializer
from bank.models import Wallet, Transaction
from .kyc_serializers import KYCProfileDetailSerializer
from notification.models import Notification

User = get_user_model()

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications in profile response."""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'level', 'status',
            'isRead', 'action_text', 'action_url', 'link', 'priority', 'source',
            'created_at', 'read_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Convert UUID to string
        data['id'] = str(data['id'])
        # Convert datetime to ISO format
        if data['created_at']:
            data['created_at'] = instance.created_at.isoformat()
        if data['read_at']:
            data['read_at'] = instance.read_at.isoformat()
        return data

class CustomRegisterSerializer(RegisterSerializer):
    phone = PhoneNumberField(required=True)
    is_verified = serializers.BooleanField(read_only=True)
    
    def is_fully_verified(self, user):
        profile = getattr(user, 'profile', None)
        if not profile or not profile.is_verified:
            return False
        from .models import KYCProfile
        kyc = KYCProfile.objects.filter(user=user, is_approved=True).first()
        has_kyc = kyc and (kyc.bvn or kyc.nin)
        has_wallet = Wallet.objects.filter(user=user).exists()
        return has_kyc and has_wallet

    def validate_username(self, value):
        user_qs = User.objects.filter(username=value)
        if user_qs.exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_email(self, value):
        user_qs = User.objects.filter(email=value)
        if user_qs.exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return value

    def validate_phone(self, value):
        profile_qs = UserProfile.objects.filter(phone=value)
        if profile_qs.exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value
    
    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data['phone'] = self.validated_data.get('phone', '')
        # is_verified is always False on registration
        data['is_verified'] = False
        return data
    
    def save(self, request):
        username = self.validated_data.get('username')
        email = self.validated_data.get('email')
        phone = self.validated_data.get('phone')
        user = User.objects.filter(username=username).first()
        if user and not self.is_fully_verified(user):
            # Update existing incomplete user
            user.email = email
            user.save()
            profile = user.profile
            profile.phone = phone
            profile.save()
            # Generate and send OTP after registration (OTP is sent via email and contains the code)
            otp = set_otp(profile)
            send_otp_email(user, otp)
            send_otp_sms(profile.phone, otp)
            return user
        # Otherwise, create a new user as normal
        user = super().save(request)
        profile = user.profile
        profile.phone = phone
        profile.save()
        # Generate and send OTP after registration (OTP is sent via email and contains the code)
        otp = set_otp(profile)
        send_otp_email(user, otp)
        send_otp_sms(profile.phone, otp)
        return user

class CustomLoginSerializer(LoginSerializer):
    username = serializers.CharField(required=False, allow_blank=True, label="Username, Email or Phone")

class UserProfileSerializer(serializers.ModelSerializer):
    kyc = serializers.SerializerMethodField()
    wallet = serializers.SerializerMethodField()
    transactions = serializers.SerializerMethodField()
    transaction_pin = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = '__all__'

    def get_kyc(self, obj):
        kyc = KYCProfile.objects.filter(user=obj.user).first()
        if kyc:
            return KYCProfileDetailSerializer(kyc).data
        return None

    def get_wallet(self, obj):
        wallet = Wallet.objects.filter(user=obj.user).first()
        if wallet:
            return {
                'id': wallet.id,
                'account_number': wallet.account_number,
                'alternative_account_number': wallet.alternative_account_number,
                'balance': str(wallet.balance),
                'currency': wallet.currency,
                'created_at': wallet.created_at,
                'updated_at': wallet.updated_at
            }
        return None

    def get_transactions(self, obj):
        transactions = Transaction.objects.filter(wallet__user=obj.user).order_by('-timestamp')[:10]
        return [
            {
                'id': t.id,
                'reference': t.reference,
                'amount': str(t.amount),
                'transaction_type': t.type,
                'status': t.status,
                'description': t.description,
                'timestamp': t.timestamp
            }
            for t in transactions
        ]

    def get_transaction_pin(self, obj):
        # Hide the actual PIN value for security
        return "***" if obj.transaction_pin else None

    def get_notifications(self, obj):
        notifications = Notification.objects.filter(recipient=obj.user).order_by('-created_at')[:10]
        return NotificationSerializer(notifications, many=True).data

class KYCProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCProfile
        fields = [
            'id', 'bvn', 'nin', 'date_of_birth', 'state', 'gender', 'lga', 'area', 
            'address', 'telephone_number', 'passport_photo', 'selfie', 'id_document', 
            'govt_id_type', 'govt_id_document', 'proof_of_address',
            'kyc_level', 'is_approved', 'created_at'
        ]
        read_only_fields = ['id', 'is_approved', 'created_at']

    def validate(self, data):
        user = self.context['request'].user
        # Prevent duplicate KYCProfile
        if KYCProfile.objects.filter(user=user).exists():
            raise serializers.ValidationError('You already have a KYC profile.')
        bvn = data.get('bvn')
        nin = data.get('nin')
        if not bvn and not nin:
            raise serializers.ValidationError('Either BVN or NIN is required.')
        if bvn:
            if not bvn.isdigit() or len(bvn) != 11:
                raise serializers.ValidationError('BVN must be 11 digits.')
            if KYCProfile.objects.filter(bvn=bvn).exists():
                raise serializers.ValidationError('This BVN is already in use.')
        if nin:
            if not nin.isdigit() or len(nin) != 11:
                raise serializers.ValidationError('NIN must be 11 digits.')
            if KYCProfile.objects.filter(nin=nin).exists():
                raise serializers.ValidationError('This NIN is already in use.')
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        # Auto-approve and set tier 1
        validated_data['user'] = user
        validated_data['kyc_level'] = KYCLevelChoices.TIER_1
        validated_data['is_approved'] = True
        return super().create(validated_data)

class KYCProfileDetailSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    daily_transaction_limit = serializers.SerializerMethodField()
    max_balance_limit = serializers.SerializerMethodField()
    class Meta:
        model = KYCProfile
        fields = '__all__'
    def get_daily_transaction_limit(self, obj):
        return obj.get_daily_transaction_limit()
    def get_max_balance_limit(self, obj):
        return obj.get_max_balance_limit()

class KYCLevelUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCProfile
        fields = ['kyc_level']
    def validate_kyc_level(self, value):
        instance = self.instance
        # ... (validation logic as in bank/serializers.py) ...
        return value 

class BVNValidationSerializer(serializers.Serializer):
    bvn = serializers.CharField(min_length=10, max_length=10)

class NINValidationSerializer(serializers.Serializer):
    nin = serializers.CharField(min_length=10, max_length=10) 

class SetTransactionPinSerializer(serializers.Serializer):
    pin = serializers.CharField(min_length=4, max_length=10, write_only=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('PIN must be numeric.')
        if len(value) < 4:
            raise serializers.ValidationError('PIN must be at least 4 digits.')
        return value 

class UpdateTransactionPinSerializer(serializers.Serializer):
    old_pin = serializers.CharField(min_length=4, max_length=10, write_only=True)
    new_pin = serializers.CharField(min_length=4, max_length=10, write_only=True)

    def validate_old_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('Old PIN must be numeric.')
        return value

    def validate_new_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('New PIN must be numeric.')
        if len(value) < 4:
            raise serializers.ValidationError('New PIN must be at least 4 digits.')
        return value 