from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets, permissions
from django.contrib.auth.models import User
import random
from django.db.models import Avg, Count, Sum, Q, F
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import datetime, timedelta
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import Store, StoreAnalytics, StoreStaff
from product.models import Product, ProductVariant

from .serializers import StoreAnalyticsSerializer, StoreSerializer, StoreStaffSerializer
from product.serializers import ProductSerializer


class StoreAnalyticsViewSet(viewsets.ModelViewSet):
    queryset = StoreAnalytics.objects.all()
    serializer_class = StoreAnalyticsSerializer

class StoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing stores with filtering, search, and analytics.
    """
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_verified', 'owner']
    search_fields = ['name', 'description', 'location', 'contact_email']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Store.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by verification status
        is_verified = self.request.query_params.get('is_verified')
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')
        
        # Filter by owner
        owner_id = self.request.query_params.get('owner')
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search) |
                Q(contact_email__icontains=search)
            )
        
        return queryset

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get all products for a specific store."""
        store = self.get_object()
        products = store.products.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def staff(self, request, pk=None):
        """Get all staff members for a specific store."""
        store = self.get_object()
        staff = store.storestaff_set.all()
        serializer = StoreStaffSerializer(staff, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for a specific store."""
        store = self.get_object()
        analytics, created = StoreAnalytics.objects.get_or_create(store=store)
        serializer = StoreAnalyticsSerializer(analytics)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def verified(self, request):
        """Get only verified stores."""
        stores = self.get_queryset().filter(is_verified=True)
        serializer = self.get_serializer(stores, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active stores."""
        stores = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(stores, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='search')
    def search_stores(self, request):
        """Advanced store search with multiple criteria."""
        query = request.query_params.get('q', '')
        category = request.query_params.get('category', '')
        location = request.query_params.get('location', '')
        is_verified = request.query_params.get('is_verified', '')
        
        queryset = self.get_queryset()
        
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(location__icontains=query)
            )
        
        if category:
            queryset = queryset.filter(products__category__name__icontains=category).distinct()
        
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        if is_verified in ['true', 'false']:
            queryset = queryset.filter(is_verified=is_verified == 'true')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'total_count': queryset.count(),
            'search_criteria': {
                'query': query,
                'category': category,
                'location': location,
                'is_verified': is_verified
            }
        })

    @action(detail=False, methods=['get'], url_path='recommended')
    def recommended_stores(self, request):
        """Get recommended stores based on activity."""
        queryset = self.get_queryset().filter(
            is_active=True,
            is_verified=True
        )[:10]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'recommended_stores': serializer.data,
            'criteria': 'Active and verified stores'
        })

    @action(detail=False, methods=['get'], url_path='statistics')
    def store_statistics(self, request):
        """Get comprehensive store statistics."""
        total_stores = Store.objects.count()
        active_stores = Store.objects.filter(is_active=True).count()
        verified_stores = Store.objects.filter(is_verified=True).count()
        total_products = Product.objects.count()
        total_staff = StoreStaff.objects.count()
        
        # Store categories distribution
        store_categories = Store.objects.values('products__category__name').annotate(
            count=Count('id', distinct=True)
        ).exclude(products__category__name__isnull=True)
        
        statistics = {
            'total_stores': total_stores,
            'active_stores': active_stores,
            'verified_stores': verified_stores,
            'inactive_stores': total_stores - active_stores,
            'unverified_stores': total_stores - verified_stores,
            'total_products': total_products,
            'total_staff': total_staff,
            'store_categories': list(store_categories),
            'verification_rate': round((verified_stores / total_stores) * 100, 2) if total_stores > 0 else 0,
            'activation_rate': round((active_stores / total_stores) * 100, 2) if total_stores > 0 else 0
        }
        
        return Response(statistics)

    @action(detail=False, methods=['get'], url_path='homestore')
    def homestore(self, request):
        """Get 5 stores with highest product views for home page display with products and staff included."""
        try:
            # Get all active and verified stores with their analytics
            stores = Store.objects.filter(
                is_active=True,
                is_verified=True
            ).prefetch_related('storeanalytics')
            
            # Create a list of stores with their total views
            stores_with_views = []
            for store in stores:
                # Get total views for this store from analytics
                try:
                    analytics = store.storeanalytics
                    total_views = analytics.total_views if analytics else 0
                except StoreAnalytics.DoesNotExist:
                    total_views = 0
                
                stores_with_views.append({
                    'store': store,
                    'total_views': total_views
                })
            
            # Sort stores by total views (highest first)
            stores_with_views.sort(key=lambda x: x['total_views'], reverse=True)
            
            # Take the top 5 stores (or all if less than 5)
            top_stores = stores_with_views[:5]
            selected_stores = [item['store'] for item in top_stores]
            
            # Create a custom serializer context to include products and staff
            context = self.get_serializer_context()
            context['include_products'] = True
            context['include_staff'] = True
            
            # Serialize the stores with products and staff included
            serializer = self.get_serializer(selected_stores, many=True, context=context)
            
            # Add view information to the response
            response_data = []
            for i, store_data in enumerate(serializer.data):
                store_data['total_views'] = top_stores[i]['total_views']
                response_data.append(store_data)
            
            return Response({
                'home_stores': response_data,
                'total_stores_returned': len(selected_stores),
                'criteria': 'Top stores by product views (active and verified)',
                'message': 'Stores ranked by highest product views for home page display',
                'ranking_info': {
                    'sort_by': 'total_views',
                    'order': 'descending'
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Error retrieving home stores',
                'debug_info': {
                    'error_details': str(e)
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='verify')
    def verify_store(self, request, pk=None):
        """Verify a store (admin only)."""
        if not request.user.is_staff:
            return Response({
                "error": "Only staff members can verify stores"
            }, status=status.HTTP_403_FORBIDDEN)
        
        store = self.get_object()
        store.is_verified = True
        store.save()
        
        serializer = self.get_serializer(store)
        return Response({
            "message": f"Store '{store.name}' has been verified",
            "store": serializer.data
        })

    @action(detail=True, methods=['post'], url_path='activate')
    def activate_store(self, request, pk=None):
        """Activate a store."""
        store = self.get_object()
        store.is_active = True
        store.save()
        
        serializer = self.get_serializer(store)
        return Response({
            "message": f"Store '{store.name}' has been activated",
            "store": serializer.data
        })

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate_store(self, request, pk=None):
        """Deactivate a store."""
        store = self.get_object()
        store.is_active = False
        store.save()
        
        serializer = self.get_serializer(store)
        return Response({
            "message": f"Store '{store.name}' has been deactivated",
            "store": serializer.data
        })

    @action(detail=True, methods=['get'], url_path='analytics')
    def store_analytics(self, request, pk=None):
        """Get detailed analytics for a specific store."""
        store = self.get_object()
        
        # Product statistics
        products = Product.objects.filter(store=store)
        total_products = products.count()
        active_products = products.filter(status='published').count()
        featured_products = products.filter(is_featured=True).count()
        on_sale_products = products.filter(discount_price__isnull=False).count()
        
        # Staff statistics
        total_staff = StoreStaff.objects.filter(store=store).count()
        active_staff = StoreStaff.objects.filter(store=store, is_active=True).count()
        
        # Review statistics
        total_reviews = sum(product.reviews.count() for product in products)
        avg_product_rating = products.aggregate(
            avg_rating=Avg('reviews__rating')
        )['avg_rating'] or 0
        
        analytics = {
            'store_id': store.id,
            'store_name': store.name,
            'products': {
                'total_products': total_products,
                'active_products': active_products,
                'featured_products': featured_products,
                'on_sale_products': on_sale_products,
                'draft_products': total_products - active_products
            },
            'staff': {
                'total_staff': total_staff,
                'active_staff': active_staff,
                'inactive_staff': total_staff - active_staff
            },
            'reviews': {
                'total_reviews': total_reviews,
                'average_rating': round(avg_product_rating, 2)
            },
            'store_status': {
                'is_active': store.is_active,
                'is_verified': store.is_verified,
                'created_at': store.created_at,
                'last_updated': store.updated_at
            }
        }
        
        return Response(analytics)

    @action(detail=True, methods=['get'], url_path='inventory')
    def store_inventory(self, request, pk=None):
        """Get inventory overview for a store."""
        store = self.get_object()
        products = Product.objects.filter(store=store)
        
        # Stock levels
        low_stock_products = products.filter(stock__lt=5)
        out_of_stock_products = products.filter(stock=0)
        well_stocked_products = products.filter(stock__gte=10)
        
        # Category distribution
        category_distribution = products.values('category__name').annotate(
            count=Count('id'),
            total_stock=Sum('stock')
        )
        
        inventory = {
            'store_id': store.id,
            'store_name': store.name,
            'stock_levels': {
                'total_products': products.count(),
                'low_stock_products': low_stock_products.count(),
                'out_of_stock_products': out_of_stock_products.count(),
                'well_stocked_products': well_stocked_products.count()
            },
            'low_stock_alerts': list(low_stock_products.values('id', 'name', 'stock')),
            'out_of_stock_alerts': list(out_of_stock_products.values('id', 'name')),
            'category_distribution': list(category_distribution)
        }
        
        return Response(inventory)

    @action(detail=False, methods=['post'], url_path='bulk-verify')
    def bulk_verify_stores(self, request):
        """Bulk verify multiple stores."""
        if not request.user.is_staff:
            return Response({
                "error": "Only staff members can verify stores"
            }, status=status.HTTP_403_FORBIDDEN)
        
        store_ids = request.data.get('store_ids', [])
        if not store_ids:
            return Response({
                "error": "No store IDs provided"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        stores = Store.objects.filter(id__in=store_ids)
        verified_count = 0
        
        for store in stores:
            store.is_verified = True
            store.save()
            verified_count += 1
        
        return Response({
            "message": f"Successfully verified {verified_count} stores",
            "verified_count": verified_count,
            "total_requested": len(store_ids)
        })

    @action(detail=False, methods=['get'], url_path='filterbyid')
    def filterbyid(self, request):
        """Filter store by ID with detailed statistics."""
        query = request.query_params.get('store-details', None)
        if query:
            try:
                # Debug: Check if store exists
                store = Store.objects.filter(id=query).first()
                if not store:
                    return Response({
                        "error": "Store not found",
                        "debug_info": {
                            "requested_store_id": query,
                            "available_stores": list(Store.objects.values('id', 'name'))
                        }
                    }, status=status.HTTP_404_NOT_FOUND)

                # Get store details
                serializer = self.get_serializer(store)
                
                # Get additional store statistics
                product_count = Product.objects.filter(store_id=query).count()
                staff_count = StoreStaff.objects.filter(store_id=query).count()
                
                return Response({
                    "data": serializer.data,
                    "store_statistics": {
                        "total_products": product_count,
                        "total_staff": staff_count,
                        "store_rating": store.rating if hasattr(store, 'rating') else None,
                        "store_created_at": store.created_at if hasattr(store, 'created_at') else None
                    },
                    "debug_info": {
                        "store_id": query,
                        "store_name": store.name
                    }
                }, status=status.HTTP_200_OK)

            except ValueError as e:
                return Response({
                    "error": "Invalid store ID",
                    "debug_info": {
                        "error_details": str(e),
                        "requested_store_id": query
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                "error": "Store ID parameter is required",
                "debug_info": {
                    "available_stores": list(Store.objects.values('id', 'name'))
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='listall')
    def listall(self, request):
        """List all stores with statistics."""
        try:
            # Get all stores
            stores = Store.objects.all()
            
            # Get store statistics
            store_data = []
            for store in stores:
                store_dict = self.get_serializer(store).data
                store_dict.update({
                    'statistics': {
                        'total_products': Product.objects.filter(store_id=store.id).count(),
                        'total_staff': StoreStaff.objects.filter(store_id=store.id).count(),
                        'store_rating': store.rating if hasattr(store, 'rating') else None,
                        'store_created_at': store.created_at if hasattr(store, 'created_at') else None
                    }
                })
                store_data.append(store_dict)
            
            return Response({
                "data": store_data,
                "total_stores": len(store_data),
                "debug_info": {
                    "total_stores_in_system": Store.objects.count()
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": "Error retrieving stores",
                "debug_info": {
                    "error_details": str(e)
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StoreStaffViewSet(viewsets.ModelViewSet):
    queryset = StoreStaff.objects.all()
    serializer_class = StoreStaffSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['joined_at', 'role', 'is_active']
    ordering = ['-joined_at']

    def get_queryset(self):
        """Enhanced queryset with related data and custom search."""
        try:
            queryset = StoreStaff.objects.select_related('user', 'store').annotate(
                total_products_managed=Count('store__products')
            )
            
            # Custom search functionality
            search_query = self.request.query_params.get('search', None)
            if search_query and search_query.strip():
                queryset = queryset.filter(
                    Q(user__username__icontains=search_query) |
                    Q(user__first_name__icontains=search_query) |
                    Q(user__last_name__icontains=search_query) |
                    Q(role__icontains=search_query)
                )
            
            return queryset
        except Exception as e:
            # Fallback to basic queryset if annotations fail
            return StoreStaff.objects.select_related('user', 'store')

    @action(detail=False, methods=['get'], url_path='by-store')
    def staff_by_store(self, request):
        """Get all staff for a specific store."""
        store_id = request.query_params.get('store_id', None)
        if not store_id:
            return Response({
                "error": "Store ID is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        staff = self.get_queryset().filter(store_id=store_id)
        serializer = self.get_serializer(staff, many=True)
        
        return Response({
            'store_id': store_id,
            'total_staff': staff.count(),
            'active_staff': staff.filter(is_active=True).count(),
            'staff_members': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='by-role')
    def staff_by_role(self, request):
        """Get staff members by role."""
        role = request.query_params.get('role', None)
        if not role:
            return Response({
                "error": "Role parameter is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        staff = self.get_queryset().filter(role=role)
        serializer = self.get_serializer(staff, many=True)
        
        return Response({
            'role': role,
            'total_staff_with_role': staff.count(),
            'staff_members': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='assign-role')
    def assign_role(self, request, pk=None):
        """Assign a role to a staff member."""
        staff_member = self.get_object()
        new_role = request.data.get('role', None)
        
        if not new_role:
            return Response({
                "error": "Role is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate role (you can add more roles as needed)
        valid_roles = ['owner', 'manager', 'staff']
        if new_role not in valid_roles:
            return Response({
                "error": f"Invalid role. Valid roles are: {', '.join(valid_roles)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        staff_member.role = new_role
        staff_member.save()
        
        serializer = self.get_serializer(staff_member)
        return Response({
            "message": f"Role '{new_role}' assigned to {staff_member.user.username}",
            "staff_member": serializer.data
        })

    @action(detail=True, methods=['post'], url_path='activate')
    def activate_staff(self, request, pk=None):
        """Activate a staff member."""
        staff_member = self.get_object()
        staff_member.is_active = True
        staff_member.save()
        
        serializer = self.get_serializer(staff_member)
        return Response({
            "message": f"Staff member {staff_member.user.username} has been activated",
            "staff_member": serializer.data
        })

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate_staff(self, request, pk=None):
        """Deactivate a staff member."""
        staff_member = self.get_object()
        staff_member.is_active = False
        staff_member.save()
        
        serializer = self.get_serializer(staff_member)
        return Response({
            "message": f"Staff member {staff_member.user.username} has been deactivated",
            "staff_member": serializer.data
        })

    @action(detail=True, methods=['get'], url_path='performance')
    def staff_performance(self, request, pk=None):
        """Get performance metrics for a staff member."""
        staff_member = self.get_object()
        store = staff_member.store
        
        # Get products managed by this staff member's store
        products = Product.objects.filter(store=store)
        total_products = products.count()
        active_products = products.filter(status='published').count()
        
        # Calculate performance metrics
        performance = {
            'staff_id': staff_member.id,
            'staff_name': f"{staff_member.user.first_name} {staff_member.user.last_name}",
            'role': staff_member.role,
            'store_name': store.name,
            'is_active': staff_member.is_active,
            'joined_at': staff_member.joined_at,
            'performance_metrics': {
                'total_products_managed': total_products,
                'active_products': active_products,
                'product_activation_rate': round((active_products / total_products) * 100, 2) if total_products > 0 else 0,
                'days_with_store': (datetime.now().date() - staff_member.joined_at.date()).days
            }
        }
        
        return Response(performance)

    @action(detail=False, methods=['post'], url_path='bulk-assign-role')
    def bulk_assign_role(self, request):
        """Bulk assign role to multiple staff members."""
        staff_ids = request.data.get('staff_ids', [])
        role = request.data.get('role', None)
        
        if not staff_ids:
            return Response({
                "error": "No staff IDs provided"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not role:
            return Response({
                "error": "Role is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate role
        valid_roles = ['owner', 'manager', 'staff']
        if role not in valid_roles:
            return Response({
                "error": f"Invalid role. Valid roles are: {', '.join(valid_roles)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        staff_members = StoreStaff.objects.filter(id__in=staff_ids)
        updated_count = 0
        
        for staff_member in staff_members:
            staff_member.role = role
            staff_member.save()
            updated_count += 1
        
        return Response({
            "message": f"Successfully assigned role '{role}' to {updated_count} staff members",
            "updated_count": updated_count,
            "total_requested": len(staff_ids)
        })

    @action(detail=False, methods=['get'], url_path='statistics')
    def staff_statistics(self, request):
        """Get comprehensive staff statistics."""
        total_staff = StoreStaff.objects.count()
        active_staff = StoreStaff.objects.filter(is_active=True).count()
        
        # Role distribution
        role_distribution = StoreStaff.objects.values('role').annotate(
            count=Count('id')
        )
        
        # Store distribution
        store_distribution = StoreStaff.objects.values('store__name').annotate(
            count=Count('id')
        )
        
        statistics = {
            'total_staff': total_staff,
            'active_staff': active_staff,
            'inactive_staff': total_staff - active_staff,
            'activation_rate': round((active_staff / total_staff) * 100, 2) if total_staff > 0 else 0,
            'role_distribution': list(role_distribution),
            'store_distribution': list(store_distribution)
        }
        
        return Response(statistics)

class ProductByStoreViewSet(viewsets.ModelViewSet):
    """ViewSet for filtering products by store."""
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related('store', 'category', 'subcategory').prefetch_related('variants', 'reviews')

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

            serializer = self.get_serializer(products, many=True)
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