from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, F
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from .models import Cart
from .serializers import (
    CartSerializer, CartCreateSerializer, CartUpdateSerializer,
    CartSummarySerializer, CartBulkUpdateSerializer
)
from product.models import Product, ProductVariant
from store.models import Store
import logging

logger = logging.getLogger(__name__)

class CartViewSet(viewsets.ModelViewSet):
    """
    Production-ready Cart ViewSet with comprehensive functionality
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product__name', 'product__description', 'store__name']
    ordering_fields = ['created_at', 'updated_at', 'quantity', 'total_price']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get user's cart items with optimized queries"""
        return Cart.objects.filter(
            user=self.request.user
        ).select_related(
            'product', 'product__store', 'store', 'variant'
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return CartCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CartUpdateSerializer
        return CartSerializer

    def perform_create(self, serializer):
        """Create cart item with user assignment"""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Update cart item"""
        serializer.save()

    def perform_destroy(self, instance):
        """Delete cart item"""
        instance.delete()

    @action(detail=False, methods=['get'])
    def get_user_cart(self, request):
        """Get current user's cart with detailed information"""
        try:
            cart_items = self.get_queryset()
            
            if not cart_items.exists():
                return Response({
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'cart_items': [],
                    'total_items': 0,
                    'total_price': 0,
                    'item_count': 0,
                    'store': None,
                    'message': 'Your cart is empty'
                })

            # Calculate totals safely
            total_items = 0
            total_price = 0
            
            for item in cart_items:
                total_items += item.quantity
                try:
                    total_price += item.total_price
                except Exception as e:
                    logger.warning(f"Error calculating total price for item {item.id}: {str(e)}")
                    # Use a fallback calculation
                    if item.variant:
                        total_price += item.variant.current_price * item.quantity
                    elif item.product:
                        total_price += item.product.current_price * item.quantity

            store = cart_items.first().store if cart_items.exists() else None

            # Serialize cart items with error handling
            try:
                serializer = CartSerializer(cart_items, many=True)
                cart_data = serializer.data
            except Exception as e:
                logger.error(f"Error serializing cart items: {str(e)}")
                # Fallback to basic data
                cart_data = []
                for item in cart_items:
                    cart_data.append({
                        'id': str(item.id),
                        'quantity': item.quantity,
                        'selected_size': item.selected_size,
                        'selected_color': item.selected_color,
                        'created_at': item.created_at.isoformat() if item.created_at else None,
                        'updated_at': item.updated_at.isoformat() if item.updated_at else None
                    })
            
            response_data = {
                'user_id': request.user.id,
                'username': request.user.username,
                'cart_items': cart_data,
                'total_items': total_items,
                'total_price': total_price,
                'item_count': cart_items.count(),
                'store': None
            }
            
            # Add store info if available
            if store:
                response_data['store'] = {
                    'id': str(store.id),
                    'name': store.name,
                    'status': getattr(store, 'status', 'unknown')
                }
            
            # Add last updated if available
            try:
                if cart_items.exists():
                    latest_item = cart_items.latest('updated_at')
                    response_data['last_updated'] = latest_item.updated_at.isoformat() if latest_item.updated_at else None
            except Exception as e:
                logger.warning(f"Error getting last updated: {str(e)}")
                response_data['last_updated'] = None
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error getting user cart: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': 'Failed to fetch your cart', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    @method_decorator(vary_on_cookie)
    def summary(self, request):
        """Get cart summary with totals"""
        try:
            cart_items = self.get_queryset()
            
            if not cart_items.exists():
                return Response({
                    'total_items': 0,
                    'total_price': 0,
                    'item_count': 0,
                    'store': None,
                    'items': []
                })

            total_items = sum(item.quantity for item in cart_items)
            total_price = sum(item.total_price for item in cart_items)
            store = cart_items.first().store

            # Calculate sale information
            original_total_price = 0
            total_savings = 0
            items_on_sale = 0
            
            for item in cart_items:
                if item.variant:
                    original_price = item.variant.base_price
                    current_price = item.variant.current_price
                else:
                    original_price = item.product.original_price
                    current_price = item.product.current_price
                
                original_total_price += original_price * item.quantity
                total_savings += (original_price - current_price) * item.quantity
                
                if item.product.on_sale or (item.variant and item.variant.current_price != item.variant.base_price):
                    items_on_sale += 1
            
            serializer = CartSummarySerializer({
                'total_items': total_items,
                'total_price': total_price,
                'original_total_price': original_total_price,
                'total_savings': total_savings,
                'items_on_sale': items_on_sale,
                'item_count': cart_items.count(),
                'store': store,
                'items': cart_items
            })
            
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error in cart summary: {str(e)}")
            return Response(
                {'error': 'Failed to fetch cart summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart with validation"""
        try:
            serializer = CartCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Check if item already exists
            existing_item = self.get_queryset().filter(
                product=serializer.validated_data['product'],
                variant=serializer.validated_data.get('variant'),
                store=serializer.validated_data['store']
            ).first()

            if existing_item:
                # Update quantity
                new_quantity = existing_item.quantity + serializer.validated_data.get('quantity', 1)
                existing_item.quantity = new_quantity
                existing_item.save()
                cart_serializer = CartSerializer(existing_item)
                return Response(cart_serializer.data, status=status.HTTP_200_OK)
            else:
                # Create new item
                cart_item = serializer.save(user=request.user)
                cart_serializer = CartSerializer(cart_item)
                return Response(cart_serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error adding item to cart: {str(e)}")
            return Response(
                {'error': 'Failed to add item to cart'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update cart items"""
        try:
            updates = request.data.get('updates', [])
            if not updates:
                return Response(
                    {'error': 'No updates provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            results = []
            errors = []

            for update_data in updates:
                serializer = CartBulkUpdateSerializer(data=update_data)
                if serializer.is_valid():
                    try:
                        cart_item = self.get_queryset().get(id=serializer.validated_data['cart_id'])
                        cart_item.quantity = serializer.validated_data['quantity']
                        cart_item.save()
                        results.append({
                            'id': str(cart_item.id),
                            'quantity': cart_item.quantity,
                            'status': 'success'
                        })
                    except Cart.DoesNotExist:
                        errors.append({
                            'id': serializer.validated_data['cart_id'],
                            'error': 'Cart item not found'
                        })
                else:
                    errors.append({
                        'id': update_data.get('cart_id'),
                        'error': serializer.errors
                    })

            return Response({
                'success': results,
                'errors': errors
            })

        except Exception as e:
            logger.error(f"Error in bulk update: {str(e)}")
            return Response(
                {'error': 'Failed to update cart items'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all items from cart"""
        try:
            cart_items = self.get_queryset()
            count = cart_items.count()
            
            cart_items.delete()
            
            return Response({
                'message': f'Cleared {count} items from cart',
                'cleared_count': count
            })
        except Exception as e:
            logger.error(f"Error clearing cart: {str(e)}")
            return Response(
                {'error': 'Failed to clear cart'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get cart item count with comprehensive information"""
        try:
            cart_items = self.get_queryset()
            
            if not cart_items.exists():
                return Response({
                    'item_count': 0,
                    'total_quantity': 0,
                    'total_price': 0,
                    'has_items': False,
                    'store_count': 0,
                    'stores': [],
                    'message': 'Your cart is empty'
                })

            # Calculate comprehensive counts
            item_count = cart_items.count()
            total_quantity = sum(item.quantity for item in cart_items)
            
            # Calculate total price with error handling
            total_price = 0
            for item in cart_items:
                try:
                    total_price += item.total_price
                except Exception as e:
                    logger.warning(f"Error calculating total price for item {item.id}: {str(e)}")
                    # Fallback calculation
                    if item.variant:
                        total_price += item.variant.current_price * item.quantity
                    elif item.product:
                        total_price += item.product.current_price * item.quantity

            # Get unique stores
            stores = cart_items.values('store__id', 'store__name', 'store__status').distinct()
            store_count = stores.count()
            stores_list = [
                {
                    'id': str(store['store__id']),
                    'name': store['store__name'],
                    'status': store['store__status']
                }
                for store in stores
            ]

            return Response({
                'item_count': item_count,
                'total_quantity': total_quantity,
                'total_price': total_price,
                'has_items': True,
                'store_count': store_count,
                'stores': stores_list,
                'last_updated': cart_items.latest('updated_at').updated_at.isoformat() if cart_items.exists() else None
            })
            
        except Exception as e:
            logger.error(f"Error getting cart count: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': 'Failed to get cart count', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search cart items"""
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart_items = self.get_queryset().filter(
                Q(product__name__icontains=query) |
                Q(product__description__icontains=query) |
                Q(store__name__icontains=query) |
                Q(variant__name__icontains=query)
            )
            
            serializer = CartSerializer(cart_items, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error searching cart: {str(e)}")
            return Response(
                {'error': 'Failed to search cart'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def move_to_wishlist(self, request):
        """Move cart items to wishlist"""
        try:
            cart_ids = request.data.get('cart_ids', [])
            if not cart_ids:
                return Response(
                    {'error': 'No cart items specified'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Import here to avoid circular imports
            from wishlist.models import Wishlist
            
            results = []
            errors = []

            for cart_id in cart_ids:
                try:
                    cart_item = self.get_queryset().get(id=cart_id)
                    
                    # Create wishlist item
                    wishlist_item, created = Wishlist.objects.get_or_create(
                        user=request.user,
                        product=cart_item.product,
                        store=cart_item.store,
                        defaults={'variant': cart_item.variant}
                    )
                    
                    # Remove from cart
                    cart_item.delete()
                    
                    results.append({
                        'id': str(cart_id),
                        'status': 'success',
                        'message': 'Moved to wishlist'
                    })
                except Cart.DoesNotExist:
                    errors.append({
                        'id': cart_id,
                        'error': 'Cart item not found'
                    })
                except Exception as e:
                    errors.append({
                        'id': cart_id,
                        'error': str(e)
                    })

            return Response({
                'success': results,
                'errors': errors
            })
        except Exception as e:
            logger.error(f"Error moving to wishlist: {str(e)}")
            return Response(
                {'error': 'Failed to move items to wishlist'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def validate_stock(self, request):
        """Validate stock availability for all cart items"""
        try:
            cart_items = self.get_queryset()
            validation_results = []
            
            for item in cart_items:
                stock = item.variant.stock if item.variant else item.product.stock
                is_available = stock >= item.quantity
                
                validation_results.append({
                    'id': str(item.id),
                    'product_name': item.product.name,
                    'variant_name': item.variant.name if item.variant else None,
                    'requested_quantity': item.quantity,
                    'available_stock': stock,
                    'is_available': is_available,
                    'shortage': max(0, item.quantity - stock) if not is_available else 0
                })
            
            return Response(validation_results)
        except Exception as e:
            logger.error(f"Error validating stock: {str(e)}")
            return Response(
                {'error': 'Failed to validate stock'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def low_stock_items(self, request):
        """Get cart items with low stock"""
        try:
            threshold = int(request.query_params.get('threshold', 5))
            low_stock_items = []
            
            for item in self.get_queryset():
                stock = item.variant.stock if item.variant else item.product.stock
                if stock <= threshold:
                    low_stock_items.append(item)
            
            serializer = CartSerializer(low_stock_items, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error getting low stock items: {str(e)}")
            return Response(
                {'error': 'Failed to get low stock items'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
