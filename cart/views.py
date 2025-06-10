from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from .models import Cart, CartItem
from .serializers import (
    CartSerializer, CartItemSerializer,
    AddToCartSerializer, UpdateCartItemSerializer,
    CartTemplateSerializer, MergeCartSerializer,
    SaveCartTemplateSerializer, ApplyCouponSerializer,
    CartNoteSerializer, SaveForLaterSerializer
)
from product.models import Product, ProductVariant
from django.utils import timezone

# Create your views here.

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['store'] = self.request.query_params.get('store')
        return context

    def create(self, request, *args, **kwargs):
        store_id = request.data.get('store')
        if not store_id:
            return Response(
                {"error": "Store ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response(
                {"error": "Store not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        cart = Cart.get_or_create_cart(user=request.user, store=store)
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def merge(self, request, pk=None):
        cart = self.get_object()
        serializer = MergeCartSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                source_cart = Cart.objects.get(
                    id=serializer.validated_data['source_cart_id']
                )
                cart.merge_with(source_cart)
                return Response(
                    self.get_serializer(cart).data,
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def save_as_template(self, request, pk=None):
        cart = self.get_object()
        serializer = SaveCartTemplateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                cart.save_as_template(serializer.validated_data['template_name'])
                return Response(
                    CartTemplateSerializer(cart).data,
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def load_template(self, request, pk=None):
        cart = self.get_object()
        template_id = request.data.get('template_id')
        
        try:
            template_cart = Cart.objects.get(
                id=template_id,
                is_template=True,
                user=request.user
            )
            cart.load_from_template(template_cart)
            return Response(
                self.get_serializer(cart).data,
                status=status.HTTP_200_OK
            )
        except Cart.DoesNotExist:
            return Response(
                {"error": "Template not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def save_for_later(self, request, pk=None):
        cart = self.get_object()
        serializer = SaveForLaterSerializer(
            data=request.data,
            context={'cart': cart}
        )
        
        if serializer.is_valid():
            if cart.save_for_later(serializer.validated_data['item_id']):
                return Response(
                    self.get_serializer(cart).data,
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": "Failed to save item for later"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def move_to_cart(self, request, pk=None):
        cart = self.get_object()
        serializer = SaveForLaterSerializer(
            data=request.data,
            context={'cart': cart}
        )
        
        if serializer.is_valid():
            if cart.move_to_cart(serializer.validated_data['item_id']):
                return Response(
                    self.get_serializer(cart).data,
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": "Failed to move item to cart"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def apply_coupon(self, request, pk=None):
        cart = self.get_object()
        serializer = ApplyCouponSerializer(data=request.data)
        
        if serializer.is_valid():
            if cart.apply_coupon(serializer.validated_data['coupon_code']):
                return Response(
                    self.get_serializer(cart).data,
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": "Invalid or expired coupon"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_coupon(self, request, pk=None):
        cart = self.get_object()
        if cart.remove_coupon():
            return Response(
                self.get_serializer(cart).data,
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "No coupon applied"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def update_notes(self, request, pk=None):
        cart = self.get_object()
        serializer = CartNoteSerializer(data=request.data)
        
        if serializer.is_valid():
            cart.notes = serializer.validated_data.get('notes', '')
            cart.save()
            return Response(
                self.get_serializer(cart).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def recommended_items(self, request, pk=None):
        cart = self.get_object()
        recommended = cart.get_recommended_items()
        return Response(
            ProductSerializer(recommended, many=True).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def recently_viewed(self, request, pk=None):
        cart = self.get_object()
        viewed = cart.get_recently_viewed()
        return Response(
            ProductSerializer(viewed, many=True).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def saved_items(self, request, pk=None):
        cart = self.get_object()
        saved = cart.get_saved_items()
        return Response(
            CartItemSerializer(saved, many=True).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def active_items(self, request, pk=None):
        cart = self.get_object()
        active = cart.get_active_items()
        return Response(
            CartItemSerializer(active, many=True).data,
            status=status.HTTP_200_OK
        )

class ActiveCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id)
            cart = Cart.objects.get(
                user=request.user,
                store=store,
                is_active=True
            )
            serializer = CartSerializer(cart)
            return Response(serializer.data)
        except (Store.DoesNotExist, Cart.DoesNotExist):
            return Response(
                {"error": "No active cart found for this store"},
                status=status.HTTP_404_NOT_FOUND
            )

    def post(self, request, store_id):
        """Add item to active cart"""
        try:
            store = Store.objects.get(id=store_id)
            cart = Cart.objects.get(
                user=request.user,
                store=store,
                is_active=True
            )
        except (Store.DoesNotExist, Cart.DoesNotExist):
            # If no active cart exists, create one
            cart = Cart.get_or_create_cart(user=request.user, store=store)

        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            try:
                cart_item = cart.add_item(
                    product=serializer.validated_data['product'],
                    variant=serializer.validated_data.get('variant'),
                    quantity=serializer.validated_data['quantity']
                )
                return Response(
                    CartItemSerializer(cart_item).data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, store_id, item_id=None):
        """Remove item from active cart"""
        try:
            store = Store.objects.get(id=store_id)
            cart = Cart.objects.get(
                user=request.user,
                store=store,
                is_active=True
            )
            
            if item_id:
                # Remove specific item
                if cart.remove_item(item_id):
                    return Response(status=status.HTTP_204_NO_CONTENT)
                return Response(
                    {"error": "Cart item not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            else:
                # Clear entire cart
                cart.clear()
                return Response(status=status.HTTP_204_NO_CONTENT)
                
        except (Store.DoesNotExist, Cart.DoesNotExist):
            return Response(
                {"error": "No active cart found for this store"},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, store_id, item_id):
        """Update item quantity in active cart"""
        try:
            store = Store.objects.get(id=store_id)
            cart = Cart.objects.get(
                user=request.user,
                store=store,
                is_active=True
            )
            
            try:
                cart_item = cart.items.get(id=item_id)
            except CartItem.DoesNotExist:
                return Response(
                    {"error": "Cart item not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = UpdateCartItemSerializer(
                data=request.data,
                context={'cart_item': cart_item}
            )
            
            if serializer.is_valid():
                try:
                    cart.update_quantity(
                        item_id=item_id,
                        quantity=serializer.validated_data['quantity']
                    )
                    return Response(
                        CartItemSerializer(cart_item).data,
                        status=status.HTTP_200_OK
                    )
                except Exception as e:
                    return Response(
                        {"error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except (Store.DoesNotExist, Cart.DoesNotExist):
            return Response(
                {"error": "No active cart found for this store"},
                status=status.HTTP_404_NOT_FOUND
            )

class UserCartListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get all carts for the current user"""
        carts = Cart.objects.filter(user=request.user)
        serializer = CartSerializer(carts, many=True)
        return Response(serializer.data)

class CartTemplateListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        templates = Cart.objects.filter(
            user=request.user,
            is_template=True
        )
        serializer = CartTemplateSerializer(templates, many=True)
        return Response(serializer.data)

class CartCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, store_id=None):
        """
        Get cart count for the current user.
        If store_id is provided, returns count for that store only.
        """
        try:
            if store_id:
                # Get count for specific store
                store = Store.objects.get(id=store_id)
                cart = Cart.objects.get(
                    user=request.user,
                    store=store,
                    is_active=True
                )
                total_items = cart.items.aggregate(
                    total_count=Sum('quantity')
                )['total_count'] or 0
                total_products = cart.items.count()
                
                return Response({
                    'store_id': store_id,
                    'store_name': store.name,
                    'total_items': total_items,
                    'total_products': total_products,
                    'cart_id': cart.id
                })
            else:
                # Get count for all stores
                carts = Cart.objects.filter(
                    user=request.user,
                    is_active=True
                )
                
                result = []
                for cart in carts:
                    total_items = cart.items.aggregate(
                        total_count=Sum('quantity')
                    )['total_count'] or 0
                    total_products = cart.items.count()
                    
                    result.append({
                        'store_id': cart.store.id,
                        'store_name': cart.store.name,
                        'total_items': total_items,
                        'total_products': total_products,
                        'cart_id': cart.id
                    })
                
                return Response({
                    'total_stores': len(result),
                    'stores': result
                })
                
        except Store.DoesNotExist:
            return Response(
                {"error": "Store not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Cart.DoesNotExist:
            return Response({
                'store_id': store_id,
                'store_name': store.name,
                'total_items': 0,
                'total_products': 0,
                'cart_id': None
            })
