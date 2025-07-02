import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from product.models import Product
from django.conf import settings
from django.utils import timezone

class Wishlist(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
     
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        pass

    def restore(self, user=None):
        pass
