from django.db import models
from django.contrib.auth.models import User
from product.models import Product
from store.models import Store

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId_id')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, db_column='storeId_id')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='productId_id')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        unique_together = ('user', 'store', 'product')
        db_table = 'cart_cart'
        managed = True

    def __str__(self):
        return f"{self.user.username}'s cart - {self.store.name} - {self.product.name}"

    @property
    def total_price(self):
        """Calculate the total price for this cart item"""
        return self.product.price * self.quantity

    def save(self, *args, **kwargs):
        """Override save to ensure quantity is at least 1"""
        if self.quantity < 1:
            self.quantity = 1
        super().save(*args, **kwargs)
