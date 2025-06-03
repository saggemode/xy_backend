from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Avg, Min, Max, Sum

# User Profile model
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'core'

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Transaction model for sending/receiving money
class Transaction(models.Model):
    sender = models.ForeignKey(User, related_name='sent_transactions', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"{self.sender.username} to {self.receiver.username}: {self.amount}"

# Social Media Post model
class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(default='')
    image = models.JSONField(blank=True, default=list)
    video = models.JSONField(blank=True, default=list)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.author.username}'s Post: {self.content[:50]}"

# E-commerce Store model
class Store(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(default='')
    location = models.TextField(default='')
    logo = models.URLField(blank=False)
    cover_image = models.URLField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    # is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# Category model
class Category(models.Model):
    name = models.CharField(max_length=100)
    imageUrl = models.URLField(blank=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    image_url = models.URLField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('category', 'name')
        verbose_name_plural = 'Subcategories'

    def __str__(self):
        return f"{self.category.name} - {self.name}"

# Coupon model
class Coupon(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percent'), ('amount', 'Amount'), ('fixed', 'Fixed')], default='amount')
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.PositiveIntegerField(default=1)
    times_used = models.PositiveIntegerField(default=0)
    users_used = models.ManyToManyField(User, related_name='used_coupons', blank=True)
    valid_from = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional restrictions
    restricted_users = models.ManyToManyField(User, related_name='restricted_coupons', blank=True)
    restricted_products = models.ManyToManyField('Product', related_name='restricted_coupons', blank=True)
    restricted_categories = models.ManyToManyField('Category', related_name='restricted_coupons', blank=True)
    max_uses_per_user = models.PositiveIntegerField(default=1)

    def is_valid(self):
        now = timezone.now()
        return (
            self.active and 
            now >= self.valid_from and 
            now < self.expires_at and 
            self.times_used < self.max_uses
        )

    def can_be_used_by(self, user):
        if self.restricted_users.exists() and user not in self.restricted_users.all():
            return False
        return self.users_used.filter(id=user.id).count() < self.max_uses_per_user

    def apply_discount(self, amount):
        if self.discount_type == 'percent':
            discount = amount * (self.value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        elif self.discount_type == 'fixed':
            return min(self.value, amount)
        else:  # amount type
            return min(self.value, amount)

    def __str__(self):
        return f"{self.code} - {self.store.name}"

# Product model
class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(default='')
    image_urls = models.JSONField(
        help_text="List of image URLs",
        default=list
    )
    
    stock = models.PositiveIntegerField(default=0)
    rating = models.FloatField(default=1.0)
    is_featured = models.BooleanField(default=False)
    
    has_variants = models.BooleanField(default=False)
    available_sizes = models.JSONField(blank=True, null=True, help_text="e.g. ['S', 'M', 'L']")
    available_colors = models.JSONField(blank=True, null=True, help_text="e.g. ['Red', 'Blue']")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['store', 'name']

    def __str__(self):
        return f"{self.name} ({self.store})"

    def clean(self):
        if self.subcategory and self.category and self.subcategory.category != self.category:
            raise ValidationError("Subcategory must belong to the selected category")
        
        if self.has_variants:
            if not self.available_sizes and not self.available_colors:
                raise ValidationError("Products with variants must have at least one size or color option")
            
            # Validate that all variants have required attributes
            for variant in self.variants.all():
                if not variant.size and not variant.color:
                    raise ValidationError(f"Variant {variant} must have at least one of size or color")
                
                if variant.size and self.available_sizes and variant.size not in self.available_sizes:
                    raise ValidationError(f"Invalid size '{variant.size}' for variant {variant}")
                
                if variant.color and self.available_colors and variant.color not in self.available_colors:
                    raise ValidationError(f"Invalid color '{variant.color}' for variant {variant}")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def average_rating(self):
        return self.reviews.aggregate(avg=Avg('rating'))['avg'] or self.rating

    @property
    def min_price(self):
        if self.has_variants:
            return self.variants.aggregate(min_price=Min('price'))['min_price'] or self.base_price
        return self.base_price

    @property
    def max_price(self):
        if self.has_variants:
            return self.variants.aggregate(max_price=Max('price'))['max_price'] or self.base_price
        return self.base_price

    @property
    def total_stock(self):
        if self.has_variants:
            return self.variants.aggregate(total=Sum('stock'))['total'] or 0
        return self.stock

    @property
    def is_in_stock(self):
        if self.has_variants:
            return self.variants.filter(stock__gt=0).exists()
        return self.stock > 0

    @property
    def available_variants(self):
        if not self.has_variants:
            return []
        return self.variants.filter(is_active=True, stock__gt=0)

    def get_variant(self, size=None, color=None):
        """Get a specific variant by size and/or color"""
        if not self.has_variants:
            return None
        
        filters = {'is_active': True}
        if size:
            filters['size'] = size
        if color:
            filters['color'] = color
            
        return self.variants.filter(**filters).first()

    def create_variant(self, size=None, color=None, price=None, stock=0, sku=None):
        """Create a new variant for this product"""
        if not self.has_variants:
            raise ValidationError("Cannot create variants for a product that doesn't support variants")
        
        if not size and not color:
            raise ValidationError("Variant must have at least one of size or color")
        
        if size and self.available_sizes and size not in self.available_sizes:
            raise ValidationError(f"Invalid size '{size}'")
        
        if color and self.available_colors and color not in self.available_colors:
            raise ValidationError(f"Invalid color '{color}'")
        
        return self.variants.create(
            size=size,
            color=color,
            price=price or self.base_price,
            stock=stock,
            sku=sku or f"{self.name}-{size or ''}-{color or ''}".strip()
        )

        # Product Variants



class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.PositiveIntegerField(default=0)
    image_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    size = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        ordering = ['size', 'color']

    def __str__(self):
        variant_parts = []
        if self.size:
            variant_parts.append(self.size)
        if self.color:
            variant_parts.append(self.color)
        return f"{self.product.name} - {' '.join(variant_parts)}".strip()

    def clean(self):
        if not self.product.has_variants:
            raise ValidationError("Cannot create variants for a product that doesn't support variants")
        if not self.size and not self.color:
            raise ValidationError("Variant must have at least one of size or color")
        if self.size and self.product.available_sizes and self.size not in self.product.available_sizes:
            raise ValidationError("Invalid size for this product")
        if self.color and self.product.available_colors and self.color not in self.product.available_colors:
            raise ValidationError("Invalid color for this product")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# Review model
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)], default=1)
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField(blank=True)
    images = models.JSONField(blank=True, null=True, help_text="List of image URLs", default=list)
    is_verified_purchase = models.BooleanField(default=False)
    helpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product rating
        self.product.rating = self.product.average_rating()
        self.product.save(update_fields=['rating'])

# Order model
class Order(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order by {self.buyer.username} from {self.store.name}"

# OrderItem model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"

# Report model
class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    reason = models.TextField(default='')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report by {self.reporter.username} on {self.store.name}"

class UserVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True)
    token_expires = models.DateTimeField(null=True)

    def __str__(self):
        return f"Verification for {self.user.username}"

# Two-Factor Authentication (2FA)
class TwoFactorAuth(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=False)
    secret_key = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return f"2FA for {self.user.username}"

# Role-Based Access Control (RBAC)
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField('auth.Permission')

    def __str__(self):
        return self.name

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

# Passwordless Login / Magic Links
class MagicLink(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Magic Link for {self.user.username}"

# Login History
class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    device = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} logged in from {self.ip_address}"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Wishlist"

class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s address in {self.city}"

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id} for Order {self.order.id}"

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

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} likes {self.post}"

class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    store = models.ForeignKey(Store, related_name='followers', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'store')

    def __str__(self):
        return f"{self.follower.username} follows {self.store.name}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=50)
    related_id = models.PositiveIntegerField()  # ID of related object
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"

class SystemSettings(models.Model):
    maintenance_mode = models.BooleanField(default=False)
    currency = models.CharField(max_length=3, default='USD')
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"System Settings (Currency: {self.currency})"

# Multi-Currency Support
class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=100)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

# Subscription Plans
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.PositiveIntegerField()  # in days
    features = models.JSONField()

    def __str__(self):
        return self.name

# Advanced Analytics
class Analytics(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    date = models.DateField()
    views = models.PositiveIntegerField(default=0)
    sales = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    def __str__(self):
        return f"Analytics for {self.store.name} on {self.date}"

# Automated Refunds
class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund for Order {self.order.id}"

# Fraud Detection
class FraudDetection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    risk_score = models.FloatField()
    is_fraudulent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fraud Detection for {self.user.username}"

# Loyalty Program
class LoyaltyProgram(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    points_per_purchase = models.PositiveIntegerField()
    points_redeemed = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Loyalty Program for {self.store.name}"

# Auction System
class Auction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    start_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Auction for {self.product.name}"

# Advanced Search
class SearchIndex(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    search_vector = models.TextField()

    def __str__(self):
        return f"Search Index for {self.product.name}"

# Real-Time Notifications
class RealTimeNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}"

# API Rate Limiting
class RateLimit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    endpoint = models.CharField(max_length=100)
    requests = models.PositiveIntegerField(default=0)
    last_request = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rate Limit for {self.user.username} on {self.endpoint}"

# Multi-Language Support
class Language(models.Model):
    code = models.CharField(max_length=5, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# Advanced Reporting
class Report(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=50)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.user.username}"

# Social Sharing
class SocialShare(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    platform = models.CharField(max_length=50)
    shared_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} shared {self.product.name} on {self.platform}"

# Advanced Security
class SecurityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Security Log for {self.user.username}"

# Integration with External Services
class ExternalService(models.Model):
    name = models.CharField(max_length=100)
    api_key = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# GDPR Compliance Features
class GDPRCompliance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    data_downloaded = models.BooleanField(default=False)
    account_deleted = models.BooleanField(default=False)
    cookie_policy_viewed = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"GDPR Compliance for {self.user.username}"

# Inventory Management System
class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    last_restock_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Inventory for {self.product.name}"


# Dynamic Pricing or Discounts
class DynamicPricing(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    min_quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return f"Dynamic Pricing for {self.product.name}"

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

# Abandoned Cart Recovery
class AbandonedCart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product)
    created_at = models.DateTimeField(auto_now_add=True)
    last_reminder = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Abandoned Cart for {self.user.username}"

# User Behavior Tracking
class UserBehavior(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    page_viewed = models.CharField(max_length=255)
    product_clicked = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    cart_added = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='cart_additions')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Behavior for {self.user.username}"

# Sales Reports & Dashboards
class SalesReport(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    date = models.DateField()
    total_sales = models.DecimalField(max_digits=12, decimal_places=2)
    total_orders = models.PositiveIntegerField()
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Sales Report for {self.store.name} on {self.date}"

# Group Chat
class Group(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(User, related_name='chat_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Private Messaging System
class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    group = models.ForeignKey(Group, related_name='messages', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, default='sent')  # sent, delivered, read
    content = models.TextField()
    image = models.ImageField(upload_to='message_images/', null=True, blank=True)
    video = models.FileField(upload_to='message_videos/', null=True, blank=True)
    file = models.FileField(upload_to='message_files/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"

# Post Sharing / Re-posts
class Repost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_post = models.ForeignKey(Post, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} reposted {self.original_post}"

# Hashtags and Mentions
class Hashtag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    posts = models.ManyToManyField(Post, related_name='hashtags')

    def __str__(self):
        return self.name

class Mention(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} mentioned in {self.post}"