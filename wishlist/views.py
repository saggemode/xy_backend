from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from .models import Wishlist
from .serializers import WishlistSerializer
from product.models import Product

class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product', 'product__store', 'product__category')

    def create(self, request, *args, **kwargs):
        product_id = request.data.get('product_id')
        
        # Check if product exists
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if already in wishlist
        if Wishlist.objects.filter(user=request.user, product=product).exists():
            return Response(
                {'error': 'Product already in wishlist'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Wishlist.DoesNotExist:
            return Response(
                {'error': 'Wishlist item not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def my_wishlist(self, request):
        wishlist_items = self.get_queryset()
        serializer = self.get_serializer(wishlist_items, many=True)
        
        # Add debugging information
        # debug_info = {
        #     'user_authenticated': request.user.is_authenticated,
        #     'user_id': request.user.id if request.user.is_authenticated else None,
        #     'total_wishlist_items': wishlist_items.count(),
        #     'total_wishlist_items_in_db': Wishlist.objects.count(),
        # }
        
        return Response({
            'data': serializer.data,
            # 'debug_info': debug_info
        })

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        wishlist_items = self.get_queryset().filter(
            Q(product__name__icontains=query) |
            Q(product__brand__icontains=query) |
            Q(product__description__icontains=query)
        )
        serializer = self.get_serializer(wishlist_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        wishlist_items = self.get_queryset().filter(product__is_featured=True)
        serializer = self.get_serializer(wishlist_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response(
                {'error': 'Category ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        wishlist_items = self.get_queryset().filter(product__category_id=category_id)
        serializer = self.get_serializer(wishlist_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='toggle')
    def toggle(self, request):
        product_id = request.data.get('product_id')
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)

        wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
        if wishlist_item:
            wishlist_item.delete()
            return Response({'message': 'Product removed from wishlist'})
        else:
            Wishlist.objects.create(user=request.user, product=product)
            return Response({'message': 'Product added to wishlist'})
