import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from cities_light.models import Country, Region
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

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
    state = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="State, province, or region"
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="Country"
    )
    postal_code = models.CharField(
        max_length=20,
        verbose_name=_('Postal Code'),
        help_text=_('Postal or ZIP code'),
        default='12345',
        validators=[
            RegexValidator(
                regex=r'^\d{5}(-\d{4})?$',
                message=_('Enter a valid postal code (e.g., 12345 or 12345-6789)')
            )
        ]
    )
    phone = PhoneNumberField(region=None, help_text="Contact phone number")

    additional_phone = PhoneNumberField(region=None, blank=True, null=True, help_text="Additional contact phone number (optional)")

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
        state_name = self.state.name if self.state else ""
        country_name = self.country.name if self.country else ""
        return f"{self.address}, {self.city}, {state_name}, {country_name}"

    def clean(self):
        """Validate the model instance."""
        # Normalize postal code (remove spaces)
        if self.postal_code:
            self.postal_code = self.postal_code.strip().replace(" ", "")

    def save(self, *args, **kwargs):
        """Override save to handle validation and default address logic."""
        self.full_clean()
        
        # If this is the user's first address, make it default
        if not self.pk and not ShippingAddress.objects.filter(user=self.user).exists():
            self.is_default = True
            
        super().save(*args, **kwargs)

    @property
    def full_address(self):
        """Return the complete formatted address"""
        state_name = self.state.name if self.state else ""
        country_name = self.country.name if self.country else ""
        return f"{self.address}, {self.city}, {state_name} {self.postal_code}, {country_name}"
