from rest_framework import serializers
from .models import Cart
from product.serializers import ProductSerializer

class CartSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'product', 'product_details', 'quantity', 'total_price', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at'] 