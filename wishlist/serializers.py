from rest_framework import serializers
from .models import Wishlist
from core.serializers import ProductSerializer

class WishlistSerializer(serializers.ModelSerializer):
    userId = serializers.PrimaryKeyRelatedField(read_only=True)
    products = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'userId', 'products', 'created_at', 'updated_at']
        read_only_fields = ['userId', 'created_at', 'updated_at']

    def get_products(self, obj):
        products = obj.product.all()
        return ProductSerializer(products, many=True).data

class WishlistCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = ['product']

