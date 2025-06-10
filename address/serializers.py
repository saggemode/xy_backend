from rest_framework import serializers
from .models import ShippingAddress

class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'user', 'full_name', 'address_line1', 'address_line2',
            'city', 'state', 'postal_code', 'country', 'phone',
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate(self, data):
        # If this is being set as default, unset any existing default addresses
        if data.get('is_default'):
            ShippingAddress.objects.filter(
                user=self.context['request'].user,
                is_default=True
            ).update(is_default=False)
        return data
