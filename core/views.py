from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from django.contrib.auth.models import User
import random

from .models import (
    Profile, Transaction, Post, Store, Category, Coupon, Product, Review, Order, OrderItem,
    Report, UserVerification, TwoFactorAuth, Role, UserRole, MagicLink, LoginHistory, Wishlist,
    ShippingAddress, Payment, StoreStaff, CustomerLifetimeValue, StoreAnalytics, Like, Follow,
    Notification, SystemSettings, Currency, SubscriptionPlan, Analytics, Refund, FraudDetection,
    LoyaltyProgram, Auction, SearchIndex, RealTimeNotification, RateLimit, Language, Report,
    SocialShare, SecurityLog, ExternalService, GDPRCompliance, Inventory, ProductVariant,
    DynamicPricing, LoyaltyPoints, SearchFilter, AbandonedCart, UserBehavior, SalesReport,
    Group, Message, Repost, Hashtag, Mention, SubCategory
)
from .serializers import (
    ProfileSerializer, TransactionSerializer, PostSerializer, StoreSerializer, CategorySerializer,
    CouponSerializer, ProductSerializer, ReviewSerializer, OrderSerializer, OrderItemSerializer,
    ReportSerializer, UserVerificationSerializer, TwoFactorAuthSerializer, RoleSerializer,
    UserRoleSerializer, MagicLinkSerializer, LoginHistorySerializer, WishlistSerializer,
    ShippingAddressSerializer, PaymentSerializer, StoreStaffSerializer, CustomerLifetimeValueSerializer,
    StoreAnalyticsSerializer, LikeSerializer, FollowSerializer, NotificationSerializer,
    SystemSettingsSerializer, CurrencySerializer, SubscriptionPlanSerializer, AnalyticsSerializer,
    RefundSerializer, FraudDetectionSerializer, LoyaltyProgramSerializer, AuctionSerializer,
    SearchIndexSerializer, RealTimeNotificationSerializer, RateLimitSerializer, LanguageSerializer,
    ReportSerializer, SocialShareSerializer, SecurityLogSerializer, ExternalServiceSerializer,
    GDPRComplianceSerializer, InventorySerializer, ProductVariantSerializer, DynamicPricingSerializer,
    LoyaltyPointsSerializer, SearchFilterSerializer, AbandonedCartSerializer, UserBehaviorSerializer,
    SalesReportSerializer, GroupSerializer, MessageSerializer, RepostSerializer, HashtagSerializer,
    MentionSerializer, UserSerializer, SubCategorySerializer
)
from django.db.models import Count

from xy_backend.core import models

# Create your views here.

class MessageList(generics.ListCreateAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

class GroupList(generics.ListCreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer

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
    queryset = Product.objects.all().order_by('-rating')  # Using rating field instead of popularity
    serializer_class = ProductSerializer


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
            products = models.Product.objects.filter(category__name__icontains=query)
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)     
        else:
            return Response({"error": "Category parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

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

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

class UserVerificationViewSet(viewsets.ModelViewSet):
    queryset = UserVerification.objects.all()
    serializer_class = UserVerificationSerializer

class TwoFactorAuthViewSet(viewsets.ModelViewSet):
    queryset = TwoFactorAuth.objects.all()
    serializer_class = TwoFactorAuthSerializer

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer

class MagicLinkViewSet(viewsets.ModelViewSet):
    queryset = MagicLink.objects.all()
    serializer_class = MagicLinkSerializer

class LoginHistoryViewSet(viewsets.ModelViewSet):
    queryset = LoginHistory.objects.all()
    serializer_class = LoginHistorySerializer

class WishlistViewSet(viewsets.ModelViewSet):
    queryset = Wishlist.objects.all()
    serializer_class = WishlistSerializer

class ShippingAddressViewSet(viewsets.ModelViewSet):
    queryset = ShippingAddress.objects.all()
    serializer_class = ShippingAddressSerializer

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

class StoreStaffViewSet(viewsets.ModelViewSet):
    queryset = StoreStaff.objects.all()
    serializer_class = StoreStaffSerializer

class CustomerLifetimeValueViewSet(viewsets.ModelViewSet):
    queryset = CustomerLifetimeValue.objects.all()
    serializer_class = CustomerLifetimeValueSerializer

class StoreAnalyticsViewSet(viewsets.ModelViewSet):
    queryset = StoreAnalytics.objects.all()
    serializer_class = StoreAnalyticsSerializer

class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all()
    serializer_class = LikeSerializer

class FollowViewSet(viewsets.ModelViewSet):
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

class SystemSettingsViewSet(viewsets.ModelViewSet):
    queryset = SystemSettings.objects.all()
    serializer_class = SystemSettingsSerializer

class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

class AnalyticsViewSet(viewsets.ModelViewSet):
    queryset = Analytics.objects.all()
    serializer_class = AnalyticsSerializer

class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer

class FraudDetectionViewSet(viewsets.ModelViewSet):
    queryset = FraudDetection.objects.all()
    serializer_class = FraudDetectionSerializer

class LoyaltyProgramViewSet(viewsets.ModelViewSet):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer

class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer

class SearchIndexViewSet(viewsets.ModelViewSet):
    queryset = SearchIndex.objects.all()
    serializer_class = SearchIndexSerializer

class RealTimeNotificationViewSet(viewsets.ModelViewSet):
    queryset = RealTimeNotification.objects.all()
    serializer_class = RealTimeNotificationSerializer

class RateLimitViewSet(viewsets.ModelViewSet):
    queryset = RateLimit.objects.all()
    serializer_class = RateLimitSerializer

class LanguageViewSet(viewsets.ModelViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

class SocialShareViewSet(viewsets.ModelViewSet):
    queryset = SocialShare.objects.all()
    serializer_class = SocialShareSerializer

class SecurityLogViewSet(viewsets.ModelViewSet):
    queryset = SecurityLog.objects.all()
    serializer_class = SecurityLogSerializer

class ExternalServiceViewSet(viewsets.ModelViewSet):
    queryset = ExternalService.objects.all()
    serializer_class = ExternalServiceSerializer

class GDPRComplianceViewSet(viewsets.ModelViewSet):
    queryset = GDPRCompliance.objects.all()
    serializer_class = GDPRComplianceSerializer

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer

class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer

class DynamicPricingViewSet(viewsets.ModelViewSet):
    queryset = DynamicPricing.objects.all()
    serializer_class = DynamicPricingSerializer

class LoyaltyPointsViewSet(viewsets.ModelViewSet):
    queryset = LoyaltyPoints.objects.all()
    serializer_class = LoyaltyPointsSerializer

class SearchFilterViewSet(viewsets.ModelViewSet):
    queryset = SearchFilter.objects.all()
    serializer_class = SearchFilterSerializer

class AbandonedCartViewSet(viewsets.ModelViewSet):
    queryset = AbandonedCart.objects.all()
    serializer_class = AbandonedCartSerializer

class UserBehaviorViewSet(viewsets.ModelViewSet):
    queryset = UserBehavior.objects.all()
    serializer_class = UserBehaviorSerializer

class SalesReportViewSet(viewsets.ModelViewSet):
    queryset = SalesReport.objects.all()
    serializer_class = SalesReportSerializer

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

class RepostViewSet(viewsets.ModelViewSet):
    queryset = Repost.objects.all()
    serializer_class = RepostSerializer

class HashtagViewSet(viewsets.ModelViewSet):
    queryset = Hashtag.objects.all()
    serializer_class = HashtagSerializer

class MentionViewSet(viewsets.ModelViewSet):
    queryset = Mention.objects.all()
    serializer_class = MentionSerializer

class SearchProductByTitle(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        title = self.request.query_params.get('title', '')
        return Product.objects.filter(title__icontains=title)

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer

    def get_queryset(self):
        category_id = self.request.query_params.get('category', None)
        if category_id:
            return SubCategory.objects.filter(category_id=category_id)
        return SubCategory.objects.all()
