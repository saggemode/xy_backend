from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from django.contrib.auth.models import User
import random
from django.db.models import Avg
from django.contrib.auth.decorators import login_required

from datetime import datetime
from django.db.models import Count

from .serializers import (
    CategorySerializer, SubCategorySerializer, ProductSerializer,
    ProductVariantSerializer, BundleSerializer, BundleItemSerializer,
    CouponSerializer, CouponUsageSerializer, FlashSaleSerializer,
    FlashSaleItemSerializer, DynamicPricingSerializer, SearchFilterSerializer,
    ProductReviewSerializer, SubscriptionSerializer, SubscriptionItemSerializer,
    UserSubscriptionSerializer, LoyaltyProgramSerializer, LoyaltyPointsSerializer,
    GDPRComplianceSerializer, AuctionSerializer
)

from .models import (
    Category, SubCategory, Product, ProductVariant, Coupon, Bundle,
    BundleItem, CouponUsage, FlashSale, FlashSaleItem, DynamicPricing,
    SearchFilter, ProductReview, Subscription, SubscriptionItem,
    UserSubscription, LoyaltyProgram, LoyaltyPoints, GDPRCompliance,
    Auction
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryList(generics.ListAPIView):
    # queryset = Category.objects.annotate(product_count=Count('products')).order_by('-product_count')
    serializer_class = CategorySerializer 
    queryset = Category.objects.all()
    def get_queryset(self):
        return Category.objects.annotate(product_count=Count('products')).order_by('-product_count')  


class HomeCategoryList(generics.ListAPIView):
    serializer_class = CategorySerializer

    def get_queryset(self):
        # Assuming you want to return a random selection of categories
        queryset = Category.objects.all()

        queryset = queryset.annotate(random_order=Count('id'))
        
        queryset = list(queryset)
        random.shuffle(queryset)
        
        return queryset[:5]  # Randomly select 10 categories

class ProductList(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        # Assuming you want to return a random selection of categories
        queryset = Product.objects.all()

        queryset = queryset.annotate(random_order=Count('id'))
        
        queryset = list(queryset)
        random.shuffle(queryset)
        
        return queryset[:5]  # Randomly select 10 categories

class PopularProductList(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.annotate(
            avg_rating=Avg('reviews__rating')
        ).order_by('-avg_rating')


class HomeSimilarProduct(APIView):
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            similar_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:10]
            serializer = ProductSerializer(similar_products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)


class SimilarProductBasedOnUser(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            # Assuming you have a method to get similar products based on user preferences
            similar_products = Product.objects.filter(preferences__user=user)[:10]
            serializer = ProductSerializer(similar_products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class FilterProductsByUser(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            products = Product.objects.filter(user=user)
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
class FilterProductsByCategory(APIView):
    def get(self, request):
        query = request.query_params.get('category', None)
        if query:
            try:
                # Debug: Check if category exists
                category = Category.objects.filter(id=query).first()
                if not category:
                    return Response({
                        "error": "Category not found",
                        "debug_info": {
                            "requested_category_id": query,
                            "available_categories": list(Category.objects.values('id', 'name'))
                        }
                    }, status=status.HTTP_404_NOT_FOUND)

                # Debug: Get products and check count
                products = Product.objects.filter(category_id=query)
                product_count = products.count()
                
                if product_count == 0:
                    return Response({
                        "error": "No products found for this category",
                        "debug_info": {
                            "category_id": query,
                            "category_name": category.name,
                            "total_products_in_category": product_count,
                            "total_products_in_system": Product.objects.count()
                        }
                    }, status=status.HTTP_404_NOT_FOUND)

                serializer = ProductSerializer(products, many=True)
                return Response({
                    "data": serializer.data,
                    "debug_info": {
                        "category_id": query,
                        "category_name": category.name,
                        "total_products_found": product_count
                    }
                }, status=status.HTTP_200_OK)

            except ValueError as e:
                return Response({
                    "error": "Invalid category ID",
                    "debug_info": {
                        "error_details": str(e),
                        "requested_category_id": query
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                "error": "Category parameter is required",
                "debug_info": {
                    "available_categories": list(Category.objects.values('id', 'name'))
                }
            }, status=status.HTTP_400_BAD_REQUEST)


class SearchProductByTitle(APIView):
    def get(self, request):
        title = request.query_params.get('title', '')
        if not title:
            return Response({"error": "Title parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        products = Product.objects.filter(title__icontains=title)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
   

class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


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
    


class SearchProductByTitle(APIView):
    def get(self, request):
        query = request.query_params.get('q', None)

        if query:
            products = Product.objects.filter(name__icontains=query)
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Query parameter 'q' is required"}, status=status.HTTP_400_BAD_REQUEST)

class ProductReviewViewSet(viewsets.ModelViewSet):
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer

class FlashSaleViewSet(viewsets.ModelViewSet):
    queryset = FlashSale.objects.all()
    serializer_class = FlashSaleSerializer

class FlashSaleItemViewSet(viewsets.ModelViewSet):
    queryset = FlashSaleItem.objects.all()
    serializer_class = FlashSaleItemSerializer

class DynamicPricingViewSet(viewsets.ModelViewSet):
    queryset = DynamicPricing.objects.all()
    serializer_class = DynamicPricingSerializer

class SearchFilterViewSet(viewsets.ModelViewSet):
    queryset = SearchFilter.objects.all()
    serializer_class = SearchFilterSerializer

class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

class SubscriptionItemViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionItem.objects.all()
    serializer_class = SubscriptionItemSerializer

class UserSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = UserSubscription.objects.all()
    serializer_class = UserSubscriptionSerializer

class LoyaltyProgramViewSet(viewsets.ModelViewSet):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer

class LoyaltyPointsViewSet(viewsets.ModelViewSet):
    queryset = LoyaltyPoints.objects.all()
    serializer_class = LoyaltyPointsSerializer

class GDPRComplianceViewSet(viewsets.ModelViewSet):
    queryset = GDPRCompliance.objects.all()
    serializer_class = GDPRComplianceSerializer

class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer



