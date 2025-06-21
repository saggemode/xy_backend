from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ProductViewSet,
    ProductVariantViewSet,
    SubCategoryViewSet,
    FlashSaleViewSet,
    FlashSaleItemViewSet,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'product-variants', ProductVariantViewSet)
router.register(r'flash-sales', FlashSaleViewSet)
router.register(r'flash-sale-items', FlashSaleItemViewSet)


urlpatterns = [
    path('', include(router.urls)),
]