from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from django.contrib.auth.models import User
import random
from django.db.models import Count, Avg, Q, F
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

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
        # Use a simpler queryset for random selection
        queryset = Category.objects.all()
        shuffled_queryset = list(queryset)
        random.shuffle(shuffled_queryset)
        
        # Take first 5 items
        selected_categories = shuffled_queryset[:5]
        
        # Now get the full data with annotations for the selected categories
        full_queryset = Category.objects.prefetch_related('subcategories').annotate(
            product_count=Count('products')
        ).filter(id__in=[cat.id for cat in selected_categories])
        
        serializer = self.get_serializer(full_queryset, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related('store', 'category', 'subcategory').prefetch_related('variants', 'reviews')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['brand', 'is_featured', 'status', 'store', 'category', 'subcategory']
    search_fields = ['name', 'description', 'brand']
    ordering_fields = ['name', 'base_price', 'current_price', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Enhanced filtering with price range, stock status, and advanced search.
        """
        queryset = super().get_queryset()

        # Category filter
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Subcategory filter
        subcategory_id = self.request.query_params.get('subcategory', None)
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)

        # Store filter
        store_id = self.request.query_params.get('store', None)
        if store_id:
            queryset = queryset.filter(store_id=store_id)

        # Price range filter
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            queryset = queryset.filter(current_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(current_price__lte=max_price)

        # Stock status filter
        in_stock = self.request.query_params.get('in_stock', None)
        if in_stock == 'true':
            queryset = queryset.filter(stock__gt=0)
        elif in_stock == 'false':
            queryset = queryset.filter(stock=0)

        # On sale filter
        on_sale = self.request.query_params.get('on_sale', None)
        if on_sale == 'true':
            queryset = queryset.filter(discount_price__isnull=False).filter(discount_price__lt=F('base_price'))
        elif on_sale == 'false':
            queryset = queryset.filter(Q(discount_price__isnull=True) | Q(discount_price__gte=F('base_price')))

        # Featured filter
        featured = self.request.query_params.get('featured', None)
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        elif featured == 'false':
            queryset = queryset.filter(is_featured=False)

        # Status filter
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Brand filter
        brand = self.request.query_params.get('brand', None)
        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        # Advanced search
        search_query = self.request.query_params.get('q', None)
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(brand__icontains=search_query) |
                Q(sku__icontains=search_query)
            )

        return queryset

    @action(detail=False, methods=['get'], url_path='homeproducts')
    def homeproducts(self, request):
        """Returns 5 random products for the homepage."""
        # Use a simpler queryset for random selection
        queryset = Product.objects.all()
        shuffled_queryset = list(queryset)
        random.shuffle(shuffled_queryset)
        
        # Take first 5 items
        selected_products = shuffled_queryset[:5]
        
        # Now get the full data with related fields for the selected products
        full_queryset = Product.objects.select_related('store', 'category', 'subcategory').prefetch_related(
            'variants', 'reviews'
        ).filter(id__in=[prod.id for prod in selected_products])
        
        serializer = self.get_serializer(full_queryset, many=True)
        return Response(serializer.data)

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

    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        """Returns only featured products."""
        queryset = self.get_queryset().filter(is_featured=True)
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='on-sale')
    def on_sale(self, request):
        """Returns products that are currently on sale."""
        queryset = self.get_queryset().filter(
            discount_price__isnull=False
        ).filter(discount_price__lt=F('base_price'))
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        """Returns products with low stock (less than 5 items)."""
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        queryset = self.get_queryset().filter(
            store__owner=request.user,
            stock__lt=5
        )
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='popular')
    def popular(self, request):
        """Returns most reviewed products."""
        queryset = self.get_queryset().annotate(
            review_count=Count('reviews'),
            avg_rating=Avg('reviews__rating')
        ).filter(review_count__gt=0).order_by('-review_count', '-avg_rating')
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return self.get_paginated_response(serializer.data) if paginated_queryset is not None else Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='analytics')
    def analytics(self, request, pk=None):
        """Returns product performance metrics."""
        product = self.get_object()
        
        # Get review statistics
        reviews = product.reviews.all()
        total_reviews = reviews.count()
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Rating distribution
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[f'{i}_star'] = reviews.filter(rating=i).count()
        
        analytics_data = {
            'product_id': product.id,
            'product_name': product.name,
            'total_reviews': total_reviews,
            'average_rating': round(avg_rating, 2),
            'rating_distribution': rating_distribution,
            'stock_level': product.stock,
            'is_on_sale': product.on_sale,
            'current_price': str(product.current_price),
            'base_price': str(product.base_price),
            'discount_percentage': round(((product.base_price - product.current_price) / product.base_price) * 100, 2) if product.on_sale else 0,
            'created_at': product.created_at,
            'last_updated': product.updated_at
        }
        
        return Response(analytics_data)

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulkcreate(self, request):
        """Create multiple products at once."""
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        products_data = request.data.get('products', [])
        if not products_data:
            return Response({"error": "No products data provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        created_products = []
        errors = []
        
        for product_data in products_data:
            try:
                serializer = self.get_serializer(data=product_data)
                serializer.is_valid(raise_exception=True)
                product = serializer.save()
                created_products.append(product)
            except Exception as e:
                errors.append(f"Error creating product {product_data.get('name', 'Unknown')}: {str(e)}")
        
        if created_products:
            serializer = self.get_serializer(created_products, many=True)
            response_data = {
                'created_products': serializer.data,
                'total_created': len(created_products),
                'errors': errors
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['patch'], url_path='bulk-update')
    def bulkupdate(self, request):
        """Update multiple products at once."""
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        updates_data = request.data.get('updates', [])
        if not updates_data:
            return Response({"error": "No updates data provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        updated_products = []
        errors = []
        
        for update_data in updates_data:
            product_id = update_data.get('id')
            if not product_id:
                errors.append("Product ID is required for updates")
                continue
                
            try:
                product = Product.objects.get(id=product_id, store__owner=request.user)
                serializer = self.get_serializer(product, data=update_data, partial=True)
                serializer.is_valid(raise_exception=True)
                updated_product = serializer.save()
                updated_products.append(updated_product)
            except Product.DoesNotExist:
                errors.append(f"Product with ID {product_id} not found or not owned by user")
            except Exception as e:
                errors.append(f"Error updating product {product_id}: {str(e)}")
        
        if updated_products:
            serializer = self.get_serializer(updated_products, many=True)
            response_data = {
                'updated_products': serializer.data,
                'total_updated': len(updated_products),
                'errors': errors
            }
            return Response(response_data)
        else:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

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



