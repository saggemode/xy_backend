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
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID')
    ),
    # Phone number validator
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )

    # User relationship
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shipping_addresses',
        help_text="The user this shipping address belongs to"
    )

    # Address details
    full_name = models.CharField(
        max_length=100,
        help_text="Full name of the recipient"
    )
    address = models.CharField(
        max_length=200,
        help_text="Street address, P.O. box, company name"
    )

    city = models.CharField(
        max_length=100,
        help_text="City or town"
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
        help_text="ZIP or postal code"
    )
    phone = PhoneNumberField(region=None, help_text="Contact phone number")

    additional_phone = PhoneNumberField(region=None, blank=True, null=True, help_text="Additional contact phone number (optional)")

    # Address status
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default shipping address"
    )

    # Address type
    ADDRESS_TYPE_CHOICES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('school','School'),
        ('market','Market'),
        ('business', 'Business'),
        ('other', 'Other'),
        

    ]
    address_type = models.CharField(
        max_length=10,
        choices=ADDRESS_TYPE_CHOICES,
        default='home',
        help_text="Type of address (Home, Work, Other)"
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
        return f"{self.full_name} - {self.city}, {self.region}, {self.country}"

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
        """
        Returns the full address as a single string, including all relevant fields.
        """
        parts = [
            self.full_name,
            self.address,
            self.city,
            str(self.state) if self.state else "",
            str(self.country) if self.country else "",
            self.postal_code,
            f"Phone: {self.phone}" if self.phone else "",
            f"Additional Phone: {self.additional_phone}" if self.additional_phone else "",
            f"Type: {self.get_address_type_display()}" if self.address_type else "",
        ]
        # Filter out empty parts and join with commas
        return ', '.join([part for part in parts if part])