from rest_framework import serializers
from .models import ShippingAddress
from phonenumber_field.serializerfields import PhoneNumberField
from cities_light.models import Country, Region

class SimpleShippingAddressSerializer(serializers.ModelSerializer):
    """Simple serializer for debugging - minimal fields only"""
    
    class Meta:
        model = ShippingAddress
        fields = ['id', 'address', 'city', 'created_at']
        read_only_fields = ['id', 'created_at']

class Test1Serializer(serializers.ModelSerializer):
    """Test 1: Add user field"""
    
    class Meta:
        model = ShippingAddress
        fields = ['id', 'user', 'address', 'city', 'created_at']
        read_only_fields = ['id', 'created_at']

class Test2Serializer(serializers.ModelSerializer):
    """Test 2: Add state field"""
    
    class Meta:
        model = ShippingAddress
        fields = ['id', 'user', 'address', 'city', 'state', 'created_at']
        read_only_fields = ['id', 'created_at']

class Test3Serializer(serializers.ModelSerializer):
    """Test 3: Add country field"""
    
    class Meta:
        model = ShippingAddress
        fields = ['id', 'user', 'address', 'city', 'state', 'country', 'created_at']
        read_only_fields = ['id', 'created_at']

class Test4Serializer(serializers.ModelSerializer):
    """Test 4: Add phone field"""
    phone = PhoneNumberField(required=False, allow_null=True)
    
    class Meta:
        model = ShippingAddress
        fields = ['id', 'user', 'address', 'city', 'state', 'country', 'phone', 'created_at']
        read_only_fields = ['id', 'created_at']

class Test5Serializer(serializers.ModelSerializer):
    """Test 5: Add full_address property"""
    phone = PhoneNumberField(required=False, allow_null=True)
    full_address = serializers.CharField(source='full_address', read_only=True)
    
    class Meta:
        model = ShippingAddress
        fields = ['id', 'user', 'address', 'city', 'state', 'country', 'phone', 'full_address', 'created_at']
        read_only_fields = ['id', 'created_at']

class ShippingAddressSerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(), required=False, allow_null=True)
    state = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), required=False, allow_null=True)
    phone = PhoneNumberField(required=False, allow_null=True)
    additional_phone = PhoneNumberField(required=False, allow_null=True)
    id = serializers.UUIDField(read_only=True)
    full_address = serializers.CharField(source='full_address', read_only=True)
    address_type = serializers.ChoiceField(choices=ShippingAddress.AddressType.choices, required=False)

    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'user', 'address', 'city', 'state', 'postal_code', 'country',
            'phone', 'additional_phone', 'is_default', 'address_type', 'created_at', 'updated_at', 'full_address'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'full_address']

    def validate(self, data):
        # If this is being set as default, unset any existing default addresses
        if data.get('is_default') and 'request' in self.context:
            user = self.context['request'].user
            if user.is_authenticated:
                ShippingAddress.objects.filter(
                    user=user,
                    is_default=True
                ).update(is_default=False)
        return data

class Test6Serializer(serializers.ModelSerializer):
    """Test 6: Add all remaining fields with simple config"""
    phone = PhoneNumberField(required=False, allow_null=True)
    additional_phone = PhoneNumberField(required=False, allow_null=True)
    full_address = serializers.CharField(source='full_address', read_only=True)
    
    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'user', 'address', 'city', 'state', 'country', 'postal_code',
            'phone', 'additional_phone', 'is_default', 'address_type', 'created_at', 'updated_at', 'full_address'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_address']

class Test7Serializer(serializers.ModelSerializer):
    """Test 7: Original serializer but without validation method"""
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(), required=False, allow_null=True)
    state = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), required=False, allow_null=True)
    phone = PhoneNumberField(required=False, allow_null=True)
    additional_phone = PhoneNumberField(required=False, allow_null=True)
    id = serializers.UUIDField(read_only=True)
    full_address = serializers.CharField(source='full_address', read_only=True)
    address_type = serializers.ChoiceField(choices=ShippingAddress.AddressType.choices, required=False)

    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'user', 'address', 'city', 'state', 'postal_code', 'country',
            'phone', 'additional_phone', 'is_default', 'address_type', 'created_at', 'updated_at', 'full_address'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'full_address']
