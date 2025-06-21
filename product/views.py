from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from django.contrib.auth.models import User
import random
from django.db.models import Count
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
      FlashSale, FlashSaleItem, ProductReview
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


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related('store', 'category', 'subcategory').prefetch_related('variants', 'reviews')

    def get_queryset(self):
        """
        Optionally restricts the returned products by filtering against a
        'category' or 'q' (search) query parameter in the URL.
        """
        queryset = super().get_queryset()

        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        search_query = self.request.query_params.get('q', None)
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        return queryset

    @action(detail=False, methods=['get'], url_path='homeproducts')
    def homeproducts(self, request):
        """Returns 5 random products for the homepage."""
        queryset = list(self.get_queryset())
        random.shuffle(queryset)
        paginated_queryset = self.paginate_queryset(queryset[:5])
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """Returns products from the same category, excluding the product itself."""
        product = self.get_object()
        queryset = self.get_queryset().filter(category=product.category).exclude(id=product.id)[:10]
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='myproducts')
    def myproducts(self, request):
        """
        Returns products for the currently authenticated user, based on
        the stores they own.
        """
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        queryset = self.get_queryset().filter(store__owner=request.user)
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)


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

class FlashSaleViewSet(viewsets.ModelViewSet):
    queryset = FlashSale.objects.all()
    serializer_class = FlashSaleSerializer

class FlashSaleItemViewSet(viewsets.ModelViewSet):
    queryset = FlashSaleItem.objects.all()
    serializer_class = FlashSaleItemSerializer

class ProductReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ProductReviewSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        product_pk = self.kwargs.get('product_pk')
        if product_pk:
            return ProductReview.objects.filter(product_id=product_pk)
        return ProductReview.objects.none()

    def create(self, request, *args, **kwargs):
        product_pk = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_pk)
        user = request.user

        try:
            review = ProductReview.objects.get(product=product, user=user)
            serializer = self.get_serializer(review, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except ProductReview.DoesNotExist:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        product_pk = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_pk)
        serializer.save(user=self.request.user, product=product)



