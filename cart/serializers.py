from rest_framework import serializers
from .models import Cart

class CartSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'store', 'product', 'variant', 'quantity', 'selected_size',
            'selected_color', 'unit_price', 'total_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Custom representation to include basic product and store info"""
        data = super().to_representation(instance)
        
        # Add basic product info
        if instance.product:
            data['product_name'] = instance.product.name
            data['product_price'] = str(instance.product.current_price)
            # Add product images
            data['product_images'] = instance.product.image_urls or []
        
        # Add basic store info
        if instance.store:
            data['store_name'] = instance.store.name
            data['store_status'] = getattr(instance.store, 'status', 'unknown')
        
        # Add basic variant info
        if instance.variant:
            data['variant_name'] = instance.variant.name
            data['variant_price'] = str(instance.variant.current_price)
        
        return data

    def validate_quantity(self, value):
        """Validate quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    def validate(self, data):
        """Validate cart item data"""
        product = data.get('product')
        store = data.get('store')
        variant = data.get('variant')
        quantity = data.get('quantity', 1)

        # Check if product belongs to store
        if product and store and product.store != store:
            raise serializers.ValidationError("Product does not belong to the selected store")

        # Check if variant belongs to product
        if variant and product and variant.product != product:
            raise serializers.ValidationError("Variant does not belong to the selected product")

        # Check stock availability
        if variant:
            if quantity > variant.stock:
                raise serializers.ValidationError(f"Insufficient stock. Available: {variant.stock}")
        elif product:
            if quantity > product.stock:
                raise serializers.ValidationError(f"Insufficient stock. Available: {product.stock}")

        return data

class CartCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating cart items"""
    product_id = serializers.UUIDField(write_only=True)
    variant_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    store_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Cart
        fields = ['product_id', 'variant_id', 'store_id', 'quantity', 'selected_size', 'selected_color']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate cart creation data"""
        from product.models import Product, ProductVariant
        from store.models import Store

        try:
            product = Product.objects.get(id=data['product_id'])
            store = Store.objects.get(id=data['store_id'])
        except (Product.DoesNotExist, Store.DoesNotExist):
            raise serializers.ValidationError("Invalid product or store")

        # Check if product belongs to store
        if product.store != store:
            raise serializers.ValidationError("Product does not belong to the selected store")

        # Validate variant if provided
        variant = None
        if data.get('variant_id'):
            try:
                variant = ProductVariant.objects.get(id=data['variant_id'], product=product)
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError("Invalid variant for this product")

        # Check stock availability
        if variant:
            if data['quantity'] > variant.stock:
                raise serializers.ValidationError(f"Insufficient stock. Available: {variant.stock}")
        else:
            if data['quantity'] > product.stock:
                raise serializers.ValidationError(f"Insufficient stock. Available: {product.stock}")

        # Store the actual objects for creation
        data['product'] = product
        data['store'] = store
        data['variant'] = variant
        return data

    def create(self, validated_data):
        # Remove the write-only IDs before creating the Cart instance
        validated_data.pop('product_id', None)
        validated_data.pop('store_id', None)
        validated_data.pop('variant_id', None)
        
        # Ensure variant is None if not provided
        if 'variant' not in validated_data:
            validated_data['variant'] = None
            
        return super().create(validated_data)

class CartUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating cart items"""
    
    class Meta:
        model = Cart
        fields = ['quantity', 'selected_size', 'selected_color']

    def validate_quantity(self, value):
        """Validate quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    def validate(self, data):
        """Validate cart update data"""
        instance = self.instance
        quantity = data.get('quantity', instance.quantity)

        # Check stock availability
        if instance.variant:
            if quantity > instance.variant.stock:
                raise serializers.ValidationError(f"Insufficient stock. Available: {instance.variant.stock}")
        else:
            if quantity > instance.product.stock:
                raise serializers.ValidationError(f"Insufficient stock. Available: {instance.product.stock}")

        return data

class CartSummarySerializer(serializers.Serializer):
    """Serializer for cart summary"""
    total_items = serializers.IntegerField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    item_count = serializers.IntegerField()
    store = serializers.DictField()
    items = CartSerializer(many=True)

class CartBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk cart updates"""
    cart_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value
