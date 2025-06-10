from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Avg, Min, Max, Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from datetime import datetime
import random
from decimal import Decimal
from store.models import Store





# Category model
class Category(models.Model):
    name = models.CharField()
    image_url = models.URLField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
    

class SubCategory(models.Model):
    name = models.CharField()
    image_url = models.URLField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.CASCADE)


    class Meta:
        unique_together = ('category', 'name')
        verbose_name_plural = 'Subcategories'

    def __str__(self):
        return f"{self.category.name} - {self.name}"
    

class Product(models.Model):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    image_urls = models.JSONField(default=list)  # List of image URLs
    stock = models.IntegerField()
    rating = models.FloatField(default=0.0)
    is_featured = models.BooleanField(default=False)
    has_variants = models.BooleanField(default=False)
    available_sizes = models.JSONField(default=list)   # List of strings like ["S", "M", "L"]
    available_colors = models.JSONField(default=list)  # List of strings like ["Red", "Blue"]
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")


    def __str__(self):
        return f"{self.name} - {self.store.name}"

    def clean(self):
        if not self.store.is_active:
            raise ValidationError("Cannot create product for inactive store")
        # Optional: Add check for store verification
        # if not self.store.is_verified:
        #     raise ValidationError("Store must be verified to create products")

    @property
    def rating(self):
        """Calculate the average rating for the product"""
        from django.db.models import Avg
        return self.reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0

    @property
    def review_count(self):
        """Get the total number of reviews for the product"""
        return self.reviews.count()

    @classmethod
    def create_product(cls, store, name, description, base_price, categories=None):
        if not store.is_active:
            raise ValidationError("Cannot create product for inactive store")
        if not store.owner.is_active:
            raise ValidationError("Store owner's account must be active")
        
        product = cls(
            store=store,
            name=name,
            description=description,
            base_price=base_price
        )
        product.full_clean()
        product.save()
        
        if categories:
            product.categories.set(categories)
        
        return product

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50, unique=True)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def current_price(self):
        return self.product.base_price + self.price_adjustment
    

class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='coupons')
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=1)
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional restrictions
    products = models.ManyToManyField(Product, blank=True, related_name='coupons')
    categories = models.ManyToManyField(Category, blank=True, related_name='coupons')
    users = models.ManyToManyField(User, blank=True, related_name='available_coupons')
    max_uses_per_user = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} - {self.store.name}"

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")
        
        if self.discount_type == 'percentage' and self.discount_value > 100:
            raise ValidationError("Percentage discount cannot exceed 100%")
        
        if self.max_discount_amount and self.discount_type == 'percentage':
            if self.max_discount_amount <= 0:
                raise ValidationError("Maximum discount amount must be greater than 0")

    @property
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            now >= self.start_date and
            now <= self.end_date and
            (self.usage_limit is None or self.usage_count < self.usage_limit)
        )

    def calculate_discount(self, cart_total, user=None):
        if not self.is_valid:
            return 0
        
        if user and self.users.exists() and user not in self.users.all():
            return 0
        
        if self.min_purchase_amount and cart_total < self.min_purchase_amount:
            return 0
        
        if self.discount_type == 'percentage':
            discount = (cart_total * self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        elif self.discount_type == 'fixed_amount':
            return min(self.discount_value, cart_total)
        elif self.discount_type == 'free_shipping':
            return 0  # Handle shipping discount separately
        
        return 0

    def apply(self, user):
        if not self.is_valid:
            raise ValidationError("Coupon is not valid")
        
        if user and self.users.exists() and user not in self.users.all():
            raise ValidationError("User is not eligible for this coupon")
        
        if self.usage_limit and self.usage_count >= self.usage_limit:
            raise ValidationError("Coupon usage limit reached")
        
        self.usage_count += 1
        self.save()

class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_usages')
    order = models.ForeignKey('order.Order', on_delete=models.CASCADE, related_name='coupon_usages')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.coupon.code} used by {self.user.username}"

class Bundle(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='bundles')
    name = models.CharField(max_length=100)
    description = models.TextField()
    products = models.ManyToManyField(Product, through='BundleItem')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.store.name}"

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    @property
    def total_original_price(self):
        return sum(item.product.base_price * item.quantity for item in self.items.all())

    @property
    def savings_amount(self):
        return self.total_original_price - self.price

    @property
    def savings_percentage(self):
        if self.total_original_price == 0:
            return 0
        return (self.savings_amount / self.total_original_price) * 100


class BundleItem(models.Model):
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ['bundle', 'product']

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.bundle.name}"

class Subscription(models.Model):
    SUBSCRIPTION_TYPES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='subscriptions')
    name = models.CharField(max_length=100)
    description = models.TextField()
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    products = models.ManyToManyField(Product, through='SubscriptionItem')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.store.name}"

class SubscriptionItem(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    frequency = models.PositiveIntegerField(default=1)  # How often to deliver (in days)

    class Meta:
        unique_together = ['subscription', 'product']

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.subscription.name}"

class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    next_delivery_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s subscription to {self.subscription.name}"

    def calculate_next_delivery(self):
        if self.subscription.subscription_type == 'monthly':
            return self.next_delivery_date + timezone.timedelta(days=30)
        elif self.subscription.subscription_type == 'quarterly':
            return self.next_delivery_date + timezone.timedelta(days=90)
        else:  # yearly
            return self.next_delivery_date + timezone.timedelta(days=365)
        
class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200)
    content = models.TextField()
    images = models.JSONField(default=list, blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    helpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"


class DynamicPricing(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    min_quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return f"Dynamic Pricing for {self.product.name}"
    


# GDPR Compliance Features
class GDPRCompliance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    data_downloaded = models.BooleanField(default=False)
    account_deleted = models.BooleanField(default=False)
    cookie_policy_viewed = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"GDPR Compliance for {self.user.username}"


# Loyalty Points System
class LoyaltyPoints(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    points = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Loyalty Points for {self.user.username}"

# Advanced Search & Filters
class SearchFilter(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    rating_min = models.FloatField(null=True, blank=True)
    color = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Search Filter for {self.product.name}"

# Auction System
class Auction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    start_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Auction for {self.product.name}"


# Loyalty Program
class LoyaltyProgram(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    points_per_purchase = models.PositiveIntegerField()
    points_redeemed = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Loyalty Program for {self.store.name}"



class FlashSale(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='flash_sales')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.name} - {self.store.name}"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")
        
        # Check if there's any overlap with other active flash sales for the same store
        overlapping_sales = FlashSale.objects.filter(
            store=self.store,
            is_active=True
        ).exclude(pk=self.pk).filter(
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        )
        
        if overlapping_sales.exists():
            raise ValidationError("This flash sale overlaps with another active flash sale")

    @property
    def is_currently_active(self):
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    @property
    def time_remaining(self):
        if not self.is_currently_active:
            return None
        return self.end_time - timezone.now()

    @property
    def total_discount(self):
        return sum(item.discount_amount for item in self.items.all())

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class FlashSaleItem(models.Model):
    flash_sale = models.ForeignKey(FlashSale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_available = models.PositiveIntegerField()
    quantity_sold = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['flash_sale', 'product', 'variant']

    def __str__(self):
        if self.variant:
            return f"{self.product.name} ({self.variant}) - {self.sale_price}"
        return f"{self.product.name} - {self.sale_price}"

    @property
    def discount_amount(self):
        return self.original_price - self.sale_price

    @property
    def discount_percentage(self):
        return (self.discount_amount / self.original_price) * 100

    @property
    def is_available(self):
        return (
            self.flash_sale.is_currently_active and
            self.quantity_available > self.quantity_sold
        )

    def clean(self):
        # Validate that the product belongs to the store
        if self.product.store != self.flash_sale.store:
            raise ValidationError("Product must belong to the same store as the flash sale")
        
        # Validate that the variant belongs to the product
        if self.variant and self.variant.product != self.product:
            raise ValidationError("Variant must belong to the selected product")
        
        # Validate sale price
        if self.sale_price >= self.original_price:
            raise ValidationError("Sale price must be less than original price")
        
        # Validate quantity
        if self.variant:
            if self.quantity_available > self.variant.stock:
                raise ValidationError("Quantity available cannot exceed variant stock")
        else:
            if self.quantity_available > self.product.stock:
                raise ValidationError("Quantity available cannot exceed product stock")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def create_flash_sale_item(cls, flash_sale, product, sale_price, quantity_available, variant=None):
        """Create a new flash sale item with validation"""
        if variant:
            original_price = variant.price
        else:
            original_price = product.base_price

        return cls.objects.create(
            flash_sale=flash_sale,
            product=product,
            variant=variant,
            original_price=original_price,
            sale_price=sale_price,
            quantity_available=quantity_available
        )

    def purchase(self, quantity=1):
        """Handle a purchase of this flash sale item"""
        if not self.is_available:
            raise ValidationError("Flash sale item is not available")
        
        if self.quantity_sold + quantity > self.quantity_available:
            raise ValidationError("Not enough quantity available")
        
        self.quantity_sold += quantity
        self.save()