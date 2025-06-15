from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q, Sum, F
from .models import Cart
from .serializers import CartSerializer
from product.models import Product

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).select_related('product', 'product__store', 'product__category')

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        # Check if product exists
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if product is already in cart
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = self.get_serializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        quantity = request.data.get('quantity', instance.quantity)
        
        if int(quantity) < 1:
            return Response(
                {'error': 'Quantity must be at least 1'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.quantity = quantity
        instance.save()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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
        """Get current user's cart with total"""
        cart_items = self.get_queryset()
        total = cart_items.aggregate(
            total_items=Sum('quantity'),
            total_price=Sum(F('product__price') * F('quantity'))
        )
        
        serializer = self.get_serializer(cart_items, many=True)
        return Response({
            'items': serializer.data,
            'total_items': total['total_items'] or 0,
            'total_price': total['total_price'] or 0
        })

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
            Q(product__description__icontains=query)
        )
        serializer = self.get_serializer(cart_items, many=True)
        return Response(serializer.data)
