from django.urls import path, include
from django.contrib import admin
from . import views
from rest_framework.routers import DefaultRouter

from .views import (CategoryViewSet,
                 
                      ProductViewSet, 
                      ProductVariantViewSet,
                      SubCategoryViewSet,
                      PopularProductList,
                      SearchProductByTitle,
                     ProductReviewViewSet
                      
                      )





router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'product-variants', ProductVariantViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('popular-products/', PopularProductList.as_view(), name='popular-products'),
    path('search/', SearchProductByTitle.as_view(), name='search-products'),
    path('home-categories/', views.HomeCategoryList.as_view(), name='home-categories'),
    path('home-products/', views.ProductList.as_view(), name='home-products'),
    path('similar-products/<int:product_id>/', views.HomeSimilarProduct.as_view(), name='similar-products'),
    path('user-similar-products/<int:user_id>/', views.SimilarProductBasedOnUser.as_view(), name='user-similar-products'),
    path('user-products/<int:user_id>/', views.FilterProductsByUser.as_view(), name='user-products'),
    path('category/', views.FilterProductsByCategory.as_view(), name='category-products'),
    path('products/<int:pk>/reviews/', views.ProductReviewViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('products/<int:pk>/reviews/<int:review_id>/', views.ProductReviewViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
  
]