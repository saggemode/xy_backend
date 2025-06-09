from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone  
from core.models import Product 
from django.db.models import Sum
from django.core.exceptions import ValidationError


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_items(self):
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    def add_item(self, product, quantity=1, size=None, color=None):
        """Add an item to the cart"""
        if not product.is_in_stock:
            raise ValidationError("Product is out of stock")

        if product.has_variants:
            if not size and not color:
                raise ValidationError("Variant product requires size or color")
            
            variant = product.get_variant(size=size, color=color)
            if not variant:
                raise ValidationError("Invalid variant combination")
            
            if variant.stock < quantity:
                raise ValidationError("Not enough stock available")
            
            cart_item, created = self.items.get_or_create(
                product=product,
                variant=variant,
                defaults={'quantity': quantity}
            )
        else:
            if product.stock < quantity:
                raise ValidationError("Not enough stock available")
            
            cart_item, created = self.items.get_or_create(
                product=product,
                defaults={'quantity': quantity}
            )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return cart_item

    def remove_item(self, item_id):
        """Remove an item from the cart"""
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
        """Remove all items from the cart"""
        self.items.all().delete()

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['cart', 'product', 'variant']

    def __str__(self):
        if self.variant:
            return f"{self.quantity}x {self.product.name} ({self.variant})"
        return f"{self.quantity}x {self.product.name}"

    @property
    def unit_price(self):
        if self.variant:
            return self.variant.price
        return self.product.base_price

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def clean(self):
        if self.variant and self.variant.product != self.product:
            raise ValidationError("Variant must belong to the selected product")
        
        if self.variant and self.variant.stock < self.quantity:
            raise ValidationError("Not enough stock available for this variant")
        
        if not self.variant and self.product.stock < self.quantity:
            raise ValidationError("Not enough stock available")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs) 