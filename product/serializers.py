from rest_framework import serializers
from .models import (
    Product, ProductVariant, Category, SubCategory, Coupon,  
    CouponUsage, FlashSale, FlashSaleItem
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
    on_sale = serializers.BooleanField(read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'base_price', 'discount_price', 'current_price', 'on_sale',
            'description', 'image_urls', 'stock', 'is_featured', 'has_variants',
            'sku', 'slug', 'status',
            'available_sizes', 'available_colors', 'created_at', 'updated_at', 
            'store', 'category', 'subcategory', 'variants', 'category_name', 
            'subcategory_name'
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
