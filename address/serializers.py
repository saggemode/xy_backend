from rest_framework import serializers
from .models import ShippingAddress
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class ShippingAddressSerializer(serializers.ModelSerializer):
    full_address = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'user', 'address', 'city', 'state', 'postal_code', 'country',
            'phone', 'additional_phone', 'is_default', 'address_type', 'created_at', 'updated_at', 'full_address',
            'latitude', 'longitude', 'is_deleted', 'deleted_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'full_address', 'is_deleted', 'deleted_at', 'created_by', 'updated_by']
        extra_kwargs = {
            'address': {'required': True},
            'city': {'required': True},
            'state': {'required': False, 'allow_blank': True},
            'country': {'required': False, 'allow_blank': True},
            'postal_code': {'required': False, 'allow_blank': True},
            'phone': {'required': True, 'allow_blank': False},
            'additional_phone': {'required': False, 'allow_blank': True},
            'is_default': {'required': False},
            'address_type': {'required': False},
            'latitude': {'required': False},
            'longitude': {'required': False},
        }

    def validate(self, data):
        # Validate phone format
        phone = data.get('phone')
        if phone and not phone.isdigit():
            raise serializers.ValidationError({'phone': 'Phone number must be numeric.'})
        # Only one default per user
        is_default = data.get('is_default', False)
        user = self.context['request'].user if 'request' in self.context else None
        if is_default and user:
            qs = ShippingAddress.objects.filter(user=user, is_default=True, is_deleted=False)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'is_default': 'Only one default address allowed per user.'})
        # Limit to 3 addresses per user (excluding soft-deleted)
        if not self.instance and user:
            count = ShippingAddress.objects.filter(user=user, is_deleted=False).count()
            if count >= 3:
                raise serializers.ValidationError({'non_field_errors': 'You can only have up to 3 addresses.'})
        return data

    def create(self, validated_data):
        user = self.context['request'].user if 'request' in self.context else None
        validated_data['created_by'] = user
        validated_data['updated_by'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user = self.context['request'].user if 'request' in self.context else None
        validated_data['updated_by'] = user
        return super().update(instance, validated_data)
