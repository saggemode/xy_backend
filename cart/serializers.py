from rest_framework import serializers
from .models import Cart, CartItem
from core.models import Product, ProductVariant, Store
from django.contrib.auth.models import User
from django.utils import timezone

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    is_saved_for_later = serializers.BooleanField(default=False)

    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_name', 'product_image',
            'variant', 'variant_name', 'quantity', 'unit_price',
            'total_price', 'added_at', 'is_saved_for_later'
        ]
        read_only_fields = ['added_at']

    def get_product_image(self, obj):
        image = obj.product.images.filter(is_primary=True).first()
        if image:
            return image.image.url
        return None

    def validate(self, data):
        # Validate that product belongs to the same store as cart
        if data['product'].store != self.context['cart'].store:
            raise serializers.ValidationError(
                "Product must belong to the same store as the cart"
            )
        
        # Validate variant if provided
        if data.get('variant'):
            if data['variant'].product != data['product']:
                raise serializers.ValidationError(
                    "Variant must belong to the selected product"
                )
            if data['variant'].stock < data['quantity']:
                raise serializers.ValidationError(
                    "Not enough stock available for this variant"
                )
        else:
            if data['product'].stock < data['quantity']:
                raise serializers.ValidationError(
                    "Not enough stock available"
                )
        
        return data

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'stock']

class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'price', 'stock']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    shipping_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    final_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    time_remaining = serializers.SerializerMethodField()
    recommended_items = serializers.SerializerMethodField()
    recently_viewed = serializers.SerializerMethodField()
    saved_items = serializers.SerializerMethodField()
    active_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'user_name', 'store', 'store_name',
            'items', 'total_items', 'subtotal', 'is_active',
            'created_at', 'updated_at', 'expires_at', 'notes',
            'is_template', 'template_name', 'tax_amount',
            'shipping_cost', 'discount_amount', 'final_total',
            'is_expired', 'time_remaining', 'recommended_items',
            'recently_viewed', 'saved_items', 'active_items'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_time_remaining(self, obj):
        if obj.expires_at:
            remaining = obj.expires_at - timezone.now()
            return remaining.total_seconds()
        return None

    def get_recommended_items(self, obj):
        recommended = obj.get_recommended_items()
        return ProductSerializer(recommended, many=True).data

    def get_recently_viewed(self, obj):
        viewed = obj.get_recently_viewed()
        return ProductSerializer(viewed, many=True).data

    def get_saved_items(self, obj):
        saved = obj.get_saved_items()
        return CartItemSerializer(saved, many=True).data

    def get_active_items(self, obj):
        active = obj.get_active_items()
        return CartItemSerializer(active, many=True).data

    def create(self, validated_data):
        # Get the store from the context
        store = self.context.get('store')
        if not store:
            raise serializers.ValidationError("Store is required")
        
        # Deactivate any existing active carts for this user and store
        Cart.objects.filter(
            user=validated_data['user'],
            store=store,
            is_active=True
        ).update(is_active=False)
        
        # Create new cart
        cart = Cart.objects.create(
            user=validated_data['user'],
            store=store,
            is_active=True
        )
        return cart

class CartTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ['id', 'template_name', 'created_at', 'items']
        read_only_fields = ['created_at']

class MergeCartSerializer(serializers.Serializer):
    source_cart_id = serializers.IntegerField()

    def validate_source_cart_id(self, value):
        try:
            cart = Cart.objects.get(id=value)
            if cart.user != self.context['request'].user:
                raise serializers.ValidationError("Cannot merge carts from different users")
            return value
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Source cart not found")

class SaveCartTemplateSerializer(serializers.Serializer):
    template_name = serializers.CharField(max_length=100)

class ApplyCouponSerializer(serializers.Serializer):
    coupon_code = serializers.CharField(max_length=50)

class CartNoteSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)

class SaveForLaterSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()

    def validate_item_id(self, value):
        try:
            cart = self.context['cart']
            cart.items.get(id=value)
            return value
        except CartItem.DoesNotExist:
            raise serializers.ValidationError("Cart item not found")

class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, data):
        try:
            product = Product.objects.get(id=data['product_id'])
            data['product'] = product
            
            if data.get('variant_id'):
                try:
                    variant = ProductVariant.objects.get(
                        id=data['variant_id'],
                        product=product
                    )
                    data['variant'] = variant
                except ProductVariant.DoesNotExist:
                    raise serializers.ValidationError(
                        "Invalid variant for this product"
                    )
            
            return data
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")

class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        cart_item = self.context.get('cart_item')
        if cart_item.variant:
            if cart_item.variant.stock < value:
                raise serializers.ValidationError(
                    "Not enough stock available for this variant"
                )
        else:
            if cart_item.product.stock < value:
                raise serializers.ValidationError(
                    "Not enough stock available"
                )
        return value 