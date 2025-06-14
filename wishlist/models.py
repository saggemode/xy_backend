from django.db import models
from django.contrib.auth.models import User
from product.models import Product

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='userId_id')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
        unique_together = ('user', 'product')
        db_table = 'wishlist_wishlist'
        managed = True

    def __str__(self):
        return f"{self.user.username}'s wishlist - {self.product.name}"
