from rest_framework import serializers
from .models import Notification
from order.serializers import OrderSerializer
from django.contrib.auth.models import User


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class NotificationSerializer(serializers.ModelSerializer):
    """Main serializer for Notification model with all fields."""
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    user_username = serializers.CharField(source='userId.username', read_only=True)
    order_id = serializers.UUIDField(source='orderId.id', read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    order = OrderSerializer(source='orderId', read_only=True)
    recipient_details = SimpleUserSerializer(source='recipient', read_only=True)
    sender_details = SimpleUserSerializer(source='sender', read_only=True)
    user_details = SimpleUserSerializer(source='userId', read_only=True)
    source = serializers.CharField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_username', 'recipient_details',
            'sender', 'sender_username', 'sender_details',
            'userId', 'user_username', 'user_details',
            'orderId', 'order_id', 'order',
            'title', 'message', 'link', 'notification_type', 'notification_type_display',
            'level', 'level_display', 'isRead', 'created_at',
            'source', 'is_deleted', 'deleted_at',
        ] + [f for f in Notification._meta.fields if f.name not in [
            'id', 'recipient', 'sender', 'userId', 'orderId', 'title', 'message', 'link', 'notification_type', 'level', 'isRead', 'created_at', 'updated_at', 'source', 'is_deleted', 'deleted_at']]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_deleted', 'deleted_at']


class NotificationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing notifications."""
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    user_username = serializers.CharField(source='userId.username', read_only=True)
    order_id = serializers.UUIDField(source='orderId.id', read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    order = OrderSerializer(source='orderId', read_only=True)
    recipient_details = SimpleUserSerializer(source='recipient', read_only=True)
    user_details = SimpleUserSerializer(source='userId', read_only=True)
    source = serializers.CharField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient_username', 'recipient_details', 'user_username', 'user_details', 'order_id', 'order',
            'title', 'message', 'notification_type',
            'notification_type_display', 'level', 'level_display', 'isRead', 'created_at',
            'source', 'is_deleted', 'deleted_at',
        ] + [f for f in Notification._meta.fields if f.name not in [
            'id', 'recipient', 'userId', 'orderId', 'title', 'message', 'link', 'notification_type', 'level', 'isRead', 'created_at', 'updated_at', 'source', 'is_deleted', 'deleted_at']]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_deleted', 'deleted_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new notifications."""
    
    source = serializers.CharField(required=False)
    read_at = serializers.DateTimeField(required=False)
    action_text = serializers.CharField(required=False, allow_blank=True)
    action_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    priority = serializers.IntegerField(required=False)
    extra_data = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Notification
        fields = [
            'recipient', 'sender', 'userId', 'orderId', 'title', 'message', 'link',
            'notification_type', 'level', 'source',
            'read_at', 'action_text', 'action_url', 'priority', 'extra_data',
        ]

    def create(self, validated_data):
        """Create notification with current user as sender if not specified."""
        request = self.context.get('request')
        if request and not validated_data.get('sender'):
            validated_data['sender'] = request.user

        # Auto-assign priority based on notification_type
        notif_type = validated_data.get('notification_type')
        if notif_type in ['system_alert', 'order_status_update']:
            validated_data['priority'] = 10
        elif notif_type == 'promotion':
            validated_data['priority'] = 1
        else:
            validated_data['priority'] = validated_data.get('priority', 5)

        # Auto-set action_text and action_url for certain types
        order = validated_data.get('orderId')
        if notif_type == 'order_status_update' and order:
            validated_data['action_text'] = 'View Order'
            validated_data['action_url'] = f'/orders/{order.id}/'
        elif notif_type == 'review_reminder' and order:
            validated_data['action_text'] = 'Leave Review'
            validated_data['action_url'] = f'/orders/{order.id}/review/'
        elif notif_type == 'promotion':
            validated_data['action_text'] = 'Shop Now'
            validated_data['action_url'] = '/promotions/'

        # Prevent duplicate unread notifications for same user/type/order
        user = validated_data.get('recipient')
        existing = Notification.objects.filter(
            recipient=user,
            notification_type=notif_type,
            orderId=order,
            isRead=False,
            is_deleted=False
        )
        if existing.exists():
            raise serializers.ValidationError('A similar unread notification already exists.')

        # Respect user preferences if provided in extra_data
        extra_data = validated_data.get('extra_data', {})
        if extra_data and extra_data.get('user_preferences'):
            prefs = extra_data['user_preferences']
            if notif_type in prefs.get('muted_types', []):
                raise serializers.ValidationError('User has muted this notification type.')

        return super().create(validated_data)


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating notification read status."""
    
    class Meta:
        model = Notification
        fields = ['isRead']


class NotificationBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating notifications."""
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of notification IDs to update"
    )
    isRead = serializers.BooleanField(
        help_text="Set all notifications to this read status"
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
    notifications_by_type = serializers.DictField()
    notifications_by_level = serializers.DictField()
