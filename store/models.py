from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Avg, Min, Max, Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from datetime import datetime
import random
from decimal import Decimal

# E-commerce Store model
from django.db import models
from django.conf import settings

class Store(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    logo = models.URLField(max_length=500, blank=True)
    cover_image = models.URLField(max_length=500, blank=True, null=True)
    contact_email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    website_url = models.URLField(max_length=500, blank=True, null=True)
    facebook_url = models.URLField(max_length=500, blank=True, null=True)
    instagram_url = models.URLField(max_length=500, blank=True, null=True)
    twitter_url = models.URLField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stores'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Store"
        verbose_name_plural = "Stores"
        ordering = ['-created_at']


class StoreStaff(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)  # owner, manager, staff
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.role} at {self.store.name}"

# Customer Lifetime Value (CLTV) Calculation
class CustomerLifetimeValue(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    first_purchase_date = models.DateTimeField(null=True, blank=True)
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    purchase_frequency = models.FloatField(default=0.0)

    def __str__(self):
        return f"CLTV for {self.user.username}"

# Store Analytics Enhancements
class StoreAnalytics(models.Model):
    store = models.OneToOneField(Store, on_delete=models.CASCADE)
    total_views = models.PositiveIntegerField(default=0)
    total_sales = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    conversion_rate = models.FloatField(default=0.0)
    bounce_rate = models.FloatField(default=0.0)
    top_selling_products = models.JSONField(default=list)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analytics for {self.store.name}"