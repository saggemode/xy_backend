import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Avg, Min, Max, Sum, Count
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from datetime import datetime
import random
from decimal import Decimal
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

# Import bank models for payment integration
from bank.models import Wallet, XySaveAccount


class Store(models.Model): 
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending', _('Pending Review')),
        ('active', _('Active')),
        ('suspended', _('Suspended')),
        ('closed', _('Closed')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    
    # User fields for tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stores_created',
        help_text=_('User who created the store')
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stores_updated',
        help_text=_('User who last updated the store')
    )
    
    # Payment accounts for transfers
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stores',
        help_text=_('Store wallet for payment processing')
    )
     # Payment accounts for transfers
    xy_save_account = models.ForeignKey(
        XySaveAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_stores',
        help_text=_('XySave account for store payments')
    )

    name = models.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-_&.]+$',
                message=_('Store name can only contain letters, numbers, spaces, hyphens, underscores, ampersands, and periods.')
            )
        ],
        help_text=_('Store name (letters, numbers, spaces, hyphens, underscores, ampersands, periods only)')
    )
    description = models.TextField(
        blank=True,
        max_length=2000,
        help_text=_('Store description (max 2000 characters)')
    )
    location = models.CharField(
        max_length=255,
        help_text=_('Store location or address')
    )
    logo = models.URLField(
        max_length=500, 
        blank=True,
        validators=[URLValidator()],
        help_text=_('URL to store logo image')
    )
    cover_image = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        validators=[URLValidator()],
        help_text=_('URL to store cover image')
    )
    contact_email = models.EmailField(
        help_text=_('Primary contact email for the store')
    )
    phone_number = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[\+]?[1-9][\d]{0,15}$',
                message=_('Enter a valid phone number')
            )
        ],
        help_text=_('Contact phone number')
    )
    website_url = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        validators=[URLValidator()],
        help_text=_('Store website URL')
    )
    facebook_url = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        validators=[URLValidator()],
        help_text=_('Facebook page URL')
    )
    instagram_url = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        validators=[URLValidator()],
        help_text=_('Instagram profile URL')
    )
    twitter_url = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        validators=[URLValidator()],
        help_text=_('Twitter profile URL')
    )

    whatsapp_url = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        validators=[URLValidator()],
        help_text=_('Whatsapp profile URL')
    )
    
    # Status and verification
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text=_('Current status of the store')
    )
    is_verified = models.BooleanField(
        default=True,
        help_text=_('Whether the store has been verified by admin')
    )
    
    # Business settings
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=00.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Commission rate percentage (0-100)')
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Owner relationship
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_stores'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Store"
        verbose_name_plural = "Stores"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['owner']),
            models.Index(fields=['created_at']),
        ]

    def clean(self):
        """Custom validation for the store model."""
        super().clean()
        
        # Validate that at least one contact method is provided
        if not self.contact_email and not self.phone_number:
            raise ValidationError(_('At least one contact method (email or phone) is required.'))
        
        # Validate social media URLs are from correct platforms
        if self.facebook_url and 'facebook.com' not in self.facebook_url:
            raise ValidationError(_('Please provide a valid Facebook URL.'))
        
        if self.instagram_url and 'instagram.com' not in self.instagram_url:
            raise ValidationError(_('Please provide a valid Instagram URL.'))
        
        if self.twitter_url and 'twitter.com' not in self.twitter_url:
            raise ValidationError(_('Please provide a valid Twitter URL.'))

        # Ensure a user cannot own more than one store
        if self.owner:
            duplicate = Store.objects.filter(owner=self.owner).exclude(pk=self.pk).exists()
            if duplicate:
                raise ValidationError({'owner': _('You already have a store.')})

    def save(self, *args, **kwargs):
        """Override save to handle business logic and payment account linking."""
        self.full_clean()
        
        # Track whether this is a new store (no ID yet)
        is_new = not self.pk
        
        # Handle created_by and updated_by
        if 'created_by' in kwargs:
            self.created_by = kwargs.pop('created_by')
        if 'updated_by' in kwargs:
            self.updated_by = kwargs.pop('updated_by')
        
        super().save(*args, **kwargs)
        
        # After saving, link the owner's payment accounts if available and missing on the store
        # This runs on creation and on subsequent saves if links are still empty
        if self.owner and (not self.wallet or not self.xy_save_account):
            try:
                # Try to link owner's wallet if not already linked
                if not self.wallet:
                    wallet = Wallet.objects.filter(user=self.owner).first()
                    if wallet:
                        self.wallet = wallet
                        # Save again but skip the is_new check to avoid infinite recursion
                        super().save(update_fields=['wallet'])
                
                # Try to link owner's XySave account if not already linked
                if not self.xy_save_account:
                    xy_save = XySaveAccount.objects.filter(user=self.owner).first()
                    if xy_save:
                        self.xy_save_account = xy_save
                        # Save again but skip the is_new check to avoid infinite recursion
                        super().save(update_fields=['xy_save_account'])
            except Exception as e:
                # Log the error but don't prevent store creation
                print(f"Error linking payment accounts: {e}")

    # Business Logic Methods
    def activate(self, user=None):
        """Activate the store."""
        self.status = 'active'
        self.save()

    def deactivate(self, user=None):
        """Deactivate the store."""
        self.status = 'suspended'
        self.save()

    def verify(self, user=None):
        """Verify the store."""
        self.is_verified = True
        self.save()

    def close(self, user=None):
        """Close the store permanently."""
        self.status = 'closed'
        self.save()

    def soft_delete(self, user=None):
        """Soft delete the store."""
        pass

    def restore(self, user=None):
        """Restore the store."""
        pass

    @property
    def total_products(self):
        """Get total number of products for this store."""
        return self.products.count()

    @property
    def active_products(self):
        """Get number of active products for this store."""
        return self.products.filter(status='published').count()

    @property
    def total_staff(self):
        """Get total number of active staff for this store."""
        return self.staff_members.filter(is_active=True).count()

    def is_operational(self):
        """Check if store is operational (active and verified)."""
        return self.status == 'active' and self.is_verified
        
    def has_payment_account(self):
        """Check if store has at least one payment account linked."""
        return bool(self.wallet or self.xy_save_account)
    
    def get_primary_payment_account(self):
        """Get the primary payment account for this store.
        Returns the wallet first if available, otherwise the XySave account.
        """
        return self.wallet or self.xy_save_account
        
    def get_payment_account_number(self):
        """Get the account number of the primary payment account."""
        account = self.get_primary_payment_account()
        if account:
            return account.account_number
        return None
        
    def process_payment_from_user(self, user, amount, description=None):
        """Process a payment from a user to this store.
        
        Args:
            user: The user making the payment
            amount: The payment amount (Money object)
            description: Optional description for the transaction
            
        Returns:
            tuple: (success, message, transaction_reference)
        """
        if not self.has_payment_account():
            return False, "Store has no payment account configured", None
            
        if not self.is_operational():
            return False, "Store is not operational", None
            
        # Get store's payment account
        store_account = self.get_primary_payment_account()
        
        try:
            # Import transaction service
            from bank.transaction_services import TransactionService
            
            # Create transaction service
            tx_service = TransactionService()
            
            # Process the transfer
            if isinstance(store_account, Wallet):
                # Transfer to store wallet
                result = tx_service.transfer_to_wallet(
                    user=user,
                    recipient_wallet=store_account,
                    amount=amount,
                    description=description or f"Payment to {self.name}"
                )
            else:
                # Transfer to store XySave account
                result = tx_service.transfer_to_xysave(
                    user=user,
                    recipient_xysave=store_account,
                    amount=amount,
                    description=description or f"Payment to {self.name}"
                )
                
            if result.get('success'):
                return True, "Payment processed successfully", result.get('reference')
            else:
                return False, result.get('message', "Payment failed"), None
                
        except Exception as e:
            return False, f"Payment processing error: {str(e)}", None


class StoreStaff(models.Model):
    class Roles(models.TextChoices):
        OWNER = 'owner', _('Owner')
        MANAGER = 'manager', _('Manager')
        STAFF = 'staff', _('Staff')
        ADMIN = 'admin', _('Administrator')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    
    store = models.ForeignKey(
        Store, 
        on_delete=models.CASCADE,
        related_name='staff_members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='store_roles'
    )
    role = models.CharField(
        max_length=50, 
        choices=Roles.choices, 
        default=Roles.STAFF,
        help_text=_('Role of the staff member in the store')
    )
    can_manage_products = models.BooleanField(
        default=False,
        help_text=_('Can manage store products')
    )
    can_manage_orders = models.BooleanField(
        default=False,
        help_text=_('Can manage store orders')
    )
    can_manage_staff = models.BooleanField(
        default=False,
        help_text=_('Can manage other staff members')
    )
    can_view_analytics = models.BooleanField(
        default=False,
        help_text=_('Can view store analytics')
    )
    
    # Status field
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether the staff member is active')
    )
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('store', 'user')
        verbose_name = "Store Staff"
        verbose_name_plural = "Store Staff"
        indexes = [
            models.Index(fields=['store', 'role']),
            models.Index(fields=['user', 'role']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} at {self.store.name}"

    def clean(self):
        """Custom validation for staff model."""
        super().clean()
        
        # Ensure only one owner per store
        if self.role == self.Roles.OWNER:
            existing_owner = StoreStaff.objects.filter(
                store=self.store,
                role=self.Roles.OWNER,
                is_active=True
            ).exclude(pk=self.pk)
            
            if existing_owner.exists():
                raise ValidationError(_('A store can only have one owner.'))

    def save(self, *args, **kwargs):
        """Override save to handle business logic."""
        # Set permissions based on role
        if self.role == self.Roles.OWNER:
            self.can_manage_products = True
            self.can_manage_orders = True
            self.can_manage_staff = True
            self.can_view_analytics = True
        elif self.role == self.Roles.MANAGER:
            self.can_manage_products = True
            self.can_manage_orders = True
            self.can_manage_staff = False
            self.can_view_analytics = True
        elif self.role == self.Roles.ADMIN:
            self.can_manage_products = True
            self.can_manage_orders = True
            self.can_manage_staff = True
            self.can_view_analytics = True
        else:  # STAFF
            self.can_manage_products = False
            self.can_manage_orders = False
            self.can_manage_staff = False
            self.can_view_analytics = False
        
        super().save(*args, **kwargs)

    @staticmethod
    def is_owner(user, store):
        """Check if user is owner of the store."""
        return StoreStaff.objects.filter(
            user=user, 
            store=store, 
            role=StoreStaff.Roles.OWNER, 
            is_active=True
        ).exists()

    @staticmethod
    def is_manager(user, store):
        """Check if user is manager of the store."""
        return StoreStaff.objects.filter(
            user=user, 
            store=store, 
            role__in=[StoreStaff.Roles.OWNER, StoreStaff.Roles.MANAGER], 
            is_active=True
        ).exists()

    @staticmethod
    def is_staff_member(user, store):
        """Check if user is any staff member of the store."""
        return StoreStaff.objects.filter(
            user=user, 
            store=store, 
            is_active=True
        ).exists()

    def soft_delete(self, user=None):
        """Soft delete the staff member."""
        pass

    def update_last_active(self):
        """Update last active timestamp."""
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])

    def has_permission(self, permission):
        """Check if staff member has specific permission."""
        permission_map = {
            'manage_products': self.can_manage_products,
            'manage_orders': self.can_manage_orders,
            'manage_staff': self.can_manage_staff,
            'view_analytics': self.can_view_analytics,
        }
        return permission_map.get(permission, False)

# Customer Lifetime Value (CLTV) Calculation
class CustomerLifetimeValue(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
     
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='customer_lifetime_value'
    )
    total_spent = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0)]
    )
    first_purchase_date = models.DateTimeField(null=True, blank=True)
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    average_order_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0)]
    )
    purchase_frequency = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0)]
    )
    total_orders = models.PositiveIntegerField(default=0)
    customer_since = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer Lifetime Value"
        verbose_name_plural = "Customer Lifetime Values"
        indexes = [
            models.Index(fields=['total_spent']),
            models.Index(fields=['last_purchase_date']),
        ]

    def __str__(self):
        return f"CLTV for {self.user.username}"

    def calculate_cltv(self):
        """Calculate customer lifetime value."""
        if self.total_orders > 0:
            self.average_order_value = self.total_spent / self.total_orders
            # Calculate purchase frequency (orders per month)
            if self.first_purchase_date and self.last_purchase_date:
                months_diff = (self.last_purchase_date - self.first_purchase_date).days / 30
                if months_diff > 0:
                    self.purchase_frequency = self.total_orders / months_diff
        self.save()

# Store Analytics Enhancements
class StoreAnalytics(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )
    store = models.OneToOneField(
        Store, 
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # View and engagement metrics
    total_views = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)
    page_views = models.PositiveIntegerField(default=0)
    
    # Sales metrics
    total_sales = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0)]
    )
    total_orders = models.PositiveIntegerField(default=0)
    average_order_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0)]
    )
    
    # Conversion metrics
    conversion_rate = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    bounce_rate = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Product metrics
    total_products = models.PositiveIntegerField(default=0)
    active_products = models.PositiveIntegerField(default=0)
    top_selling_products = models.JSONField(default=list)
    
    # Customer metrics
    total_customers = models.PositiveIntegerField(default=0)
    repeat_customers = models.PositiveIntegerField(default=0)
    customer_retention_rate = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    calculated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Store Analytics"
        verbose_name_plural = "Store Analytics"
        indexes = [
            models.Index(fields=['revenue']),
            models.Index(fields=['total_sales']),
            models.Index(fields=['conversion_rate']),
        ]

    def __str__(self):
        return f"Analytics for {self.store.name}"

    def calculate_analytics(self):
        """Calculate all analytics metrics."""
        try:
            from order.models import Order, OrderItem
            
            # Get store orders
            store_orders = Order.objects.filter(
                items__product__store=self.store,
                status__in=['completed', 'delivered']
            ).distinct()
            
            # Calculate sales metrics
            self.total_orders = store_orders.count()
            self.revenue = store_orders.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            
            if self.total_orders > 0:
                self.average_order_value = self.revenue / self.total_orders
            
            # Calculate conversion rate
            if self.total_views > 0:
                self.conversion_rate = (self.total_orders / self.total_views) * 100
            
            # Calculate customer metrics
            unique_customers = store_orders.values('customer').distinct().count()
            self.total_customers = unique_customers
            
            # Calculate repeat customers
            customer_order_counts = store_orders.values('customer').annotate(
                order_count=Count('id')
            )
            self.repeat_customers = customer_order_counts.filter(order_count__gt=1).count()
            
            if self.total_customers > 0:
                self.customer_retention_rate = (self.repeat_customers / self.total_customers) * 100
                
        except ImportError:
            # Order models not available, set default values
            self.total_orders = 0
            self.revenue = 0
            self.average_order_value = 0
            self.conversion_rate = 0
            self.total_customers = 0
            self.repeat_customers = 0
            self.customer_retention_rate = 0
        except Exception as e:
            # Handle any other errors gracefully
            print(f"Error calculating analytics: {e}")
            self.total_orders = 0
            self.revenue = 0
            self.average_order_value = 0
            self.conversion_rate = 0
            self.total_customers = 0
            self.repeat_customers = 0
            self.customer_retention_rate = 0
        
        # Update product counts
        self.total_products = self.store.total_products
        self.active_products = self.store.active_products
        
        self.calculated_at = timezone.now()
        self.save()

    def update_views(self, count=1):
        """Update view count."""
        self.total_views += count
        self.save(update_fields=['total_views', 'last_updated'])

    def update_unique_visitors(self, count=1):
        """Update unique visitor count."""
        self.unique_visitors += count
        self.save(update_fields=['unique_visitors', 'last_updated'])