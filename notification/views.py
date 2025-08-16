import logging
from django.shortcuts import render
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Max, Min
from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.db import transaction

from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    NotificationCreateSerializer,
    NotificationUpdateSerializer,
    NotificationBulkUpdateSerializer,
    NotificationStatsSerializer,
    NotificationPreferencesSerializer
)

logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Professional ViewSet for Notification model with comprehensive CRUD operations.
    
    Features:
    - Full CRUD operations with proper permissions
    - Advanced filtering and searching
    - Bulk operations
    - Statistics and analytics
    - Caching for performance
    - Comprehensive error handling
    - Audit logging
    """
    
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Comprehensive filtering options
    filterset_fields = [
        'notification_type', 'level', 'status', 'isRead',
        'recipient', 'sender', 'user', 'orderId', 'source', 'priority',
        'transaction', 'bank_transfer', 'bill_payment', 'virtual_card'
    ]
    
    # Search across multiple fields
    search_fields = [
        'title', 'message', 'action_text', 'source',
        'recipient__username', 'sender__username', 'user__username'
    ]
    
    # Ordering options
    ordering_fields = [
        'created_at', 'updated_at', 'read_at',
        'priority', 'notification_type', 'level', 'status', 'isRead'
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        - Regular users can only see their own notifications
        - Staff users can see all notifications
        """
        queryset = super().get_queryset()
        # Staff users can see all notifications
        if self.request.user.is_staff:
            return queryset
        # Regular users can only see their own notifications
        return queryset.filter(recipient=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return NotificationListSerializer
        elif self.action == 'create':
            return NotificationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NotificationUpdateSerializer
        return NotificationSerializer

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Set the sender to the current user when creating a notification."""
        try:
            notification = serializer.save(sender=self.request.user)
            logger.info(f"Notification created: {notification.id} for user {notification.recipient.username}")
            # Clear cache for user's notification count
            cache_key = f"notification_count_{notification.recipient.id}"
            cache.delete(cache_key)
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            raise

    def perform_update(self, serializer):
        """Handle notification updates with logging."""
        try:
            notification = serializer.save()
            logger.info(f"Notification updated: {notification.id}")
            # Clear cache if read status changed
            if 'isRead' in serializer.validated_data:
                cache_key = f"notification_count_{notification.recipient.id}"
                cache.delete(cache_key)
        except Exception as e:
            logger.error(f"Error updating notification: {str(e)}")
            raise

    def perform_destroy(self, instance):
        """Hard delete notification."""
        try:
            instance.delete()
            logger.info(f"Notification deleted: {instance.id}")
            # Clear cache
            cache_key = f"notification_count_{instance.recipient.id}"
            cache.delete(cache_key)
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            raise

    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read with proper error handling."""
        try:
            notification = self.get_object()
            notification.mark_as_read()
            serializer = self.get_serializer(notification)
            logger.info(f"Notification marked as read: {notification.id}")
            # Clear cache
            cache_key = f"notification_count_{notification.recipient.id}"
            cache.delete(cache_key)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return Response(
                {'error': 'Failed to mark notification as read'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def mark_as_unread(self, request, pk=None):
        """Mark a notification as unread."""
        try:
            notification = self.get_object()
            notification.mark_as_unread()
            serializer = self.get_serializer(notification)
            logger.info(f"Notification marked as unread: {notification.id}")
            # Clear cache
            cache_key = f"notification_count_{notification.recipient.id}"
            cache.delete(cache_key)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error marking notification as unread: {str(e)}")
            return Response(
                {'error': 'Failed to mark notification as unread'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def my_notifications(self, request):
        """Get current user's notifications with caching."""
        cache_key = f"my_notifications_{request.user.id}"
        cached_data = cache.get(cache_key)
        if cached_data and not request.query_params:
            return Response(cached_data)
        try:
            notifications = self.get_queryset().filter(recipient=request.user)
            serializer = self.get_serializer(notifications, many=True)
            # Cache for 5 minutes
            cache.set(cache_key, serializer.data, 300)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching user notifications: {str(e)}")
            return Response(
                {'error': 'Failed to fetch notifications'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def unread_notifications(self, request):
        """Get current user's unread notifications."""
        try:
            notifications = self.get_queryset().filter(
                recipient=request.user,
                isRead=False
            )
            serializer = self.get_serializer(notifications, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching unread notifications: {str(e)}")
            return Response(
                {'error': 'Failed to fetch unread notifications'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def urgent_notifications(self, request):
        """Get current user's urgent notifications."""
        try:
            notifications = self.get_queryset().filter(
                recipient=request.user,
                isRead=False
            ).filter(
                Q(priority__gte=8) | Q(level='critical')
            )
            serializer = self.get_serializer(notifications, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching urgent notifications: {str(e)}")
            return Response(
                {'error': 'Failed to fetch urgent notifications'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_mark_read(self, request):
        """Mark multiple notifications as read."""
        serializer = NotificationBulkUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    notification_ids = serializer.validated_data['notification_ids']
                    notifications = Notification.objects.filter(
                        id__in=notification_ids,
                        recipient=request.user
                    )
                    # Update all notifications
                    updated_count = notifications.update(
                        isRead=True,
                        read_at=timezone.now(),
                        status='read'
                    )
                    # Clear cache
                    cache_key = f"notification_count_{request.user.id}"
                    cache.delete(cache_key)
                    logger.info(f"Bulk marked {updated_count} notifications as read for user {request.user.username}")
                    return Response({
                        'message': f'Marked {updated_count} notifications as read',
                        'updated_count': updated_count
                    })
            except Exception as e:
                logger.error(f"Error in bulk mark read: {str(e)}")
                return Response(
                    {'error': 'Failed to mark notifications as read'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def bulk_mark_unread(self, request):
        """Mark multiple notifications as unread."""
        serializer = NotificationBulkUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    notification_ids = serializer.validated_data['notification_ids']
                    notifications = Notification.objects.filter(
                        id__in=notification_ids,
                        recipient=request.user
                    )
                    updated_count = notifications.update(
                        isRead=False,
                        read_at=None,
                        status='delivered'
                    )
                    # Clear cache
                    cache_key = f"notification_count_{request.user.id}"
                    cache.delete(cache_key)
                    logger.info(f"Bulk marked {updated_count} notifications as unread for user {request.user.username}")
                    return Response({
                        'message': f'Marked {updated_count} notifications as unread',
                        'updated_count': updated_count
                    })
            except Exception as e:
                logger.error(f"Error in bulk mark unread: {str(e)}")
                return Response(
                    {'error': 'Failed to mark notifications as unread'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def notification_stats(self, request):
        """Get comprehensive notification statistics for the current user."""
        cache_key = f"notification_stats_{request.user.id}"
        cached_stats = cache.get(cache_key)
        if cached_stats:
            return Response(cached_stats)
        try:
            queryset = self.get_queryset().filter(recipient=request.user)
            # Basic counts
            total_count = queryset.count()
            unread_count = queryset.filter(isRead=False).count()
            read_count = queryset.filter(isRead=True).count()
            urgent_count = queryset.filter(
                Q(priority__gte=8) | Q(level='critical')
            ).count()
            actionable_count = queryset.filter(
                action_text__isnull=False,
                action_url__isnull=False
            ).count()
            # Grouped statistics
            by_type = dict(queryset.values('notification_type').annotate(
                count=Count('id')
            ).values_list('notification_type', 'count'))
            by_level = dict(queryset.values('level').annotate(
                count=Count('id')
            ).values_list('level', 'count'))
            by_status = dict(queryset.values('status').annotate(
                count=Count('id')
            ).values_list('status', 'count'))
            # Recent activity (last 7 days)
            seven_days_ago = timezone.now() - timedelta(days=7)
            recent_activity = queryset.filter(
                created_at__gte=seven_days_ago
            ).values('id', 'title', 'notification_type', 'created_at', 'isRead')[:10]
            stats = {
                'total_notifications': total_count,
                'unread_count': unread_count,
                'read_count': read_count,
                'urgent_count': urgent_count,
                'actionable_count': actionable_count,
                'notifications_by_type': by_type,
                'notifications_by_level': by_level,
                'notifications_by_status': by_status,
                'recent_activity': list(recent_activity),
            }
            # Cache for 10 minutes
            cache.set(cache_key, stats, 600)
            serializer = NotificationStatsSerializer(stats)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error generating notification stats: {str(e)}")
            return Response(
                {'error': 'Failed to generate notification statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def recent_notifications(self, request):
        """Get recent notifications (last 7 days)."""
        try:
            seven_days_ago = timezone.now() - timedelta(days=7)
            notifications = self.get_queryset().filter(
                recipient=request.user,
                created_at__gte=seven_days_ago
            )
            serializer = self.get_serializer(notifications, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching recent notifications: {str(e)}")
            return Response(
                {'error': 'Failed to fetch recent notifications'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get notifications filtered by type."""
        notification_type = request.query_params.get('type')
        if not notification_type:
            return Response(
                {'error': 'type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            notifications = self.get_queryset().filter(
                recipient=request.user,
                notification_type=notification_type
            )
            serializer = self.get_serializer(notifications, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching notifications by type: {str(e)}")
            return Response(
                {'error': 'Failed to fetch notifications by type'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get', 'post'])
    def preferences(self, request):
        """Get or update user notification preferences."""
        if request.method == 'GET':
            # Return current preferences (implement based on your user model)
            preferences = {
                'muted_types': [],
                'preferred_levels': ['info', 'success', 'warning'],
                'email_notifications': True,
                'push_notifications': True,
                'sms_notifications': False,
            }
            serializer = NotificationPreferencesSerializer(preferences)
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = NotificationPreferencesSerializer(data=request.data)
            if serializer.is_valid():
                # Save preferences (implement based on your user model)
                logger.info(f"User {request.user.username} updated notification preferences")
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def restore(self, request, pk=None):
        """Stub restore method for NotificationViewSet to fix schema generation."""
        return Response({'detail': 'Restore not implemented.'}, status=501)

    @action(detail=True, methods=['delete'])
    def soft_delete(self, request, pk=None):
        """Stub soft_delete method for NotificationViewSet to fix schema generation."""
        return Response({'detail': 'Soft delete not implemented.'}, status=501)

    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Stub clear_all method for NotificationViewSet to fix schema generation."""
        return Response({'detail': 'Clear all not implemented.'}, status=501)
