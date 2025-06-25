from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q, Sum, F, Count
from .models import Cart
from .serializers import CartSerializer
from product.models import Product, ProductVariant
from store.models import Store
from django.utils import timezone
from django.contrib.auth.models import User
from store.serializers import StoreSerializer
import logging

logger = logging.getLogger(__name__)

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).select_related(
            'product', 'product__store', 'product__category', 'store', 'variant'
        )

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product_id')
        variant_id = request.data.get('variant_id')
        quantity = int(request.data.get('quantity', 1))
        selected_size = request.data.get('selected_size')
        selected_color = request.data.get('selected_color')
        
        # Check if product exists
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get variant if provided
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product)
            except ProductVariant.DoesNotExist:
                return Response(
                    {'error': 'Variant not found for this product'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Get the store from the product
        store = product.store

        # Check if user has items from a different store in their cart
        existing_cart_items = Cart.objects.filter(user=request.user)
        if existing_cart_items.exists():
            first_item = existing_cart_items.first()
            if first_item.store != store:
                return Response(
                    {'error': 'Cannot add products from different stores. Please clear your cart first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            # Use the add_to_cart helper method
            cart_item = Cart.add_to_cart(
                user=request.user,
                product=product,
                quantity=quantity,
                variant=variant,
                size=selected_size,
                color=selected_color
            )
            serializer = self.get_serializer(cart_item)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        quantity = request.data.get('quantity', instance.quantity)
        selected_size = request.data.get('selected_size', instance.selected_size)
        selected_color = request.data.get('selected_color', instance.selected_color)
        
        try:
            instance.quantity = quantity
            instance.selected_size = selected_size
            instance.selected_color = selected_color
            instance.save()
            
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        """Get current user's cart with totals"""
        try:
            cart_items = self.get_queryset()
            
            if not cart_items.exists():
                return Response({
                    'store': None,
                    'items': [],
                    'total_items': 0,
                    'total_price': 0
                })

            # Get store from first item (all items should be from same store)
            store = cart_items.first().store
            if not store:
                return Response({
                    'error': 'Store not found for items in cart'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate totals
            total_items = sum(item.quantity for item in cart_items)
            total_price = sum(item.total_price for item in cart_items)

            serializer = self.get_serializer(cart_items, many=True)
            return Response({
                'store': StoreSerializer(store).data if store else None,
                'items': serializer.data,
                'total_items': total_items,
                'total_price': total_price
            })
        except Exception as e:
            logger.error(f"Error in my_cart: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {"error": "An error occurred while fetching your cart"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear all items from cart"""
        self.get_queryset().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search cart items by product name, brand, or description"""
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_items = self.get_queryset().filter(
            Q(product__name__icontains=query) |
            Q(product__brand__icontains=query) |
            Q(product__description__icontains=query) |
            Q(variant__name__icontains=query)
        )
        serializer = self.get_serializer(cart_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get a summary of the cart including item count, total price, and store info"""
        try:
            cart_items = self.get_queryset()
            
            if not cart_items.exists():
                return Response({
                    'store': None,
                    'total_items': 0,
                    'total_price': 0,
                    'item_count': 0,
                    'has_variants': False
                })

            store = cart_items.first().store
            total_items = sum(item.quantity for item in cart_items)
            total_price = sum(item.total_price for item in cart_items)
            has_variants = any(item.variant for item in cart_items)

            return Response({
                'store': StoreSerializer(store).data if store else None,
                'total_items': total_items,
                'total_price': total_price,
                'item_count': cart_items.count(),
                'has_variants': has_variants,
                'last_updated': cart_items.latest('updated_at').updated_at
            })
        except Exception as e:
            logger.error(f"Error in cart summary: {str(e)}")
            return Response(
                {"error": "An error occurred while fetching cart summary"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Update multiple cart items at once"""
        updates = request.data.get('updates', [])
        if not updates:
            return Response(
                {'error': 'No updates provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = []
        errors = []

        for update in updates:
            cart_id = update.get('id')
            quantity = update.get('quantity')
            
            try:
                cart_item = self.get_queryset().get(id=cart_id)
                cart_item.quantity = quantity
                cart_item.save()
                results.append({
                    'id': cart_id,
                    'status': 'success',
                    'quantity': quantity
                })
            except Cart.DoesNotExist:
                errors.append({
                    'id': cart_id,
                    'error': 'Cart item not found'
                })
            except ValidationError as e:
                errors.append({
                    'id': cart_id,
                    'error': str(e)
                })

        return Response({
            'success': results,
            'errors': errors
        })

    @action(detail=False, methods=['get'])
    def store_summary(self, request):
        """Get a summary of cart items grouped by store"""
        cart_items = self.get_queryset()
        
        store_summary = {}
        for item in cart_items:
            store = item.store
            if store.id not in store_summary:
                store_summary[store.id] = {
                    'store': StoreSerializer(store).data,
                    'total_items': 0,
                    'total_price': 0,
                    'item_count': 0
                }
            
            store_summary[store.id]['total_items'] += item.quantity
            store_summary[store.id]['total_price'] += item.total_price
            store_summary[store.id]['item_count'] += 1

        return Response(list(store_summary.values()))

    @action(detail=False, methods=['get'])
    def recent_items(self, request):
        """Get recently added items to cart"""
        days = int(request.query_params.get('days', 7))
        date_threshold = timezone.now() - timezone.timedelta(days=days)
        
        recent_items = self.get_queryset().filter(
            created_at__gte=date_threshold
        ).order_by('-created_at')
        
        serializer = self.get_serializer(recent_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def move_to_wishlist(self, request):
        """Move cart items to wishlist"""
        from wishlist.models import Wishlist  # Import here to avoid circular import
        
        cart_ids = request.data.get('cart_ids', [])
        if not cart_ids:
            return Response(
                {'error': 'No cart items specified'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = []
        errors = []

        for cart_id in cart_ids:
            try:
                cart_item = self.get_queryset().get(id=cart_id)
                
                # Create wishlist item
                wishlist_item, created = Wishlist.objects.get_or_create(
                    user=request.user,
                    product=cart_item.product,
                    store=cart_item.store
                )
                
                # Remove from cart
                cart_item.delete()
                
                results.append({
                    'id': cart_id,
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

    @action(detail=False, methods=['get'])
    def low_stock_items(self, request):
        """Get cart items that are low in stock"""
        threshold = int(request.query_params.get('threshold', 5))
        
        low_stock_items = []
        for item in self.get_queryset():
            stock = item.variant.stock if item.variant else item.product.stock
            if stock <= threshold:
                low_stock_items.append(item)
        
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def validate_stock(self, request):
        """Validate stock availability for all cart items"""
        cart_items = self.get_queryset()
        validation_results = []
        
        for item in cart_items:
            stock = item.variant.stock if item.variant else item.product.stock
            is_available = stock >= item.quantity
            
            validation_results.append({
                'id': item.id,
                'product': item.product.name,
                'variant': item.variant.name if item.variant else None,
                'requested_quantity': item.quantity,
                'available_stock': stock,
                'is_available': is_available
            })
        
        return Response(validation_results)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get the total number of items in the cart and total quantity"""
        cart_items = self.get_queryset()
        
        # Get total number of unique items
        unique_items_count = cart_items.count()
        
        # Get total quantity of all items
        total_quantity = cart_items.aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0
        
        # Get count by store
        store_counts = cart_items.values('store__name').annotate(
            item_count=Count('id'),
            total_quantity=Sum('quantity')
        )

        return Response({
            'unique_items': unique_items_count,
            'total_quantity': total_quantity,
            'store_breakdown': store_counts,
            'has_items': unique_items_count > 0
        })

    @action(detail=False, methods=['get'])
    def user_cart_count(self, request):
        """Get the cart count for a specific user"""
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get cart items for the specific user
        cart_items = Cart.objects.filter(user=user)
        
        # Get total number of unique items
        unique_items_count = cart_items.count()
        
        # Get total quantity of all items
        total_quantity = cart_items.aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0
        
        # Get count by store
        store_counts = cart_items.values('store__name').annotate(
            item_count=Count('id'),
            total_quantity=Sum('quantity')
        )

        # Get product categories breakdown
        category_counts = cart_items.values(
            'product__category__name'
        ).annotate(
            item_count=Count('id'),
            total_quantity=Sum('quantity')
        )

        return Response({
            'user': {
                'id': user.id,
                'username': user.username
            },
            'cart_summary': {
                'unique_items': unique_items_count,
                'total_quantity': total_quantity,
                'has_items': unique_items_count > 0
            },
            'store_breakdown': store_counts,
            'category_breakdown': category_counts,
            'last_updated': cart_items.latest('updated_at').updated_at if cart_items.exists() else None
        })
