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
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, default=None, related_name='created_cart_items')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, default=None, related_name='updated_cart_items')

    class Meta:
        verbose_name = _('Cart')
        verbose_name_plural = _('Carts')
        db_table = 'cart_cart'
        unique_together = ('user', 'store', 'product', 'variant')
        indexes = [
            models.Index(fields=['user', 'is_deleted']),
            models.Index(fields=['store', 'is_deleted']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} (Qty: {self.quantity})"

    def clean(self):
        """Validate cart item before saving"""
        if self.quantity <= 0:
            raise ValidationError(_('Quantity must be greater than 0'))
        
        # Check if product belongs to store
        if self.product.store != self.store:
            raise ValidationError(_('Product does not belong to the selected store'))
        
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
        """Override save to add audit fields and validation"""
        if not self.pk:  # New instance
            if not self.created_by:
                self.created_by = getattr(self, '_current_user', None)
        self.updated_by = getattr(self, '_current_user', None)
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

    def soft_delete(self, user=None):
        """Soft delete the cart item"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.updated_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_by'])

    def restore(self, user=None):
        """Restore soft deleted cart item"""
        self.is_deleted = False
        self.deleted_at = None
        self.updated_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_by'])

    @classmethod
    def get_user_cart(cls, user):
        """Get all active cart items for a user"""
        return cls.objects.filter(user=user, is_deleted=False)

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
        for item in cart_items:
            item.soft_delete(user=user)
