from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')

app_name = 'notification'

urlpatterns = [
    # Include all router URLs
    path('', include(router.urls)),
    
    # Additional custom endpoints
    path('notifications/mark-read/<uuid:pk>/', views.NotificationViewSet.as_view({'patch': 'mark_as_read'}), name='mark-as-read'),
    path('notifications/mark-unread/<uuid:pk>/', views.NotificationViewSet.as_view({'patch': 'mark_as_unread'}), name='mark-as-unread'),
    path('notifications/my-notifications/', views.NotificationViewSet.as_view({'get': 'my_notifications'}), name='my-notifications'),
    path('notifications/unread/', views.NotificationViewSet.as_view({'get': 'unread_notifications'}), name='unread-notifications'),
    path('notifications/bulk-mark-read/', views.NotificationViewSet.as_view({'post': 'bulk_mark_read'}), name='bulk-mark-read'),
    path('notifications/bulk-mark-unread/', views.NotificationViewSet.as_view({'post': 'bulk_mark_unread'}), name='bulk-mark-unread'),
    path('notifications/stats/', views.NotificationViewSet.as_view({'get': 'notification_stats'}), name='notification-stats'),
    path('notifications/clear-all/', views.NotificationViewSet.as_view({'delete': 'clear_all'}), name='clear-all'),
    path('notifications/recent/', views.NotificationViewSet.as_view({'get': 'recent_notifications'}), name='recent-notifications'),
    path('notifications/by-type/', views.NotificationViewSet.as_view({'get': 'by_type'}), name='by-type'),
]
