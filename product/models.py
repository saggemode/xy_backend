import uuid
from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Avg, Min, Max, Sum, Count
from django.db.models.functions import Coalesce
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from datetime import datetime
import random
from decimal import Decimal
from store.models import Store
import secrets
from django.utils.text import slugify

# Category model
class Category(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    name = models.CharField()
    image_url = models.URLField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
    

class SubCategory(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
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
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    image_urls = models.JSONField(default=list)  # List of image URLs
    stock = models.PositiveIntegerField()
    sku = models.CharField(max_length=100, unique=True, blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True, allow_unicode=True)
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )

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
        if self.discount_price and self.discount_price >= self.base_price:
            raise ValidationError("Discount price must be less than the base price.")
        if not self.store.is_active:
            raise ValidationError("Cannot create product for inactive store")
        if not self.store.is_verified:
            raise ValidationError("Store must be verified to create products")

    def _generate_unique_slug(self):
        """
        Generates a unique slug by combining the store and product names.
        If a slug with the same name already exists, appends a counter.
        e.g., "my-store-classic-t-shirt-2"
        """
        if self.slug: # If slug is already set, do nothing.
             return self.slug

        store_slug = slugify(self.store.name, allow_unicode=True) if self.store else 'no-store'
        product_slug = slugify(self.name, allow_unicode=True) or 'product'
        base_slug = f"{store_slug}-{product_slug}"
        
        slug = base_slug
        counter = 1
        # Append a counter until the slug is unique
        while Product.objects.filter(slug=slug).exclude(id=self.id).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"sku-{uuid.uuid4().hex[:8].upper()}"
        
        if not self.slug:
            self.slug = self._generate_unique_slug()
        
        super().save(*args, **kwargs)

    @property
    def on_sale(self):
        return self.discount_price is not None and self.discount_price < self.base_price

    @property
    def current_price(self):
        return self.discount_price if self.on_sale else self.base_price

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
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50, unique=True, blank=True)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    def _generate_sku(self):
        """Generate a unique SKU."""
        # Get the first 3 letters of product and variant name, or as many as available
        product_prefix = self.product.name[:3].upper()
        variant_prefix = self.name[:3].upper()
        # Generate a random 6-character hex string
        random_suffix = secrets.token_hex(3).upper()
        
        sku = f"{product_prefix}-{variant_prefix}-{random_suffix}"
        
        # Ensure the SKU is unique
        while ProductVariant.objects.filter(sku=sku).exists():
            random_suffix = secrets.token_hex(3).upper()
            sku = f"{product_prefix}-{variant_prefix}-{random_suffix}"
            
        return sku

    def save(self, *args, **kwargs):
        """Override save to generate SKU if it's not set."""
        if not self.sku:
            self.sku = self._generate_sku()
        super().save(*args, **kwargs)

    @property
    def current_price(self):
        return self.product.base_price + self.price_adjustment

class ProductReview(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']
        verbose_name = _('Product Review')
        verbose_name_plural = _('Product Reviews')

    def __str__(self):
        return f'Review for {self.product.name} by {self.user.username}'

class Coupon(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
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
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_usages')
    order = models.ForeignKey('order.Order', on_delete=models.CASCADE, related_name='coupon_usages')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.coupon.code} used by {self.user.username}"
 
class FlashSale(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
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
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
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