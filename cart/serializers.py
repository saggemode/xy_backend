from rest_framework import serializers
from .models import Cart
from product.serializers import ProductSerializer, ProductVariantSerializer
from store.serializers import StoreSerializer

class CartSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    store_details = StoreSerializer(source='store', read_only=True)
    variant_details = ProductVariantSerializer(source='variant', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'store', 'store_details', 'product', 'product_details',
            'variant', 'variant_details', 'quantity', 'selected_size',
            'selected_color', 'unit_price', 'total_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at'] 