from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    CategoryViewSet,
    ProductViewSet,
    ProductVariantViewSet,
    SubCategoryViewSet,
    FlashSaleViewSet,
    FlashSaleItemViewSet,
    ProductReviewViewSet,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'product-variants', ProductVariantViewSet)
router.register(r'flash-sales', FlashSaleViewSet)
router.register(r'flash-sale-items', FlashSaleItemViewSet)

products_router = routers.NestedSimpleRouter(router, r'products', lookup='product')
products_router.register(r'reviews', ProductReviewViewSet, basename='product-reviews')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(products_router.urls)),
]