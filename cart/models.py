import uuid
from django.db import models
from django.conf import settings
from product.models import Product, ProductVariant
from store.models import Store
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from django.utils.translation import gettext_lazy as _

class Cart(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
 
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='userId_id')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column='storeId_id')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productId_id')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, db_column='variantId_id')
    quantity = models.PositiveIntegerField(default=1)
    selected_size = models.CharField(max_length=10, null=True, blank=True)
    selected_color = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Cart')
        verbose_name_plural = _('Carts')
        db_table = 'cart_cart'
        unique_together = ('user', 'store', 'product', 'variant')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['store']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        try:
            user_name = self.user.username if self.user else "Unknown User"
            product_name = self.product.name if self.product else "Unknown Product"
            return f"{user_name} - {product_name} (Qty: {self.quantity})"
        except Exception:
            return f"Cart Item {self.id}"

    def clean(self):
        """Validate cart item before saving"""
        if self.quantity <= 0:
            raise ValidationError(_('Quantity must be greater than 0'))
        
        # Check if product belongs to store
        if self.product.store != self.store:
            raise ValidationError(_('Product does not belong to the selected store'))
        
        # Prevent users from adding their own products to cart
        if self.product.store.owner == self.user:
            raise ValidationError(_('You cannot add your own products to your cart'))
        
        # Check if variant belongs to product
        if self.variant and self.variant.product != self.product:
            raise ValidationError(_('Variant does not belong to the selected product'))
        
        # Check stock availability
        if self.variant:
            if self.quantity > self.variant.stock:
                raise ValidationError(_('Insufficient stock for selected variant'))
        else:
            if self.quantity > self.product.stock:
                raise ValidationError(_('Insufficient stock for product'))

    def save(self, *args, **kwargs):
        """Override save to add validation"""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def unit_price(self):
        """Get unit price from variant or product"""
        if self.variant:
            return self.variant.current_price
        return self.product.current_price

    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return self.unit_price * self.quantity



    @classmethod
    def get_user_cart(cls, user):
        """Get all cart items for a user"""
        return cls.objects.filter(user=user)

    @classmethod
    def get_cart_total(cls, user):
        """Calculate total price for user's cart"""
        cart_items = cls.get_user_cart(user)
        return sum(item.total_price for item in cart_items)

    @classmethod
    def get_cart_count(cls, user):
        """Get total quantity of items in user's cart"""
        cart_items = cls.get_user_cart(user)
        return sum(item.quantity for item in cart_items)

    @classmethod
    def clear_user_cart(cls, user):
        """Clear all items from user's cart"""
        cart_items = cls.get_user_cart(user)
        cart_items.delete()
