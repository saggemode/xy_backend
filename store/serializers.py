from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.contrib.auth.models import User
from django.core.validators import URLValidator
import re

from .models import (
    Store, 
    StoreAnalytics,
    StoreStaff,
    CustomerLifetimeValue
)
from product.models import Product, ProductVariant

class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer for nested data."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']

class SimpleProductSerializer(serializers.ModelSerializer):
    """Simple product serializer for store context."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'base_price', 'discount_price', 'description', 
            'image_urls', 'stock', 'is_featured', 'sku', 'slug', 'status', 
            'available_sizes', 'available_colors', 'created_at', 'updated_at',
            'category_name', 'subcategory_name'
        ]

class StoreStaffSerializer(serializers.ModelSerializer):
    staff_username = serializers.CharField(source='user.username', read_only=True)
    staff_email = serializers.CharField(source='user.email', read_only=True)
    staff_first_name = serializers.CharField(source='user.first_name', read_only=True)
    staff_last_name = serializers.CharField(source='user.last_name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, default=None)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    # Nested user data
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = StoreStaff
        fields = [
            'id', 'store', 'store_name', 'user', 'user_details',
            'role', 'role_display', 'joined_at', 'is_active',
            'staff_username', 'staff_email', 'staff_first_name', 'staff_last_name',
            'can_manage_products', 'can_manage_orders', 'can_manage_staff', 'can_view_analytics',
            'created_by', 'created_by_username',
            'updated_by', 'updated_by_username',
            'deleted_at', 'last_active'
        ]
        read_only_fields = [
            'id', 'joined_at', 'created_by', 'updated_by', 'deleted_at', 'last_active',
            'can_manage_products', 'can_manage_orders', 'can_manage_staff', 'can_view_analytics'
        ]

    def validate(self, data):
        """Custom validation for staff creation/update."""
        # Check if user is already staff at this store
        store = data.get('store')
        user = data.get('user')
        instance = self.instance
        
        if store and user:
            existing_staff = StoreStaff.objects.filter(
                store=store, 
                user=user, 
                deleted_at__isnull=True
            )
            if instance:
                existing_staff = existing_staff.exclude(pk=instance.pk)
            
            if existing_staff.exists():
                raise serializers.ValidationError({
                    'user': _('This user is already a staff member at this store.')
                })
        
        # Validate role permissions
        role = data.get('role')
        if role == StoreStaff.Roles.OWNER:
            # Check if store already has an owner
            if store:
                existing_owner = StoreStaff.objects.filter(
                    store=store,
                    role=StoreStaff.Roles.OWNER,
                    is_active=True,
                    deleted_at__isnull=True
                )
                if instance:
                    existing_owner = existing_owner.exclude(pk=instance.pk)
                
                if existing_owner.exists():
                    raise serializers.ValidationError({
                        'role': _('A store can only have one owner.')
                    })
        
        return data

    @staticmethod
    def get_role_choices():
        return [{'value': choice[0], 'label': choice[1]} for choice in StoreStaff.Roles.choices]

class StoreAnalyticsSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = StoreAnalytics
        fields = [
            'id', 'store', 'store_name', 'total_views', 'unique_visitors', 'page_views',
            'total_sales', 'revenue', 'total_orders', 'average_order_value',
            'conversion_rate', 'bounce_rate', 'total_products', 'active_products',
            'top_selling_products', 'total_customers', 'repeat_customers',
            'customer_retention_rate', 'last_updated', 'calculated_at'
        ]
        read_only_fields = [
            'id', 'last_updated', 'calculated_at', 'revenue', 'average_order_value',
            'conversion_rate', 'customer_retention_rate'
        ]

    def validate_revenue(self, value):
        """Validate revenue is non-negative."""
        if value < 0:
            raise serializers.ValidationError(_('Revenue cannot be negative.'))
        return value

    def validate_conversion_rate(self, value):
        """Validate conversion rate is between 0 and 100."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(_('Conversion rate must be between 0 and 100.'))
        return value

class CustomerLifetimeValueSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = CustomerLifetimeValue
        fields = [
            'id', 'user', 'user_details', 'total_spent', 'total_orders',
            'first_purchase_date', 'last_purchase_date', 'average_order_value',
            'purchase_frequency', 'customer_since', 'last_updated'
        ]
        read_only_fields = [
            'id', 'customer_since', 'last_updated', 'average_order_value', 'purchase_frequency'
        ]

    def validate_total_spent(self, value):
        """Validate total spent is non-negative."""
        if value < 0:
            raise serializers.ValidationError(_('Total spent cannot be negative.'))
        return value

    def validate_total_orders(self, value):
        """Validate total orders is non-negative."""
        if value < 0:
            raise serializers.ValidationError(_('Total orders cannot be negative.'))
        return value

class StoreSerializer(serializers.ModelSerializer):
    # Computed fields
    total_products = serializers.SerializerMethodField()
    total_staff = serializers.SerializerMethodField()
    is_operational = serializers.BooleanField(read_only=True)
    
    # Owner information
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    owner_details = UserSerializer(source='owner', read_only=True)
    
    # Audit information
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, default=None)
    verified_by_username = serializers.CharField(source='verified_by.username', read_only=True, default=None)
    
    # Optional nested fields
    products = serializers.SerializerMethodField()
    staff = serializers.SerializerMethodField()
    analytics = serializers.SerializerMethodField()

    def get_total_products(self, obj):
        return obj.total_products

    def get_total_staff(self, obj):
        return obj.total_staff
    
    def get_products(self, obj):
        request = self.context.get('request')
        include_products = self.context.get('include_products', False)
        
        # Check both query parameters and context variables
        if (request and request.query_params.get('include_products') == 'true') or include_products:
            products = obj.products.all()
            return SimpleProductSerializer(products, many=True, context=self.context).data
        return None
    
    def get_staff(self, obj):
        request = self.context.get('request')
        include_staff = self.context.get('include_staff', False)
        
        # Check both query parameters and context variables
        if (request and request.query_params.get('include_staff') == 'true') or include_staff:
            staff = obj.staff_members.filter(deleted_at__isnull=True)
            return StoreStaffSerializer(staff, many=True, context=self.context).data
        return None

    def get_analytics(self, obj):
        request = self.context.get('request')
        include_analytics = self.context.get('include_analytics', False)
        
        # Check both query parameters and context variables
        if (request and request.query_params.get('include_analytics') == 'true') or include_analytics:
            try:
                analytics = obj.analytics
                return StoreAnalyticsSerializer(analytics, context=self.context).data
            except StoreAnalytics.DoesNotExist:
                return None
        return None

    class Meta:
        model = Store
        fields = [
            'id', 'name', 'description', 'location', 'logo', 'cover_image',
            'contact_email', 'phone_number', 'website_url', 'facebook_url',
            'instagram_url', 'twitter_url', 'status', 'is_active', 'is_verified',
            'commission_rate', 'auto_approve_products', 'created_at', 'updated_at',
            'verified_at', 'deleted_at', 'owner', 'owner_username', 'owner_email',
            'owner_details', 'created_by', 'created_by_username', 'updated_by',
            'updated_by_username', 'verified_by', 'verified_by_username',
            'total_products', 'total_staff', 'is_operational',
            'products', 'staff', 'analytics'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'verified_at', 'deleted_at',
            'total_products', 'total_staff', 'is_operational'
        ]

    def validate(self, data):
        """Custom validation for store data."""
        # Validate that at least one contact method is provided
        contact_email = data.get('contact_email')
        phone_number = data.get('phone_number')
        
        if not contact_email and not phone_number:
            raise serializers.ValidationError({
                'contact_email': _('At least one contact method (email or phone) is required.'),
                'phone_number': _('At least one contact method (email or phone) is required.')
            })
        
        # Validate social media URLs
        facebook_url = data.get('facebook_url')
        instagram_url = data.get('instagram_url')
        twitter_url = data.get('twitter_url')
        
        if facebook_url and 'facebook.com' not in facebook_url:
            raise serializers.ValidationError({
                'facebook_url': _('Please provide a valid Facebook URL.')
            })
        
        if instagram_url and 'instagram.com' not in instagram_url:
            raise serializers.ValidationError({
                'instagram_url': _('Please provide a valid Instagram URL.')
            })
        
        if twitter_url and 'twitter.com' not in twitter_url:
            raise serializers.ValidationError({
                'twitter_url': _('Please provide a valid Twitter URL.')
            })
        
        # Validate commission rate
        commission_rate = data.get('commission_rate')
        if commission_rate is not None and (commission_rate < 0 or commission_rate > 100):
            raise serializers.ValidationError({
                'commission_rate': _('Commission rate must be between 0 and 100.')
            })
        
        return data

    def validate_name(self, value):
        """Validate store name format."""
        if not re.match(r'^[a-zA-Z0-9\s\-_&.]+$', value):
            raise serializers.ValidationError(
                _('Store name can only contain letters, numbers, spaces, hyphens, underscores, ampersands, and periods.')
            )
        return value

    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value and not re.match(r'^[\+]?[1-9][\d]{0,15}$', value):
            raise serializers.ValidationError(_('Enter a valid phone number.'))
        return value

    def validate_website_url(self, value):
        """Validate website URL format."""
        if value:
            try:
                URLValidator()(value)
            except ValidationError:
                raise serializers.ValidationError(_('Enter a valid URL.'))
        return value

    def create(self, validated_data):
        """Override create to set audit fields."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            validated_data['updated_by'] = request.user
        
        # Set owner as created_by if not specified
        if 'created_by' not in validated_data and 'owner' in validated_data:
            validated_data['created_by'] = validated_data['owner']
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Override update to set audit fields."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['updated_by'] = request.user
        
        return super().update(instance, validated_data)

# Detailed serializers for specific use cases
class StoreDetailSerializer(StoreSerializer):
    """Detailed store serializer with all nested data."""
    
    def get_products(self, obj):
        products = obj.products.all()
        return SimpleProductSerializer(products, many=True, context=self.context).data
    
    def get_staff(self, obj):
        staff = obj.staff_members.filter(deleted_at__isnull=True)
        return StoreStaffSerializer(staff, many=True, context=self.context).data

    def get_analytics(self, obj):
        try:
            analytics = obj.analytics
            return StoreAnalyticsSerializer(analytics, context=self.context).data
        except StoreAnalytics.DoesNotExist:
            return None

class StoreCreateSerializer(StoreSerializer):
    """Serializer for store creation with additional validation."""
    
    def validate(self, data):
        """Additional validation for store creation."""
        # Check if user already owns a store
        owner = data.get('owner')
        if owner:
            existing_store = Store.objects.filter(
                owner=owner,
                deleted_at__isnull=True
            ).first()
            
            if existing_store:
                raise serializers.ValidationError({
                    'owner': _('This user already owns a store.')
                })
        
        return super().validate(data)

class StoreUpdateSerializer(StoreSerializer):
    """Serializer for store updates with restricted fields."""
    
    class Meta(StoreSerializer.Meta):
        read_only_fields = StoreSerializer.Meta.read_only_fields + [
            'owner', 'created_by', 'verified_by', 'verified_at'
        ]

# Bulk operation serializers
class BulkStoreActionSerializer(serializers.Serializer):
    """Serializer for bulk store actions."""
    store_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100,
        help_text=_('List of store IDs to perform action on')
    )
    action = serializers.ChoiceField(
        choices=[
            ('activate', 'Activate'),
            ('deactivate', 'Deactivate'),
            ('verify', 'Verify'),
            ('suspend', 'Suspend'),
            ('close', 'Close'),
        ],
        help_text=_('Action to perform on selected stores')
    )

class BulkStaffActionSerializer(serializers.Serializer):
    """Serializer for bulk staff actions."""
    staff_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100,
        help_text=_('List of staff IDs to perform action on')
    )
    action = serializers.ChoiceField(
        choices=[
            ('activate', 'Activate'),
            ('deactivate', 'Deactivate'),
            ('assign_role', 'Assign Role'),
        ],
        help_text=_('Action to perform on selected staff')
    )
    role = serializers.ChoiceField(
        choices=StoreStaff.Roles.choices,
        required=False,
        help_text=_('Role to assign (required for assign_role action)')
    )

# Analytics and reporting serializers
class StoreAnalyticsReportSerializer(serializers.Serializer):
    """Serializer for store analytics reports."""
    store_id = serializers.UUIDField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    report_type = serializers.ChoiceField(
        choices=[
            ('sales', 'Sales Report'),
            ('products', 'Products Report'),
            ('customers', 'Customers Report'),
            ('performance', 'Performance Report'),
        ],
        default='sales'
    )

class StoreStatisticsSerializer(serializers.Serializer):
    """Serializer for store statistics."""
    total_stores = serializers.IntegerField()
    active_stores = serializers.IntegerField()
    verified_stores = serializers.IntegerField()
    total_products = serializers.IntegerField()
    total_staff = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    store_categories = serializers.ListField()
    verification_rate = serializers.FloatField()
    activation_rate = serializers.FloatField()
