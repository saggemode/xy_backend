from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'carts', views.CartViewSet, basename='cart')

urlpatterns = [
    path('', include(router.urls)),
    path('carts/active/<int:store_id>/', views.ActiveCartView.as_view(), name='active-cart'),
    path('carts/active/<int:store_id>/add-item/', views.ActiveCartView.as_view(), name='active-cart-add-item'),
    path('carts/active/<int:store_id>/remove-item/<int:item_id>/', views.ActiveCartView.as_view(), name='active-cart-remove-item'),
    path('carts/active/<int:store_id>/update-item/<int:item_id>/', views.ActiveCartView.as_view(), name='active-cart-update-item'),
    path('carts/user/', views.UserCartListView.as_view(), name='user-carts'),
    path('carts/count/', views.CartCountView.as_view(), name='cart-count'),
    path('carts/count/<int:store_id>/', views.CartCountView.as_view(), name='cart-count-store'),
]
