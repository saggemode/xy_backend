from rest_framework import serializers
from .models import (
    Store, 
    StoreAnalytics,
    StoreStaff,

)
from product.models import Product, ProductVariant
from django.contrib.auth.models import User

class StoreStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreStaff
        fields = ['id', 'store', 'user', 'role', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class StoreAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreAnalytics
        fields = ['id', 'store', 'total_sales', 'total_orders', 'average_order_value', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'owner', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['owner', 'created_at', 'updated_at']
  
