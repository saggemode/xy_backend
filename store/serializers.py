from rest_framework import serializers
from .models import (
    Store, 
    StoreAnalytics,
    StoreStaff,

)
from product.models import Product, ProductVariant
from django.contrib.auth.models import User

class StoreProductSerializer(serializers.ModelSerializer):
    """Simplified product serializer for store context."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    on_sale = serializers.BooleanField(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews.exists():
            return round(sum(review.rating for review in reviews) / reviews.count(), 2)
        return 0.0

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'base_price', 'discount_price', 'current_price', 'on_sale',
            'description', 'image_urls', 'stock', 'is_featured', 'has_variants',
            'sku', 'slug', 'status', 'available_sizes', 'available_colors', 
            'created_at', 'updated_at', 'category_name', 'subcategory_name',
            'review_count', 'average_rating'
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
    products = StoreProductSerializer(many=True, read_only=True)
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
  
