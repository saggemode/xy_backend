from rest_framework import serializers
from .models import (
    Store, 
    StoreAnalytics,
    StoreStaff,

)
from product.models import Product, ProductVariant
from django.contrib.auth.models import User

class SimpleProductSerializer(serializers.ModelSerializer):
    """Simple product serializer for store context."""
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'base_price', 'discount_price', 'description', 
            'image_urls', 'stock', 'is_featured', 'sku', 'slug', 'status', 
            'available_sizes', 'available_colors', 'created_at', 'updated_at'
        ]

class StoreStaffSerializer(serializers.ModelSerializer):
    staff_username = serializers.CharField(source='user.username', read_only=True)
    staff_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = StoreStaff
        fields = ['id', 'role', 'joined_at', 'is_active', 'staff_username', 'staff_email']

class StoreAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreAnalytics
        fields = '__all__'

class StoreSerializer(serializers.ModelSerializer):
    total_products = serializers.SerializerMethodField()
    total_staff = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    
    # Optional nested fields
    products = serializers.SerializerMethodField()
    staff = serializers.SerializerMethodField()

    def get_total_products(self, obj):
        return obj.products.count()

    def get_total_staff(self, obj):
        return obj.storestaff_set.count()
    
    def get_products(self, obj):
        request = self.context.get('request')
        if request and request.query_params.get('include_products') == 'true':
            return SimpleProductSerializer(obj.products.all(), many=True, context=self.context).data
        return None
    
    def get_staff(self, obj):
        request = self.context.get('request')
        if request and request.query_params.get('include_staff') == 'true':
            return StoreStaffSerializer(obj.storestaff_set.all(), many=True, context=self.context).data
        return None

    class Meta:
        model = Store
        fields = '__all__'

# ... existing code ...
  
