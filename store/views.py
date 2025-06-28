import logging
from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets, permissions
from django.contrib.auth import get_user_model
import random
from django.db.models import Avg, Count, Sum, Q, F
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import datetime, timedelta
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

from .models import Store, StoreAnalytics, StoreStaff, CustomerLifetimeValue
from product.models import Product, ProductVariant
from .serializers import (
    StoreSerializer, StoreDetailSerializer, StoreCreateSerializer, StoreUpdateSerializer,
    StoreStaffSerializer, StoreAnalyticsSerializer, CustomerLifetimeValueSerializer,
    BulkStoreActionSerializer, BulkStaffActionSerializer, StoreStatisticsSerializer,
    StoreAnalyticsReportSerializer
)
from notification.models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


class BasicTestView(APIView):
    """Basic test view to check if the app is working."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Basic test endpoint."""
        return Response({
            'status': 'success',
            'message': 'Store app is working',
            'timestamp': timezone.now().isoformat()
        })


class DebugStoreView(APIView):
    """Simple debug view to test store functionality."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Simple test endpoint to check if store models are working."""
        try:
            # Test basic model operations
            store_count = Store.objects.count()
            
            # Test if we can get any stores
            stores = Store.objects.all()[:5]
            store_names = [store.name for store in stores]
            
            # Test notification import
            try:
                from notification.models import Notification
                notification_count = Notification.objects.count()
                notification_import_success = True
            except Exception as e:
                notification_import_success = False
                notification_error = str(e)
            
            # Test notification types
            try:
                from notification.models import Notification
                notification_types = {
                    'ACCOUNT_UPDATE': Notification.NotificationType.ACCOUNT_UPDATE,
                    'SYSTEM_ALERT': Notification.NotificationType.SYSTEM_ALERT,
                }
                notification_levels = {
                    'INFO': Notification.NotificationLevel.INFO,
                    'SUCCESS': Notification.NotificationLevel.SUCCESS,
                    'WARNING': Notification.NotificationLevel.WARNING,
                }
                notification_types_success = True
            except Exception as e:
                notification_types_success = False
                notification_types_error = str(e)
            
            return Response({
                'status': 'success',
                'message': 'Store models are working correctly',
                'data': {
                    'total_stores': store_count,
                    'sample_stores': store_names,
                    'user_authenticated': request.user.is_authenticated,
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'notification_import_success': notification_import_success,
                    'notification_count': notification_count if notification_import_success else None,
                    'notification_types_success': notification_types_success,
                    'notification_error': notification_error if not notification_import_success else None,
                    'notification_types_error': notification_types_error if not notification_types_success else None,
                }
            })
            
        except Exception as e:
            logger.error(f"Debug view error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Error in debug view: {str(e)}',
                'error_type': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StoreViewSet(viewsets.ModelViewSet):
    """
    Professional ViewSet for Store model with comprehensive CRUD operations.
    """
    
    queryset = Store.objects.all().order_by('-created_at')
    serializer_class = StoreSerializer
    permission_classes = [AllowAny]
    
    def _add_related_data_to_stores(self, stores_data, request):
        """Helper method to add products, staff, and analytics data to store data."""
        for store_data in stores_data:
            store_id = store_data['id']
            store_obj = Store.objects.get(id=store_id)
            
            # Get products
            products = store_obj.products.all()
            if products.exists():
                from product.serializers import ProductSerializer
                store_data['products'] = ProductSerializer(products, many=True, context={'request': request}).data
            else:
                store_data['products'] = []
            
            # Get staff
            staff = store_obj.staff_members.filter(deleted_at__isnull=True, is_active=True)
            if staff.exists():
                store_data['staff'] = StoreStaffSerializer(staff, many=True, context={'request': request}).data
            else:
                store_data['staff'] = []
            
            # Get analytics
            try:
                analytics = store_obj.analytics
                store_data['analytics'] = StoreAnalyticsSerializer(analytics, context={'request': request}).data
            except StoreAnalytics.DoesNotExist:
                store_data['analytics'] = None
        
        return stores_data

    def list(self, request, *args, **kwargs):
        """Simple list method for debugging."""
        try:
            queryset = self.get_queryset()
            
            # Use the basic serializer first
            serializer = self.get_serializer(queryset, many=True, context={'request': request})
            data = serializer.data
            
            # Manually add products and staff for each store
            data = self._add_related_data_to_stores(data, request)
            
            return Response({
                'status': 'success',
                'count': queryset.count(),
                'data': data
            })
        except Exception as e:
            logger.error(f"Store list error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Error in store list: {str(e)}',
                'error_type': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='homestore')
    def homestore(self, request):
        """Returns 5 random active and verified stores for the homepage."""
        try:
            # Get active and verified stores
            queryset = Store.objects.filter(
                status='active',
                is_verified=True,
                deleted_at__isnull=True
            )
            
            # Convert to list and shuffle for random selection
            shuffled_queryset = list(queryset)
            random.shuffle(shuffled_queryset)
            
            # Take first 5 items
            selected_stores = shuffled_queryset[:5]
            
            # Now get the full data with related fields for the selected stores
            full_queryset = Store.objects.select_related('owner').prefetch_related(
                'products', 'staff_members', 'analytics'
            ).filter(id__in=[store.id for store in selected_stores])
            
            # Use the basic serializer for homepage display
            serializer = self.get_serializer(full_queryset, many=True, context={'request': request})
            
            return Response({
                'status': 'success',
                'message': 'Featured stores for homepage',
                'count': len(selected_stores),
                'stores': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error in homestore endpoint: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch featured stores',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def my_stores(self, request):
        """Get current user's stores."""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            stores = self.get_queryset().filter(owner=request.user)
            serializer = self.get_serializer(stores, many=True, context={'request': request})
            data = serializer.data
            
            # Manually add products and staff for each store
            data = self._add_related_data_to_stores(data, request)
            
            return Response(data)
        except Exception as e:
            logger.error(f"Error fetching user stores: {str(e)}")
            return Response(
                {'error': 'Failed to fetch stores'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def active_stores(self, request):
        """Get only active stores."""
        try:
            stores = self.get_queryset().filter(status='active', is_verified=True)
            serializer = self.get_serializer(stores, many=True, context={'request': request})
            data = serializer.data
            
            # Manually add products and staff for each store
            data = self._add_related_data_to_stores(data, request)
            
            return Response(data)
        except Exception as e:
            logger.error(f"Error fetching active stores: {str(e)}")
            return Response(
                {'error': 'Failed to fetch active stores'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def verified_stores(self, request):
        """Get only verified stores."""
        try:
            stores = self.get_queryset().filter(is_verified=True)
            serializer = self.get_serializer(stores, many=True, context={'request': request})
            data = serializer.data
            
            # Manually add products and staff for each store
            data = self._add_related_data_to_stores(data, request)
            
            return Response(data)
        except Exception as e:
            logger.error(f"Error fetching verified stores: {str(e)}")
            return Response(
                {'error': 'Failed to fetch verified stores'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def store_statistics(self, request):
        """Get store statistics."""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            queryset = self.get_queryset()
            total_stores = queryset.count()
            active_stores = queryset.filter(status='active').count()
            verified_stores = queryset.filter(is_verified=True).count()
            
            stats = {
                'total_stores': total_stores,
                'active_stores': active_stores,
                'verified_stores': verified_stores,
            }
            
            return Response(stats)
        except Exception as e:
            logger.error(f"Error generating store stats: {str(e)}")
            return Response(
                {'error': 'Failed to generate store statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_actions(self, request):
        """Bulk actions on stores."""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            return Response({'message': 'Bulk actions endpoint'})
        except Exception as e:
            logger.error(f"Error in bulk store actions: {str(e)}")
            return Response(
                {'error': 'Failed to perform bulk actions'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def activate(self, request, pk=None):
        """Activate a store."""
        try:
            store = self.get_object()
            store.activate(request.user)
            serializer = self.get_serializer(store)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error activating store: {str(e)}")
            return Response(
                {'error': 'Failed to activate store'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def deactivate(self, request, pk=None):
        """Deactivate a store."""
        try:
            store = self.get_object()
            store.deactivate(request.user)
            serializer = self.get_serializer(store)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error deactivating store: {str(e)}")
            return Response(
                {'error': 'Failed to deactivate store'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def verify(self, request, pk=None):
        """Verify a store."""
        if not request.user.is_staff:
            return Response({
                "error": "Only staff members can verify stores"
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            store = self.get_object()
            store.verify(request.user)
            serializer = self.get_serializer(store)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error verifying store: {str(e)}")
            return Response(
                {'error': 'Failed to verify store'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def close(self, request, pk=None):
        """Close a store."""
        try:
            store = self.get_object()
            store.close(request.user)
            serializer = self.get_serializer(store)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error closing store: {str(e)}")
            return Response(
                {'error': 'Failed to close store'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get store analytics."""
        try:
            store = self.get_object()
            return Response({'message': 'Analytics endpoint', 'store_id': str(store.id)})
        except Exception as e:
            logger.error(f"Error fetching store analytics: {str(e)}")
            return Response(
                {'error': 'Failed to fetch store analytics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get all products for a specific store."""
        try:
            store = self.get_object()
            
            # Get query parameters for filtering
            category = request.query_params.get('category')
            subcategory = request.query_params.get('subcategory')
            min_price = request.query_params.get('min_price')
            max_price = request.query_params.get('max_price')
            status = request.query_params.get('status', 'published')
            featured = request.query_params.get('featured')
            search = request.query_params.get('search')
            ordering = request.query_params.get('ordering', '-created_at')
            
            # Start with store's products
            products = store.products.all()
            
            # Apply filters
            if category:
                products = products.filter(category__name__icontains=category)
            
            if subcategory:
                products = products.filter(subcategory__name__icontains=subcategory)
            
            if min_price:
                products = products.filter(base_price__gte=min_price)
            
            if max_price:
                products = products.filter(base_price__lte=max_price)
            
            if status:
                products = products.filter(status=status)
            
            if featured:
                products = products.filter(is_featured=True)
            
            if search:
                products = products.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(brand__icontains=search)
                )
            
            # Apply ordering
            products = products.order_by(ordering)
            
            # Pagination
            page = request.query_params.get('page', 1)
            page_size = request.query_params.get('page_size', 20)
            
            paginator = Paginator(products, page_size)
            products_page = paginator.get_page(page)
            
            # Serialize products
            from product.serializers import ProductSerializer
            serializer = ProductSerializer(products_page, many=True, context={'request': request})
            
            return Response({
                'store_id': str(store.id),
                'store_name': store.name,
                'total_products': products.count(),
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'has_next': products_page.has_next(),
                'has_previous': products_page.has_previous(),
                'products': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error fetching products for store {pk}: {str(e)}")
            return Response({
                'error': 'Failed to fetch products',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def featured_products(self, request, pk=None):
        """Get featured products for a specific store."""
        try:
            store = self.get_object()
            products = store.products.filter(is_featured=True, status='published')
            
            from product.serializers import ProductSerializer
            serializer = ProductSerializer(products, many=True, context={'request': request})
            
            return Response({
                'store_id': str(store.id),
                'store_name': store.name,
                'total_featured': products.count(),
                'products': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error fetching featured products for store {pk}: {str(e)}")
            return Response({
                'error': 'Failed to fetch featured products'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def products_by_category(self, request, pk=None):
        """Get products by category for a specific store."""
        try:
            store = self.get_object()
            category = request.query_params.get('category')
            
            if not category:
                return Response({
                    'error': 'Category parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            products = store.products.filter(
                category__name__icontains=category,
                status='published'
            )
            
            from product.serializers import ProductSerializer
            serializer = ProductSerializer(products, many=True, context={'request': request})
            
            return Response({
                'store_id': str(store.id),
                'store_name': store.name,
                'category': category,
                'total_products': products.count(),
                'products': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error fetching products by category for store {pk}: {str(e)}")
            return Response({
                'error': 'Failed to fetch products by category'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def product_categories(self, request, pk=None):
        """Get all product categories available in a store."""
        try:
            store = self.get_object()
            
            # Get unique categories from store's products
            categories = store.products.filter(status='published').values(
                'category__id', 'category__name'
            ).distinct()
            
            return Response({
                'store_id': str(store.id),
                'store_name': store.name,
                'categories': list(categories)
            })
            
        except Exception as e:
            logger.error(f"Error fetching product categories for store {pk}: {str(e)}")
            return Response({
                'error': 'Failed to fetch product categories'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def inventory(self, request, pk=None):
        """Get comprehensive inventory information for a store."""
        try:
            store = self.get_object()
            
            # Get all products for the store
            products = store.products.all()
            
            # Calculate inventory statistics
            total_products = products.count()
            published_products = products.filter(status='published').count()
            draft_products = products.filter(status='draft').count()
            out_of_stock = products.filter(stock=0).count()
            low_stock = products.filter(stock__gt=0, stock__lte=10).count()
            featured_products = products.filter(is_featured=True).count()
            
            # Get products by category
            products_by_category = products.values('category__name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Get low stock products
            low_stock_products = products.filter(stock__gt=0, stock__lte=10).values(
                'id', 'name', 'stock', 'base_price'
            )[:10]  # Limit to 10 items
            
            # Get out of stock products
            out_of_stock_products = products.filter(stock=0).values(
                'id', 'name', 'base_price'
            )[:10]  # Limit to 10 items
            
            return Response({
                'store_id': str(store.id),
                'store_name': store.name,
                'inventory_summary': {
                    'total_products': total_products,
                    'published_products': published_products,
                    'draft_products': draft_products,
                    'out_of_stock': out_of_stock,
                    'low_stock': low_stock,
                    'featured_products': featured_products
                },
                'products_by_category': list(products_by_category),
                'low_stock_products': list(low_stock_products),
                'out_of_stock_products': list(out_of_stock_products)
            })
            
        except Exception as e:
            logger.error(f"Error fetching inventory for store {pk}: {str(e)}")
            return Response({
                'error': 'Failed to fetch inventory information'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        """Get individual store with related data."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, context={'request': request})
            data = serializer.data
            
            # Add related data
            data = self._add_related_data_to_stores([data], request)[0]
            
            return Response(data)
        except Exception as e:
            logger.error(f"Store retrieve error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Error retrieving store: {str(e)}',
                'error_type': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StoreStaffViewSet(viewsets.ModelViewSet):
    """
    Professional ViewSet for StoreStaff model with comprehensive CRUD operations.
    """
    
    queryset = StoreStaff.objects.all().order_by('-joined_at')
    serializer_class = StoreStaffSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    throttle_classes = [UserRateThrottle]
    
    # Filtering options
    filterset_fields = [
        'store', 'user', 'role', 'joined_at',
        'can_manage_products', 'can_manage_orders', 'can_manage_staff', 'can_view_analytics'
    ]
    
    # Search fields
    search_fields = [
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'store__name', 'role'
    ]
    
    # Ordering options
    ordering_fields = [
        'joined_at', 'role', 'last_active'
    ]
    ordering = ['-joined_at']

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Regular users can only see staff from their own stores.
        Staff users can see all staff members.
        """
        queryset = super().get_queryset().filter(deleted_at__isnull=True, is_active=True)
        
        if not self.request.user.is_staff:
            # Users can only see staff from stores they own or are staff at
            user_stores = StoreStaff.objects.filter(
                user=self.request.user,
                deleted_at__isnull=True,
                is_active=True
            ).values_list('store_id', flat=True)
            queryset = queryset.filter(store_id__in=user_stores)
        
        return queryset

    def perform_create(self, serializer):
        """Create staff member with proper permissions."""
        try:
            staff_member = serializer.save(created_by=self.request.user, updated_by=self.request.user)
            logger.info(f"Staff member created: {staff_member.user.username} at {staff_member.store.name}")
            
            # Create notification
            self.create_staff_notification(staff_member, "added")
            
        except Exception as e:
            logger.error(f"Error creating staff member: {str(e)}")
            raise

    def perform_update(self, serializer):
        """Update staff member with logging."""
        try:
            staff_member = serializer.save(updated_by=self.request.user)
            logger.info(f"Staff member updated: {staff_member.user.username}")
            
            # Create notification
            self.create_staff_notification(staff_member, "updated")
            
        except Exception as e:
            logger.error(f"Error updating staff member: {str(e)}")
            raise

    def perform_destroy(self, instance):
        """Soft delete staff member."""
        try:
            instance.soft_delete(self.request.user)
            logger.info(f"Staff member soft deleted: {instance.user.username}")
            
            # Create notification
            self.create_staff_notification(instance, "removed")
            
        except Exception as e:
            logger.error(f"Error soft deleting staff member: {str(e)}")
            raise

    @action(detail=False, methods=['post'])
    def bulk_actions(self, request):
        """Bulk actions on staff members."""
        serializer = BulkStaffActionSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    staff_ids = serializer.validated_data['staff_ids']
                    action = serializer.validated_data['action']
                    role = serializer.validated_data.get('role')
                    
                    staff_members = StoreStaff.objects.filter(
                        id__in=staff_ids,
                        deleted_at__isnull=True,
                        is_active=True
                    )
                    
                    updated_count = 0
                    for staff_member in staff_members:
                        if action == 'assign_role' and role:
                            staff_member.role = role
                            staff_member.updated_by = request.user
                            staff_member.save()
                            updated_count += 1
                    
                    logger.info(f"Bulk {action} performed on {updated_count} staff members")
                    
                    return Response({
                        'message': f'Successfully {action} {updated_count} staff members',
                        'updated_count': updated_count
                    })
                    
            except Exception as e:
                logger.error(f"Error in bulk staff actions: {str(e)}")
                return Response(
                    {'error': 'Failed to perform bulk actions'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_store(self, request):
        """Get all staff for a specific store."""
        store_id = request.query_params.get('store_id')
        if not store_id:
            return Response({
                "error": "Store ID is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            staff = self.get_queryset().filter(store_id=store_id)
            serializer = self.get_serializer(staff, many=True)
            
            return Response({
                'store_id': store_id,
                'total_staff': staff.count(),
                'staff_members': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error fetching staff by store: {str(e)}")
            return Response(
                {'error': 'Failed to fetch staff by store'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Get staff members by role."""
        role = request.query_params.get('role')
        if not role:
            return Response({
                "error": "Role parameter is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            staff = self.get_queryset().filter(role=role)
            serializer = self.get_serializer(staff, many=True)
            
            return Response({
                'role': role,
                'total_staff_with_role': staff.count(),
                'staff_members': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error fetching staff by role: {str(e)}")
            return Response(
                {'error': 'Failed to fetch staff by role'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create_staff_notification(self, staff_member, action):
        """Create notification for staff action."""
        try:
            action_messages = {
                'added': f"You have been added as {staff_member.get_role_display()} to {staff_member.store.name}.",
                'updated': f"Your role at {staff_member.store.name} has been updated.",
                'removed': f"Your access to {staff_member.store.name} has been removed."
            }
            
            notification_type_map = {
                'added': Notification.NotificationType.ACCOUNT_UPDATE,
                'updated': Notification.NotificationType.ACCOUNT_UPDATE,
                'removed': Notification.NotificationType.SYSTEM_ALERT
            }
            
            level_map = {
                'added': Notification.NotificationLevel.SUCCESS,
                'updated': Notification.NotificationLevel.INFO,
                'removed': Notification.NotificationLevel.WARNING
            }
            
            Notification.objects.create(
                recipient=staff_member.user,
                title=f"Staff {action.title()}: {staff_member.store.name}",
                message=action_messages.get(action, f"Your status at {staff_member.store.name} has been {action}."),
                notification_type=notification_type_map.get(action, Notification.NotificationType.ACCOUNT_UPDATE),
                level=level_map.get(action, Notification.NotificationLevel.INFO),
                link=f'/stores/{staff_member.store.id}/staff/'
            )
        except Exception as e:
            logger.error(f"Error creating staff notification: {e}")


class StoreAnalyticsViewSet(viewsets.ModelViewSet):
    """
    Professional ViewSet for StoreAnalytics model.
    """
    
    queryset = StoreAnalytics.objects.all().order_by('-last_updated')
    serializer_class = StoreAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    throttle_classes = [UserRateThrottle]
    
    # Filtering options
    filterset_fields = [
        'store', 'last_updated', 'calculated_at'
    ]
    
    # Ordering options
    ordering_fields = [
        'revenue', 'total_views', 'total_sales', 'conversion_rate',
        'last_updated', 'calculated_at'
    ]
    ordering = ['-last_updated']

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Regular users can only see analytics from their own stores.
        Staff users can see all analytics.
        """
        queryset = super().get_queryset()
        
        if not self.request.user.is_staff:
            # Users can only see analytics from stores they own or are staff at
            user_stores = StoreStaff.objects.filter(
                user=self.request.user,
                deleted_at__isnull=True
            ).values_list('store_id', flat=True)
            queryset = queryset.filter(store_id__in=user_stores)
        
        return queryset

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """Recalculate analytics for a store."""
        try:
            analytics = self.get_object()
            analytics.calculate_analytics()
            
            serializer = self.get_serializer(analytics)
            logger.info(f"Analytics recalculated for store: {analytics.store.name}")
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error recalculating analytics: {str(e)}")
            return Response(
                {'error': 'Failed to recalculate analytics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def report(self, request):
        """Generate analytics report."""
        serializer = StoreAnalyticsReportSerializer(data=request.query_params)
        
        if serializer.is_valid():
            try:
                store_id = serializer.validated_data.get('store_id')
                start_date = serializer.validated_data.get('start_date')
                end_date = serializer.validated_data.get('end_date')
                report_type = serializer.validated_data.get('report_type')
                
                queryset = self.get_queryset()
                
                if store_id:
                    queryset = queryset.filter(store_id=store_id)
                
                if start_date:
                    queryset = queryset.filter(last_updated__gte=start_date)
                
                if end_date:
                    queryset = queryset.filter(last_updated__lte=end_date)
                
                # Generate report based on type
                if report_type == 'sales':
                    report_data = self.generate_sales_report(queryset)
                elif report_type == 'products':
                    report_data = self.generate_products_report(queryset)
                elif report_type == 'customers':
                    report_data = self.generate_customers_report(queryset)
                else:
                    report_data = self.generate_performance_report(queryset)
                
                return Response(report_data)
                
            except Exception as e:
                logger.error(f"Error generating analytics report: {str(e)}")
                return Response(
                    {'error': 'Failed to generate analytics report'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def generate_sales_report(self, queryset):
        """Generate sales report."""
        total_revenue = queryset.aggregate(total=Sum('revenue'))['total'] or 0
        total_orders = queryset.aggregate(total=Sum('total_orders'))['total'] or 0
        average_order_value = queryset.aggregate(avg=Avg('average_order_value'))['avg'] or 0
        
        return {
            'report_type': 'sales',
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'average_order_value': average_order_value,
            'top_performing_stores': list(queryset.order_by('-revenue')[:10].values('store__name', 'revenue'))
        }

    def generate_products_report(self, queryset):
        """Generate products report."""
        total_products = queryset.aggregate(total=Sum('total_products'))['total'] or 0
        active_products = queryset.aggregate(total=Sum('active_products'))['total'] or 0
        
        return {
            'report_type': 'products',
            'total_products': total_products,
            'active_products': active_products,
            'product_activation_rate': round((active_products / total_products) * 100, 2) if total_products > 0 else 0
        }

    def generate_customers_report(self, queryset):
        """Generate customers report."""
        total_customers = queryset.aggregate(total=Sum('total_customers'))['total'] or 0
        repeat_customers = queryset.aggregate(total=Sum('repeat_customers'))['total'] or 0
        avg_retention_rate = queryset.aggregate(avg=Avg('customer_retention_rate'))['avg'] or 0
        
        return {
            'report_type': 'customers',
            'total_customers': total_customers,
            'repeat_customers': repeat_customers,
            'average_retention_rate': avg_retention_rate
        }

    def generate_performance_report(self, queryset):
        """Generate performance report."""
        avg_conversion_rate = queryset.aggregate(avg=Avg('conversion_rate'))['avg'] or 0
        avg_bounce_rate = queryset.aggregate(avg=Avg('bounce_rate'))['avg'] or 0
        total_views = queryset.aggregate(total=Sum('total_views'))['total'] or 0
        
        return {
            'report_type': 'performance',
            'average_conversion_rate': avg_conversion_rate,
            'average_bounce_rate': avg_bounce_rate,
            'total_views': total_views
        }


class ProductByStoreViewSet(viewsets.ModelViewSet):
    """ViewSet for filtering products by store."""
    serializer_class = None  # Will be set dynamically
    queryset = Product.objects.select_related('store', 'category', 'subcategory').prefetch_related('variants', 'reviews')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        """Filter products by store ID."""
        queryset = super().get_queryset()
        store_id = self.request.query_params.get('store', None)
        
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        return queryset

    def list(self, request, *args, **kwargs):
        """Override list method to provide debug information."""
        store_id = request.query_params.get('store', None)
        
        if not store_id:
            return Response({
                "error": "Store parameter is required",
                "debug_info": {
                    "available_stores": list(Store.objects.values('id', 'name'))
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Debug: Check if store exists
            store = Store.objects.filter(id=store_id).first()
            if not store:
                return Response({
                    "error": "Store not found",
                    "debug_info": {
                        "requested_store_id": store_id,
                        "available_stores": list(Store.objects.values('id', 'name'))
                    }
                }, status=status.HTTP_404_NOT_FOUND)

            # Get filtered products
            products = self.get_queryset()
            product_count = products.count()
            
            if product_count == 0:
                return Response({
                    "error": "No products found for this store",
                    "debug_info": {
                        "store_id": store_id,
                        "store_name": store.name,
                        "total_products_in_store": product_count,
                        "total_products_in_system": Product.objects.count()
                    }
                }, status=status.HTTP_404_NOT_FOUND)

            # Use a simple serializer for list view
            from product.serializers import ProductSerializer
            serializer = ProductSerializer(products, many=True)
            
            return Response({
                "data": serializer.data,
                "debug_info": {
                    "store_id": store_id,
                    "store_name": store.name,
                    "total_products_found": product_count
                }
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                "error": "Invalid store ID",
                "debug_info": {
                    "error_details": str(e),
                    "requested_store_id": store_id
                }
            }, status=status.HTTP_400_BAD_REQUEST)


class SimpleStoreViewSet(viewsets.ModelViewSet):
    """Simple store viewset for debugging."""
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [AllowAny]
    
    def list(self, request, *args, **kwargs):
        """Simple list method to test basic functionality."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'status': 'success',
                'count': queryset.count(),
                'data': serializer.data
            })
        except Exception as e:
            logger.error(f"Simple store list error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Error in simple store list: {str(e)}',
                'error_type': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SimpleStoreTestView(APIView):
    """Simple test view for store endpoint."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Simple test endpoint that just returns basic store data."""
        try:
            # Get basic store data
            stores = Store.objects.all()[:10]  # Limit to 10 stores
            
            # Create simple data structure
            store_data = []
            for store in stores:
                store_data.append({
                    'id': str(store.id),
                    'name': store.name,
                    'status': store.status,
                    'is_verified': store.is_verified,
                    'created_at': store.created_at.isoformat() if store.created_at else None,
                })
            
            return Response({
                'status': 'success',
                'message': 'Simple store test successful',
                'count': len(store_data),
                'data': store_data
            })
            
        except Exception as e:
            logger.error(f"Simple store test error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Error in simple store test: {str(e)}',
                'error_type': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StoreViewSetDebugView(APIView):
    """Debug view to test StoreViewSet functionality."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Test the StoreViewSet list method."""
        try:
            # Create a temporary viewset instance
            viewset = StoreViewSet()
            viewset.request = request
            viewset.action = 'list'
            
            # Get the queryset
            queryset = viewset.get_queryset()
            
            # Get the serializer
            serializer_class = viewset.get_serializer_class()
            serializer = serializer_class(queryset, many=True, context={'request': request})
            
            return Response({
                'status': 'success',
                'message': 'StoreViewSet list method works',
                'count': queryset.count(),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"StoreViewSet debug error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Error in StoreViewSet debug: {str(e)}',
                'error_type': type(e).__name__,
                'error_details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MinimalStoreViewSet(viewsets.ModelViewSet):
    """Minimal store viewset for debugging."""
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [AllowAny]
    
    def list(self, request, *args, **kwargs):
        """Simple list method."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'status': 'success',
                'count': queryset.count(),
                'data': serializer.data
            })
        except Exception as e:
            logger.error(f"Minimal store list error: {str(e)}")
            return Response({
                'status': 'error',
                'message': f'Error in minimal store list: {str(e)}',
                'error_type': type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicProductByStoreView(APIView):
    """Public endpoint for getting products by store."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get products for a specific store with filtering and pagination."""
        try:
            store_id = request.query_params.get('store_id')
            
            if not store_id:
                return Response({
                    'error': 'store_id parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the store
            try:
                store = Store.objects.get(id=store_id, status='active', is_verified=True)
            except Store.DoesNotExist:
                return Response({
                    'error': 'Store not found or not active'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get query parameters for filtering
            category = request.query_params.get('category')
            subcategory = request.query_params.get('subcategory')
            min_price = request.query_params.get('min_price')
            max_price = request.query_params.get('max_price')
            featured = request.query_params.get('featured')
            search = request.query_params.get('search')
            ordering = request.query_params.get('ordering', '-created_at')
            
            # Start with store's published products only
            products = store.products.filter(status='published')
            
            # Apply filters
            if category:
                products = products.filter(category__name__icontains=category)
            
            if subcategory:
                products = products.filter(subcategory__name__icontains=subcategory)
            
            if min_price:
                products = products.filter(base_price__gte=min_price)
            
            if max_price:
                products = products.filter(base_price__lte=max_price)
            
            if featured:
                products = products.filter(is_featured=True)
            
            if search:
                products = products.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search) |
                    Q(brand__icontains=search)
                )
            
            # Apply ordering
            products = products.order_by(ordering)
            
            # Pagination
            page = request.query_params.get('page', 1)
            page_size = request.query_params.get('page_size', 20)
            
            paginator = Paginator(products, page_size)
            products_page = paginator.get_page(page)
            
            # Serialize products
            from product.serializers import ProductSerializer
            serializer = ProductSerializer(products_page, many=True, context={'request': request})
            
            return Response({
                'store': {
                    'id': str(store.id),
                    'name': store.name,
                    'description': store.description,
                    'logo': store.logo,
                    'is_verified': store.is_verified
                },
                'total_products': products.count(),
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'has_next': products_page.has_next(),
                'has_previous': products_page.has_previous(),
                'products': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error in public product by store view: {str(e)}")
            return Response({
                'error': 'Failed to fetch products',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
