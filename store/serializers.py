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
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = StoreStaff
        fields = '__all__'

class StoreAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreAnalytics
        fields = '__all__'

class StoreSerializer(serializers.ModelSerializer):
    products = SimpleProductSerializer(many=True, read_only=True)
    staff = StoreStaffSerializer(many=True, read_only=True)
    total_products = serializers.SerializerMethodField()
    total_staff = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)

    def get_total_products(self, obj):
        return obj.products.count()

    def get_total_staff(self, obj):
        return obj.staff.count()

    class Meta:
        model = Store
        fields = '__all__'
  
