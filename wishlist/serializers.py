from rest_framework import serializers
from .models import Wishlist
from product.models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'base_price', 'description', 
            'image_urls', 'stock', 'rating', 'is_featured',
            'has_variants', 'available_sizes', 'available_colors',
            'created_at', 'updated_at', 'store', 'category', 'subcategory'
        ]
        read_only_fields = ['created_at', 'updated_at']

class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        source='product'
    )

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        user = self.context['request'].user
        return Wishlist.objects.create(user=user, **validated_data)
