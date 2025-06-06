from rest_framework import serializers
from .models import Wishlist
from core.serializers import ProductSerializer

class WishlistSerializer(serializers.ModelSerializer):
    userId = serializers.PrimaryKeyRelatedField(read_only=True)
    products = ProductSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'userId', 'products', 'created_at', 'updated_at']
        read_only_fields = ['userId', 'created_at', 'updated_at']

class WishlistCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wishlist
        fields = ['product']

