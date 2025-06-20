from django.shortcuts import render
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    NotificationCreateSerializer,
    NotificationUpdateSerializer,
    NotificationBulkUpdateSerializer,
    NotificationStatsSerializer
)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Notification model with full CRUD operations.
    Supports filtering by type, level, and read status.
    """
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'level', 'isRead', 'recipient', 'sender']
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'isRead', 'notification_type', 'level']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Regular users can only see their own notifications.
        Staff users can see all notifications.
        """
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(recipient=self.request.user)
        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return NotificationListSerializer
        elif self.action == 'create':
            return NotificationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NotificationUpdateSerializer
        return NotificationSerializer

    def perform_create(self, serializer):
        """Set the sender to the current user when creating a notification."""
        serializer.save(sender=self.request.user)

    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def mark_as_unread(self, request, pk=None):
        """Mark a notification as unread."""
        notification = self.get_object()
        notification.mark_as_unread()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_notifications(self, request):
        """Get current user's notifications."""
        notifications = self.get_queryset().filter(recipient=request.user)
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_notifications(self, request):
        """Get current user's unread notifications."""
        notifications = self.get_queryset().filter(
            recipient=request.user,
            isRead=False
        )
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_mark_read(self, request):
        """Mark multiple notifications as read."""
        serializer = NotificationBulkUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            notification_ids = serializer.validated_data['notification_ids']
            Notification.objects.filter(
                id__in=notification_ids,
                recipient=request.user
            ).update(isRead=True)
            return Response({'message': f'Marked {len(notification_ids)} notifications as read'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def bulk_mark_unread(self, request):
        """Mark multiple notifications as unread."""
        serializer = NotificationBulkUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            notification_ids = serializer.validated_data['notification_ids']
            Notification.objects.filter(
                id__in=notification_ids,
                recipient=request.user
            ).update(isRead=False)
            return Response({'message': f'Marked {len(notification_ids)} notifications as unread'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def notification_stats(self, request):
        """Get notification statistics for the current user."""
        queryset = self.get_queryset().filter(recipient=request.user)
        
        stats = {
            'total_notifications': queryset.count(),
            'unread_count': queryset.filter(isRead=False).count(),
            'read_count': queryset.filter(isRead=True).count(),
            'notifications_by_type': dict(queryset.values('notification_type').annotate(
                count=Count('id')
            ).values_list('notification_type', 'count')),
            'notifications_by_level': dict(queryset.values('level').annotate(
                count=Count('id')
            ).values_list('level', 'count')),
        }
        
        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Clear all notifications for the current user."""
        count = self.get_queryset().filter(recipient=request.user).delete()[0]
        return Response({'message': f'Cleared {count} notifications'})

    @action(detail=False, methods=['get'])
    def recent_notifications(self, request):
        """Get recent notifications (last 7 days)."""
        seven_days_ago = timezone.now() - timedelta(days=7)
        notifications = self.get_queryset().filter(
            recipient=request.user,
            created_at__gte=seven_days_ago
        )
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get notifications filtered by type."""
        notification_type = request.query_params.get('type')
        if not notification_type:
            return Response(
                {'error': 'type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notifications = self.get_queryset().filter(
            recipient=request.user,
            notification_type=notification_type
        )
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
