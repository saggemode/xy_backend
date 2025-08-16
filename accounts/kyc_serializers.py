from rest_framework import serializers
from .models import KYCProfile, KYCLevelChoices

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