from django.db import models
from django.contrib.auth.models import User 
from core.models import Product

class Wishlist(models.Model):
    userId = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    product = models.ManyToManyField(Product, related_name='wishlists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'

    def __str__(self):
        return f"{self.userId.username}'s Wishlist" if self.userId else "Wishlist"
