from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from django.contrib.auth.models import User
import random
from django.db.models import Avg, Count
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import action

from datetime import datetime

from .serializers import (
    CategorySerializer, SubCategorySerializer, ProductSerializer,
    ProductVariantSerializer,
      FlashSaleSerializer,
    FlashSaleItemSerializer, ProductReviewSerializer
)

from .models import (
    Category, SubCategory, Product, ProductVariant,
      FlashSale, FlashSaleItem,
    ProductReview, 
)

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()

    def get_queryset(self):
        return Category.objects.prefetch_related('subcategories').annotate(product_count=Count('products')).order_by('-product_count')

    @action(detail=False, methods=['get'], url_path='home')
    def homecategories(self, request):
        """Returns 5 random categories for the homepage."""
        queryset = self.get_queryset()
        shuffled_queryset = list(queryset)
        random.shuffle(shuffled_queryset)
        
        paginated_queryset = self.paginate_queryset(shuffled_queryset[:5])
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)


# Temporarily simplified for debugging the 500 error.
# The original, more complex view is commented out below.
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

# class ProductViewSet(viewsets.ModelViewSet):
#     serializer_class = ProductSerializer
#     queryset = Product.objects.all()

#     def get_queryset(self):
#         """
#         Optionally restricts the returned products by filtering against a
#         'category' or 'q' (search) query parameter in the URL.
#         """
#         queryset = Product.objects.select_related('store', 'category', 'subcategory').prefetch_related('variants').annotate(
#             rating=Coalesce(Avg('reviews__rating'), 0.0),
#             review_count=Count('reviews')
#         )

#         category_id = self.request.query_params.get('category', None)
#         if category_id:
#             queryset = queryset.filter(category_id=category_id)

#         search_query = self.request.query_params.get('q', None)
#         if search_query:
#             queryset = queryset.filter(name__icontains=search_query)

#         return queryset

#     @action(detail=False, methods=['get'])
#     def popular(self, request):
#         """Returns products ordered by their average rating."""
#         queryset = self.get_queryset().order_by('-rating')
#         paginated_queryset = self.paginate_queryset(queryset)
#         serializer = self.get_serializer(paginated_queryset, many=True)
#         return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)

#     @action(detail=False, methods=['get'], url_path='homeproducts')
#     def homeproducts(self, request):
#         """Returns 5 random products for the homepage."""
#         queryset = list(self.get_queryset())
#         random.shuffle(queryset)
#         paginated_queryset = self.paginate_queryset(queryset[:5])
#         serializer = self.get_serializer(paginated_queryset, many=True)
#         return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)

#     @action(detail=True, methods=['get'])
#     def similar(self, request, pk=None):
#         """Returns products from the same category, excluding the product itself."""
#         product = self.get_object()
#         queryset = self.get_queryset().filter(category=product.category).exclude(id=product.id)[:10]
#         paginated_queryset = self.paginate_queryset(queryset)
#         serializer = self.get_serializer(paginated_queryset, many=True)
#         return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)

#     @action(detail=False, methods=['get'], url_path='myproducts')
#     def myproducts(self, request):
#         """
#         Returns products for the currently authenticated user, based on
#         the stores they own.
#         """
#         if not request.user.is_authenticated:
#             return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

#         queryset = self.get_queryset().filter(store__owner=request.user)
#         paginated_queryset = self.paginate_queryset(queryset)
#         serializer = self.get_serializer(paginated_queryset, many=True)
#         return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)


class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer

    def get_queryset(self):
        category_id = self.request.query_params.get('category', None)
        if category_id:
            return SubCategory.objects.filter(category_id=category_id)
        return SubCategory.objects.all()

class ProductReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ProductReviewSerializer
    queryset = ProductReview.objects.all()

    def get_queryset(self):
        """
        Optionally restricts the returned reviews to a given product
        by filtering against a `product` query parameter in the URL.
        """
        queryset = ProductReview.objects.select_related('user', 'product__store')
        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        """Associate the review with the currently authenticated user."""
        serializer.save(user=self.request.user)

class FlashSaleViewSet(viewsets.ModelViewSet):
    queryset = FlashSale.objects.all()
    serializer_class = FlashSaleSerializer

class FlashSaleItemViewSet(viewsets.ModelViewSet):
    queryset = FlashSaleItem.objects.all()
    serializer_class = FlashSaleItemSerializer



