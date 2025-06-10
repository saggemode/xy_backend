from django.urls import path
from . import views

urlpatterns = [
    path('', views.CouponListCreateView.as_view(), name='coupon-list-create'),
    path('<int:pk>/', views.CouponDetailView.as_view(), name='coupon-detail'),
    path('validate/<str:code>/', views.ValidateCouponView.as_view(), name='validate-coupon'),
] 