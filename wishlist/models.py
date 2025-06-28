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
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, default=None, related_name='created_wishlist_items')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, default=None, related_name='updated_wishlist_items')

    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
        unique_together = ('user', 'product')
        db_table = 'wishlist_wishlist'
        managed = True

    def __str__(self):
        return f"{self.user.username}'s wishlist - {self.product.name}"

    def save(self, *args, **kwargs):
        user = getattr(self, '_current_user', None)
        if not self.pk and not self.created_by and user:
            self.created_by = user
        if user:
            self.updated_by = user
        self.full_clean()
        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        if not self.is_deleted:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            if user:
                self.updated_by = user
            self.save(update_fields=['is_deleted', 'deleted_at', 'updated_by'])

    def restore(self, user=None):
        if self.is_deleted:
            self.is_deleted = False
            self.deleted_at = None
            if user:
                self.updated_by = user
            self.save(update_fields=['is_deleted', 'deleted_at', 'updated_by'])
