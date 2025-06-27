from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')

# URL patterns for notification app
urlpatterns = [
    # Include router URLs for standard CRUD operations
    path('', include(router.urls)),
    
    # Custom endpoints for specific functionality
    path('api/v1/notifications/my/', views.NotificationViewSet.as_view({
        'get': 'my_notifications'
    }), name='my-notifications'),
    
    path('api/v1/notifications/unread/', views.NotificationViewSet.as_view({
        'get': 'unread_notifications'
    }), name='unread-notifications'),
    
    path('api/v1/notifications/urgent/', views.NotificationViewSet.as_view({
        'get': 'urgent_notifications'
    }), name='urgent-notifications'),
    
    path('api/v1/notifications/recent/', views.NotificationViewSet.as_view({
        'get': 'recent_notifications'
    }), name='recent-notifications'),
    
    path('api/v1/notifications/by-type/', views.NotificationViewSet.as_view({
        'get': 'by_type'
    }), name='notifications-by-type'),
    
    path('api/v1/notifications/stats/', views.NotificationViewSet.as_view({
        'get': 'notification_stats'
    }), name='notification-stats'),
    
    path('api/v1/notifications/preferences/', views.NotificationViewSet.as_view({
        'get': 'preferences',
        'post': 'preferences'
    }), name='notification-preferences'),
    
    # Bulk operations
    path('api/v1/notifications/bulk-mark-read/', views.NotificationViewSet.as_view({
        'post': 'bulk_mark_read'
    }), name='bulk-mark-read'),
    
    path('api/v1/notifications/bulk-mark-unread/', views.NotificationViewSet.as_view({
        'post': 'bulk_mark_unread'
    }), name='bulk-mark-unread'),
    
    path('api/v1/notifications/clear-all/', views.NotificationViewSet.as_view({
        'delete': 'clear_all'
    }), name='clear-all-notifications'),
    
    # Individual notification actions
    path('api/v1/notifications/<uuid:pk>/mark-read/', views.NotificationViewSet.as_view({
        'patch': 'mark_as_read'
    }), name='mark-notification-read'),
    
    path('api/v1/notifications/<uuid:pk>/mark-unread/', views.NotificationViewSet.as_view({
        'patch': 'mark_as_unread'
    }), name='mark-notification-unread'),
    
    path('api/v1/notifications/<uuid:pk>/soft-delete/', views.NotificationViewSet.as_view({
        'delete': 'soft_delete'
    }), name='soft-delete-notification'),
    
    path('api/v1/notifications/<uuid:pk>/restore/', views.NotificationViewSet.as_view({
        'patch': 'restore'
    }), name='restore-notification'),
]

# Add router URLs to the main patterns
urlpatterns += router.urls

