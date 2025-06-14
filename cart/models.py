from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from product.models import Product, ProductVariant
from store.models import Store
from django.conf import settings

# Create your models here.
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='carts')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
   

    class Meta:
        unique_together = ('user', 'store', 'is_active')
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        return f"{self.user.username}'s cart - {self.store.name}"

    def save(self, *args, **kwargs):
        if not self.expires_at and not self.is_template:
            # Set expiration to 30 days from creation
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at

    def merge_with(self, other_cart):
        """Merge items from another cart into this one"""
        if not isinstance(other_cart, Cart):
            raise ValueError("Can only merge with another Cart instance")
        
        if other_cart.store != self.store:
            raise ValueError("Cannot merge carts from different stores")
        
        for item in other_cart.items.all():
            try:
                existing_item = self.items.get(
                    product=item.product,
                    variant=item.variant
                )
                existing_item.quantity += item.quantity
                existing_item.save()
            except CartItem.DoesNotExist:
                item.cart = self
                item.save()
        
        other_cart.delete()
        return self

    def save_as_template(self, name):
        """Save current cart as a template"""
        self.is_template = True
        self.template_name = name
        self.is_active = False
        self.save()
        return self

    def load_from_template(self, template_cart):
        """Load items from a template cart"""
        if not template_cart.is_template:
            raise ValueError("Source cart must be a template")
        
        self.clear()
        for item in template_cart.items.all():
            self.add_item(
                product=item.product,
                variant=item.variant,
                quantity=item.quantity
            )
        return self

    def get_recommended_items(self, limit=5):
        """Get recommended items based on cart contents"""
        from django.db.models import Count
        from product.models import Product
        
        # Get products from other users' carts that contain our products
        related_products = Product.objects.filter(
            cartitem__cart__items__product__in=self.items.values_list('product', flat=True)
        ).exclude(
            id__in=self.items.values_list('product', flat=True)
        ).annotate(
            frequency=Count('id')
        ).order_by('-frequency')[:limit]
        
        return related_products

    def get_recently_viewed(self, limit=5):
        """Get recently viewed products"""
        from product.models import ProductView
        
        return ProductView.objects.filter(
            user=self.user
        ).order_by('-viewed_at')[:limit]

    def save_for_later(self, item_id):
        """Move an item to saved for later"""
        try:
            item = self.items.get(id=item_id)
            item.is_saved_for_later = True
            item.save()
            return True
        except CartItem.DoesNotExist:
            return False

    def move_to_cart(self, item_id):
        """Move a saved item back to cart"""
        try:
            item = self.items.get(id=item_id)
            item.is_saved_for_later = False
            item.save()
            return True
        except CartItem.DoesNotExist:
            return False

    def get_saved_items(self):
        """Get all saved for later items"""
        return self.items.filter(is_saved_for_later=True)

    def get_active_items(self):
        """Get all active cart items"""
        return self.items.filter(is_saved_for_later=False)

    def calculate_tax(self):
        """Calculate tax for all items"""
        total_tax = 0
        for item in self.items.all():
            if item.variant:
                tax_rate = item.variant.product.tax_rate
            else:
                tax_rate = item.product.tax_rate
            total_tax += (item.total_price * tax_rate) / 100
        return total_tax

    def calculate_shipping(self):
        """Calculate shipping cost"""
        # This is a placeholder - implement your shipping logic here
        return 0

    def get_total_with_tax_and_shipping(self):
        """Get total including tax and shipping"""
        return self.subtotal + self.calculate_tax() + self.calculate_shipping()

    def apply_coupon(self, coupon_code):
        """Apply a coupon to the cart"""
        from coupon.models import Coupon
        try:
            coupon = Coupon.objects.get(
                code=coupon_code,
                store=self.store,
                is_active=True
            )
            if coupon.is_valid_for_user(self.user):
                self.coupon = coupon
                self.save()
                return True
        except Coupon.DoesNotExist:
            return False
        return False

    def remove_coupon(self):
        """Remove applied coupon"""
        self.coupon = None
        self.save()
        return True

    def get_discount_amount(self):
        """Calculate discount amount from coupon"""
        if not self.coupon:
            return 0
        return self.coupon.calculate_discount(self.subtotal)

    def get_final_total(self):
        """Get final total after all calculations"""
        return self.get_total_with_tax_and_shipping() - self.get_discount_amount()

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    def add_item(self, product, quantity=1, variant=None):
        if not self.is_active:
            raise ValueError("Cannot add items to inactive cart")
        
        if product.store != self.store:
            raise ValueError("Product does not belong to the cart's store")
        
        if variant and variant.product != product:
            raise ValueError("Variant does not belong to the product")
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return cart_item

    def remove_item(self, item_id):
        try:
            item = self.items.get(id=item_id)
            item.delete()
            return True
        except CartItem.DoesNotExist:
            return False

    def update_quantity(self, item_id, quantity):
        """Update the quantity of an item"""
        try:
            item = self.items.get(id=item_id)
            if quantity <= 0:
                item.delete()
                return True
            
            if item.variant:
                if item.variant.stock < quantity:
                    raise ValidationError("Not enough stock available")
            else:
                if item.product.stock < quantity:
                    raise ValidationError("Not enough stock available")
            
            item.quantity = quantity
            item.save()
            return True
        except CartItem.DoesNotExist:
            return False

    def clear(self):
        self.items.all().delete()

    @classmethod
    def get_or_create_cart(cls, user, store):
        """Get existing active cart for user and store, or create a new one"""
        # First, deactivate any existing active carts for this user and store
        cls.objects.filter(user=user, store=store, is_active=True).update(is_active=False)
        
        # Create a new active cart
        cart = cls.objects.create(
            user=user,
            store=store,
            is_active=True
        )
        return cart

    def save(self, *args, **kwargs):
        # Ensure only one active cart per user per store
        if self.is_active:
            Cart.objects.filter(
                user=self.user,
                store=self.store,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    is_saved_for_later = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'

    def __str__(self):
        variant_str = f" - {self.variant.name}" if self.variant else ""
        return f"{self.quantity}x {self.product.name}{variant_str} in {self.cart}"

    @property
    def unit_price(self):
        if self.variant:
            return self.variant.current_price
        return self.product.base_price

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def clean(self):
        # Check if product belongs to the same store as the cart
        if self.product.store != self.cart.store:
            raise ValidationError("Product must belong to the same store as the cart")
        
        if self.variant and self.variant.product != self.product:
            raise ValidationError("Variant must belong to the selected product")
        
        if self.variant and self.variant.stock < self.quantity:
            raise ValidationError("Not enough stock available for this variant")
        
        if not self.variant and self.product.stock < self.quantity:
            raise ValidationError("Not enough stock available")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs) 


class AbandonedCart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product)
    created_at = models.DateTimeField(auto_now_add=True)
    last_reminder = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Abandoned Cart for {self.user.username}"