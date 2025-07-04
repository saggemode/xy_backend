from rest_framework import serializers
from .models import (
    Product, ProductVariant, Category, SubCategory, Coupon,  
    CouponUsage, FlashSale, FlashSaleItem, ProductReview, ProductDiscount
)
from store.models import Store

class ProductReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    product = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = ProductReview
        fields = ['id', 'user', 'product', 'rating', 'review_text', 'created_at']
        read_only_fields = ['user', 'product', 'created_at']

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
    variant_type_display = serializers.CharField(source='get_variant_type_display', read_only=True)
    pricing_mode_display = serializers.CharField(source='get_pricing_mode_display', read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product', 'name', 'variant_type', 'variant_type_display',
            'pricing_mode', 'pricing_mode_display', 'price_adjustment', 
            'individual_price', 'current_price', 'base_price', 'stock', 
            'is_active', 'sku', 'created_at', 'updated_at'
        ]
        read_only_fields = ['sku', 'current_price', 'base_price']

class SimpleStoreSerializer(serializers.ModelSerializer):
    """A simple serializer for store details to be nested in products."""
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'logo', 'is_verified', 'location'
        ]

class ProductDiscountSerializer(serializers.ModelSerializer):
    """Serializer for product discounts"""
    class Meta:
        model = ProductDiscount
        fields = [
            'id', 'discount_type', 'discount_value', 'start_date', 'end_date',
            'is_active', 'min_quantity', 'max_discount_amount'
        ]

class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    size_variants = serializers.SerializerMethodField()
    color_variants = serializers.SerializerMethodField()
    reviews = ProductReviewSerializer(many=True, read_only=True)
    store = SimpleStoreSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    on_sale = serializers.BooleanField(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    original_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    active_discount = ProductDiscountSerializer(read_only=True)
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    has_size_variants = serializers.BooleanField(read_only=True)
    has_color_variants = serializers.BooleanField(read_only=True)

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews.exists():
            return round(sum(review.rating for review in reviews) / reviews.count(), 2)
        return 0.0
    
    def get_size_variants(self, obj):
        """Get only size variants"""
        size_variants = obj.size_variants
        return ProductVariantSerializer(size_variants, many=True).data
    
    def get_color_variants(self, obj):
        """Get only color variants"""
        color_variants = obj.color_variants
        return ProductVariantSerializer(color_variants, many=True).data

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'base_price', 'original_price', 'current_price', 'on_sale',
            'discount_percentage', 'active_discount', 'description', 'image_urls', 'stock', 
            'is_featured', 'has_variants', 'has_size_variants', 'has_color_variants', 'sku', 'slug', 'status',
            'available_sizes', 'available_colors', 'created_at', 'updated_at', 
            'store', 'category', 'subcategory', 'variants', 'size_variants', 'color_variants', 
            'category_name', 'subcategory_name', 'reviews', 'review_count', 'average_rating'
        ]
        read_only_fields = ['sku', 'slug']

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
