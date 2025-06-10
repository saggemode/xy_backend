from rest_framework import serializers
from .models import Inventory
from product.models import Product, ProductVariant

class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields = ['id', 'product', 'product_name', 'variant', 'variant_name',
                 'quantity', 'low_stock_threshold', 'is_low_stock',
                 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_is_low_stock(self, obj):
        return obj.quantity <= obj.low_stock_threshold
