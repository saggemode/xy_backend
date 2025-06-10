from rest_framework import serializers
from .models import Coupon

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_value',
            'min_purchase_amount', 'max_discount_amount', 'start_date',
            'end_date', 'is_active', 'usage_limit', 'used_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['used_count', 'created_at', 'updated_at']

    def validate(self, data):
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] >= data['end_date']:
                raise serializers.ValidationError("End date must be after start date")
        
        if data.get('discount_type') == 'percentage' and data.get('discount_value'):
            if data['discount_value'] > 100:
                raise serializers.ValidationError("Percentage discount cannot exceed 100%")
        
        if data.get('max_discount_amount') and data.get('discount_type') == 'percentage':
            if data['max_discount_amount'] <= 0:
                raise serializers.ValidationError("Maximum discount amount must be greater than 0")
        
        return data 