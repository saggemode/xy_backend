import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Create your models here.

class ShippingAddress(models.Model):

    class AddressType(models.TextChoices):
        HOME = 'home', _('Home')
        OFFICE = 'office', _('Office')
        SCHOOL = 'school', _('School')
        MARKET = 'market', _('Market')
        OTHER = 'other', _('Other')
        BUSINESS = 'business', _('Business')
        MAILING = 'mailing', _('Mailing')

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    )

    # User relationship
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shipping_addresses',
        help_text="The user this shipping address belongs to"
    )

    # Address details
   
    address = models.CharField(
        max_length=255,
        verbose_name=_('Address'),
        help_text=_('Full address including street, city, state, and postal code')
    )

    city = models.CharField(
        max_length=100,
        verbose_name=_('City'),
        help_text=_('City name')
    )
    state = models.CharField(
       
        max_length=100,
        verbose_name=_('State'),
        help_text="State, province, or region"
    )
    country = models.CharField(
       max_length=100,
        verbose_name=_('Country'),
        help_text="Country"
    )
    postal_code = models.CharField(
        max_length=20,
        verbose_name=_('Postal Code'),
        help_text=_('Postal or ZIP code'),
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9\s\-]+$',
                message=_('Enter a valid postal code')
            )
        ]
    )
    phone = models.CharField(
       max_length=100,
        verbose_name=_('Phone'),
        help_text="Phone"
    )
    additional_phone = models.CharField(
       max_length=100,
        verbose_name=_('Additional phone '),
        help_text="Additional phone"
    )

    # Address status
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Default Address'),
        help_text=_('Whether this is the user\'s default address')
    )

    # Address type
    address_type = models.CharField(
        max_length=10,
        choices=AddressType.choices,
        default=AddressType.HOME,
        verbose_name=_('Address Type'),
        help_text=_('Type of address (home, office, etc.)')
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this address was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this address was last updated"
    )

    class Meta:
        verbose_name = "Shipping Address"
        verbose_name_plural = "Shipping Addresses"
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        """Return a string representation of the address"""
        parts = []
        
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.country:
            parts.append(self.country)
            
        return ", ".join(parts) if parts else f"Shipping Address {self.id}"

    def save(self, *args, **kwargs):
        """Override save to handle default address logic"""
        # If this is the user's first address, make it default
        if not self.pk and not ShippingAddress.objects.filter(user=self.user).exists():
            self.is_default = True
            
        super().save(*args, **kwargs)

    @property
    def full_address(self):
        """Return the complete formatted address"""
        parts = []
        
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country:
            parts.append(self.country)
            
        return ", ".join(parts) if parts else "No address provided"

    