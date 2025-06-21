from rest_framework import serializers
from .models import (
    Product, ProductVariant, Category, SubCategory, Coupon,  
    CouponUsage, FlashSale, FlashSaleItem, ProductReview
)

class SubCategorySerializer(serializers.ModelSerializer):
    """Serializer for the SubCategory model."""
    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'image_url']

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for the Category model, including nested subcategories."""
    subcategories = SubCategorySerializer(many=True, read_only=True)
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'image_url', 'subcategories', 'product_count', 'created_at']

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(source='review_count', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'base_price', 'description', 'image_urls',
            'stock', 'is_featured', 'has_variants', 'rating', 'review_count',
            'available_sizes', 'available_colors', 'created_at', 'updated_at', 
            'store', 'category', 'subcategory', 'variants', 'category_name', 
            'subcategory_name'
        ]

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

class CouponUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponUsage
        fields = '__all__'

class FlashSaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashSale
        fields = '__all__'

class FlashSaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashSaleItem
        fields = '__all__'

class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    store = serializers.UUIDField(source='store.id', read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            'id', 'user', 'user_name', 'product', 'store', 'rating', 'title', 'content', 
            'is_verified_purchase', 'helpful_votes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user']
