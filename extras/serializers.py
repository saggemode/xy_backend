from rest_framework import serializers
from .models import Address, UserVerification
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class AddressSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = Address
        fields = [
            'id', 'user', 'address', 'city', 'state', 'postal_code', 'country',
            'latitude', 'longitude', 'phone', 'additional_phone', 'address_type',
            'is_default', 'is_active', 'is_verified', 'verification_date',
            'notes', 'created_at', 'updated_at', 'full_address'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'verification_date']

    def validate(self, data):
        """Validate address data"""
        if data.get('is_default') and not data.get('is_verified'):
            raise serializers.ValidationError(
                "Address must be verified before setting as default"
            )
        return data

class UserVerificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    verification_summary = serializers.SerializerMethodField()

    class Meta:
        model = UserVerification
        fields = [
            'id', 'user', 'is_verified', 'verification_method',
            'verification_status', 'verification_attempts',
            'last_verification_attempt', 'is_blocked', 'blocked_until',
            'security_questions', 'document_verification', 'biometric_data',
            'verification_history', 'verification_summary'
        ]
        read_only_fields = [
            'id', 'user', 'verification_attempts', 'last_verification_attempt',
            'is_blocked', 'blocked_until', 'verification_history'
        ]

    def get_verification_summary(self, obj):
        """Get verification summary"""
        return obj.get_verification_summary()

    def validate_security_questions(self, value):
        """Validate security questions format"""
        if value:
            if not isinstance(value, dict):
                raise serializers.ValidationError(
                    "Security questions must be a dictionary"
                )
            for question, answer in value.items():
                if not question or not answer:
                    raise serializers.ValidationError(
                        "Questions and answers cannot be empty"
                    )
        return value

    def validate_document_verification(self, value):
        """Validate document verification data"""
        if value:
            required_fields = ['document_type', 'document_number', 'issue_date']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"Missing required field: {field}"
                    )
        return value

    def validate_biometric_data(self, value):
        """Validate biometric data"""
        if value:
            if not isinstance(value, dict):
                raise serializers.ValidationError(
                    "Biometric data must be a dictionary"
                )
            if 'type' not in value or 'data' not in value:
                raise serializers.ValidationError(
                    "Biometric data must include type and data"
                )
        return value
