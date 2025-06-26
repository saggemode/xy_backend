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

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_username', 'recipient_details',
            'sender', 'sender_username', 'sender_details',
            'userId', 'user_username', 'user_details',
            'orderId', 'order_id', 'order',
            'title', 'message', 'link', 'notification_type', 'notification_type_display',
            'level', 'level_display', 'isRead', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


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

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient_username', 'recipient_details', 'user_username', 'user_details', 'order_id', 'order',
            'title', 'message', 'notification_type',
            'notification_type_display', 'level', 'level_display', 'isRead', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new notifications."""
    
    class Meta:
        model = Notification
        fields = [
            'recipient', 'sender', 'userId', 'orderId', 'title', 'message', 'link',
            'recipient', 'sender', 'title', 'message', 'link',
            'notification_type', 'level'
        ]

    def create(self, validated_data):
        """Create notification with current user as sender if not specified."""
        request = self.context.get('request')
        if request and not validated_data.get('sender'):
            validated_data['sender'] = request.user
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
