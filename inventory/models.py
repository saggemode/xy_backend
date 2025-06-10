from django.db import models
from django.core.exceptions import ValidationError
from product.models import Product, ProductVariant

class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='inventory', null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} in stock"

    def update_stock(self, quantity_change):
        """Update stock quantity and handle low stock alerts"""
        self.quantity += quantity_change
        if self.quantity < 0:
            raise ValidationError("Cannot reduce stock below 0")
        self.save()
        
        if self.quantity <= self.low_stock_threshold:
            # TODO: Implement low stock notification
            pass
