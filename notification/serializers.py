from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Notification, NotificationType, NotificationLevel, NotificationStatus
from order.serializers import OrderSerializer

User = get_user_model()


class SimpleUserSerializer(serializers.ModelSerializer):
    """Simplified user serializer for nested user data."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class NotificationSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for Notification model with all fields and nested data.
    
    Features:
    - Full model field coverage
    - Nested user and order data
    - Computed display fields
    - Read-only audit fields
    - Proper validation
    """
    
    # Computed fields for better UX
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    order_id = serializers.UUIDField(source='orderId.id', read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Nested serializers for related objects
    order = OrderSerializer(source='orderId', read_only=True)
    recipient_details = SimpleUserSerializer(source='recipient', read_only=True)
    sender_details = SimpleUserSerializer(source='sender', read_only=True)
    user_details = SimpleUserSerializer(source='user', read_only=True)
    
    # Computed properties
    is_actionable = serializers.BooleanField(read_only=True)
    age_in_hours = serializers.FloatField(read_only=True)
    is_urgent = serializers.BooleanField(read_only=True)
    
    # URL fields
    absolute_url = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            # Primary key
            'id',
            
            # User relationships
            'recipient', 'recipient_username', 'recipient_details',
            'sender', 'sender_username', 'sender_details',
            'user', 'user_username', 'user_details',
            
            # Related objects
            'orderId', 'order_id', 'order',
            
            # Banking references
            'transaction', 'bank_transfer', 'bill_payment', 'virtual_card',
            
            # Core content
            'title', 'message',
            
            # Notification metadata
            'notification_type', 'notification_type_display',
            'level', 'level_display',
            'status', 'status_display',
            
            # Read status
            'isRead', 'read_at',
            
            # Actionable notifications
            'action_text', 'action_url', 'link',
            
            # Priority and metadata
            'priority', 'source', 'extra_data',
            
            # Audit fields
            'created_at', 'updated_at',
            
            # Computed properties
            'is_actionable', 'age_in_hours', 'is_urgent',
            'absolute_url',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'read_at',
            'is_actionable', 'age_in_hours', 'is_urgent'
        ]

    def get_absolute_url(self, obj):
        """Get the absolute URL for the notification."""
        return obj.get_absolute_url()

    def validate(self, data):
        """Custom validation for notification data."""
        # Validate action_text and action_url consistency
        action_text = data.get('action_text')
        action_url = data.get('action_url')
        
        if bool(action_text) != bool(action_url):
            raise serializers.ValidationError({
                'action_text': 'Action text and action URL must be provided together.',
                'action_url': 'Action text and action URL must be provided together.'
            })
        
        # Validate priority range
        priority = data.get('priority', 0)
        if priority < 0 or priority > 100:
            raise serializers.ValidationError({
                'priority': 'Priority must be between 0 and 100.'
            })
        
        return data


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for listing notifications.
    
    Includes essential fields for list views with minimal data transfer.
    """
    
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    order_id = serializers.UUIDField(source='orderId.id', read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Nested data for list view
    recipient_details = SimpleUserSerializer(source='recipient', read_only=True)
    user_details = SimpleUserSerializer(source='user', read_only=True)
    order = OrderSerializer(source='orderId', read_only=True)
    
    # Computed properties
    is_actionable = serializers.BooleanField(read_only=True)
    age_in_hours = serializers.FloatField(read_only=True)
    is_urgent = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient', 'recipient_username', 'recipient_details',
            'user', 'user_username', 'user_details',
            'orderId', 'order_id', 'order',
            'transaction', 'bank_transfer', 'bill_payment', 'virtual_card',
            'title', 'message',
            'notification_type', 'notification_type_display',
            'level', 'level_display',
            'status', 'status_display',
            'isRead', 'read_at',
            'action_text', 'action_url', 'link',
            'priority', 'source',
            'created_at', 'updated_at',
            'is_actionable', 'age_in_hours', 'is_urgent',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'read_at',
            'is_actionable', 'age_in_hours', 'is_urgent'
        ]


class NotificationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new notifications with business logic.
    
    Features:
    - Auto-assign priority based on notification type
    - Auto-set action buttons for common types
    - Prevent duplicate notifications
    - Respect user preferences
    - Comprehensive validation
    """
    
    source = serializers.CharField(required=False, max_length=64)
    action_text = serializers.CharField(required=False, max_length=64, allow_blank=True)
    action_url = serializers.URLField(required=False, max_length=500, allow_blank=True, allow_null=True)
    priority = serializers.IntegerField(required=False, min_value=0, max_value=100)
    extra_data = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            'recipient', 'sender', 'user', 'orderId',
            'transaction', 'bank_transfer', 'bill_payment', 'virtual_card',
            'title', 'message', 'link',
            'notification_type', 'level', 'status',
            'action_text', 'action_url',
            'priority', 'source', 'extra_data',
        ]

    def validate(self, data):
        """Custom validation for notification creation."""
        # Validate action_text and action_url consistency
        action_text = data.get('action_text')
        action_url = data.get('action_url')
        
        if bool(action_text) != bool(action_url):
            raise serializers.ValidationError({
                'action_text': 'Action text and action URL must be provided together.',
                'action_url': 'Action text and action URL must be provided together.'
            })
        
        return data

    def create(self, validated_data):
        """Create notification with business logic and validation."""
        request = self.context.get('request')
        
        # Set sender if not provided
        if request and not validated_data.get('sender'):
            validated_data['sender'] = request.user
        
        # Auto-assign priority based on notification type
        notification_type = validated_data.get('notification_type')
        if notification_type in ['system_alert', 'security_alert', 'payment_failed']:
            validated_data['priority'] = 10
        elif notification_type in ['order_status_update', 'shipping_update', 'refund_processed']:
            validated_data['priority'] = 8
        elif notification_type == 'promotion':
            validated_data['priority'] = 3
        elif notification_type == 'flash_sale':
            validated_data['priority'] = 7
        else:
            validated_data['priority'] = validated_data.get('priority', 5)
        
        # Auto-set action buttons for common types
        order = validated_data.get('orderId')
        if notification_type == 'order_status_update' and order:
            validated_data['action_text'] = 'View Order'
            validated_data['action_url'] = f'/orders/{order.id}/'
        elif notification_type == 'review_reminder' and order:
            validated_data['action_text'] = 'Leave Review'
            validated_data['action_url'] = f'/orders/{order.id}/review/'
        elif notification_type == 'promotion':
            validated_data['action_text'] = 'Shop Now'
            validated_data['action_url'] = '/promotions/'
        elif notification_type == 'flash_sale':
            validated_data['action_text'] = 'Shop Sale'
            validated_data['action_url'] = '/flash-sales/'
        elif notification_type == 'payment_failed':
            validated_data['action_text'] = 'Retry Payment'
            validated_data['action_url'] = f'/orders/{order.id}/payment/'
        
        # Set status
        validated_data['status'] = validated_data.get('status', 'pending')
        
        # Prevent duplicate unread notifications
        recipient = validated_data.get('recipient')
        existing = Notification.objects.filter(
            recipient=recipient,
            notification_type=notification_type,
            orderId=order,
            isRead=False
        )
        if existing.exists():
            raise serializers.ValidationError(
                'A similar unread notification already exists for this user.'
            )
        
        # Respect user preferences if provided
        extra_data = validated_data.get('extra_data', {})
        if extra_data and extra_data.get('user_preferences'):
            preferences = extra_data['user_preferences']
            muted_types = preferences.get('muted_types', [])
            if notification_type in muted_types:
                raise serializers.ValidationError(
                    f'User has muted {notification_type} notifications.'
                )
        
        return super().create(validated_data)


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating notification fields."""
    
    class Meta:
        model = Notification
        fields = ['isRead', 'status', 'action_text', 'action_url', 'priority', 'extra_data']
        
    def validate(self, data):
        """Validate update data."""
        # Validate action_text and action_url consistency
        action_text = data.get('action_text')
        action_url = data.get('action_url')
        
        if bool(action_text) != bool(action_url):
            raise serializers.ValidationError({
                'action_text': 'Action text and action URL must be provided together.',
                'action_url': 'Action text and action URL must be provided together.'
            })
        
        return data


class NotificationBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating notifications."""
    
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of notification IDs to update"
    )
    isRead = serializers.BooleanField(
        help_text="Set all notifications to this read status"
    )
    status = serializers.ChoiceField(
        choices=NotificationStatus.choices,
        required=False,
        help_text="Set all notifications to this status"
    )

    def validate_notification_ids(self, value):
        """Validate that all notification IDs exist and belong to the user."""
        request = self.context.get('request')
        if request and request.user:
            user_notifications = Notification.objects.filter(
                id__in=value,
                recipient=request.user
            )
            if len(user_notifications) != len(value):
                raise serializers.ValidationError(
                    "Some notification IDs are invalid or don't belong to you."
                )
        return value


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics."""
    
    total_notifications = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    read_count = serializers.IntegerField()
    urgent_count = serializers.IntegerField()
    actionable_count = serializers.IntegerField()
    notifications_by_type = serializers.DictField()
    notifications_by_level = serializers.DictField()
    notifications_by_status = serializers.DictField()
    recent_activity = serializers.ListField(child=serializers.DictField())


class NotificationPreferencesSerializer(serializers.Serializer):
    """Serializer for user notification preferences."""
    
    muted_types = serializers.ListField(
        child=serializers.ChoiceField(choices=NotificationType.choices),
        required=False,
        default=list
    )
    preferred_levels = serializers.ListField(
        child=serializers.ChoiceField(choices=NotificationLevel.choices),
        required=False,
        default=list
    )
    email_notifications = serializers.BooleanField(default=True)
    push_notifications = serializers.BooleanField(default=True)
    sms_notifications = serializers.BooleanField(default=False)
