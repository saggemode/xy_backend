from rest_framework import serializers
from .models import Cart
from store.serializers import WalletSerializer, XySaveSerializer
from store.models import Store
from bank.models import Wallet, XySaveAccount

class SimpleStoreSerializer(serializers.ModelSerializer):
    """Simple store serializer with payment details"""
    wallet_details = WalletSerializer(source='wallet', read_only=True)
    xysave_details = XySaveSerializer(source='xy_save_account', read_only=True)

    class Meta:
        model = Store
        fields = ['id', 'name', 'status', 'wallet_details', 'xysave_details']

class CartSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    store_details = SimpleStoreSerializer(source='store', read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'store', 'store_details', 'product', 'variant', 'quantity', 'selected_size',
            'selected_color', 'unit_price', 'total_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Custom representation to include detailed product and store info"""
        data = super().to_representation(instance)
        
        # Add detailed product info
        if instance.product:
            data['product_name'] = instance.product.name
            data['product_price'] = str(instance.product.current_price)
            data['product_original_price'] = str(instance.product.original_price)
            data['product_on_sale'] = instance.product.on_sale
            data['product_discount_percentage'] = instance.product.discount_percentage
            data['product_images'] = instance.product.image_urls or []
            data['product_sku'] = instance.product.sku
            data['product_status'] = instance.product.status
        
        # Add basic store info
        if instance.store:
            data['store_name'] = instance.store.name
            data['store_status'] = getattr(instance.store, 'status', 'unknown')
        
        # Add detailed variant info
        if instance.variant:
            data['variant_name'] = instance.variant.name
            data['variant_type'] = instance.variant.variant_type
            data['variant_price'] = str(instance.variant.current_price)
            data['variant_base_price'] = str(instance.variant.base_price)
            data['variant_pricing_mode'] = instance.variant.pricing_mode
            if instance.variant.pricing_mode == 'adjustment':
                data['variant_price_adjustment'] = str(instance.variant.price_adjustment)
            elif instance.variant.pricing_mode == 'individual':
                data['variant_individual_price'] = str(instance.variant.individual_price)
        
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
            
        # Prevent users from adding their own products to cart
        if product.store.owner == self.context['request'].user:
            raise serializers.ValidationError("You cannot add your own products to your cart")

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
    """Serializer for cart summary with sale information"""
    total_items = serializers.IntegerField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    original_total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_savings = serializers.DecimalField(max_digits=10, decimal_places=2)
    items_on_sale = serializers.IntegerField()
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
