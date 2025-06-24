from rest_framework import serializers
from .models import ShippingAddress
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class ShippingAddressSerializer(serializers.ModelSerializer):
    full_address = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'user', 'address', 'city', 'state', 'postal_code', 'country',
            'phone', 'additional_phone', 'is_default', 'address_type', 'created_at', 'updated_at', 'full_address',
            'latitude', 'longitude'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'full_address']
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
        try:
            # If this is being set as default, unset any existing default addresses
            if data.get('is_default') and 'request' in self.context:
                user = self.context['request'].user
                if user.is_authenticated:
                    ShippingAddress.objects.filter(
                        user=user,
                        is_default=True
                    ).update(is_default=False)
            return data
        except Exception:
            return data
