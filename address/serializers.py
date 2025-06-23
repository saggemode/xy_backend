from rest_framework import serializers
from .models import ShippingAddress
from phonenumber_field.serializerfields import PhoneNumberField
from cities_light.models import Country, Region

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
