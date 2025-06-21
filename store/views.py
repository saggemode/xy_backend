from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets, permissions
from django.contrib.auth.models import User
import random
from django.db.models import Avg, Count
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import datetime
from rest_framework.decorators import action

from .models import Store, StoreAnalytics, StoreStaff
from product.models import Product, ProductVariant

from .serializers import StoreAnalyticsSerializer, StoreSerializer, StoreStaffSerializer
from product.serializers import ProductSerializer


class StoreAnalyticsViewSet(viewsets.ModelViewSet):
    queryset = StoreAnalytics.objects.all()
    serializer_class = StoreAnalyticsSerializer

class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer

    @action(detail=False, methods=['get'], url_path='filterbyid')
    def filterbyid(self, request):
        """Filter store by ID with detailed statistics."""
        query = request.query_params.get('store-details', None)
        if query:
            try:
                # Debug: Check if store exists
                store = Store.objects.filter(id=query).first()
                if not store:
                    return Response({
                        "error": "Store not found",
                        "debug_info": {
                            "requested_store_id": query,
                            "available_stores": list(Store.objects.values('id', 'name'))
                        }
                    }, status=status.HTTP_404_NOT_FOUND)

                # Get store details
                serializer = self.get_serializer(store)
                
                # Get additional store statistics
                product_count = Product.objects.filter(store_id=query).count()
                staff_count = StoreStaff.objects.filter(store_id=query).count()
                
                return Response({
                    "data": serializer.data,
                    "store_statistics": {
                        "total_products": product_count,
                        "total_staff": staff_count,
                        "store_rating": store.rating if hasattr(store, 'rating') else None,
                        "store_created_at": store.created_at if hasattr(store, 'created_at') else None
                    },
                    "debug_info": {
                        "store_id": query,
                        "store_name": store.name
                    }
                }, status=status.HTTP_200_OK)

            except ValueError as e:
                return Response({
                    "error": "Invalid store ID",
                    "debug_info": {
                        "error_details": str(e),
                        "requested_store_id": query
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                "error": "Store ID parameter is required",
                "debug_info": {
                    "available_stores": list(Store.objects.values('id', 'name'))
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='listall')
    def listall(self, request):
        """List all stores with statistics."""
        try:
            # Get all stores
            stores = Store.objects.all()
            
            # Get store statistics
            store_data = []
            for store in stores:
                store_dict = self.get_serializer(store).data
                store_dict.update({
                    'statistics': {
                        'total_products': Product.objects.filter(store_id=store.id).count(),
                        'total_staff': StoreStaff.objects.filter(store_id=store.id).count(),
                        'store_rating': store.rating if hasattr(store, 'rating') else None,
                        'store_created_at': store.created_at if hasattr(store, 'created_at') else None
                    }
                })
                store_data.append(store_dict)
            
            return Response({
                "data": store_data,
                "total_stores": len(store_data),
                "debug_info": {
                    "total_stores_in_system": Store.objects.count()
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": "Error retrieving stores",
                "debug_info": {
                    "error_details": str(e)
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StoreStaffViewSet(viewsets.ModelViewSet):
    queryset = StoreStaff.objects.all()
    serializer_class = StoreStaffSerializer

class ProductByStoreViewSet(viewsets.ModelViewSet):
    """ViewSet for filtering products by store."""
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related('store', 'category', 'subcategory').prefetch_related('variants', 'reviews')

    def get_queryset(self):
        """Filter products by store ID."""
        queryset = super().get_queryset()
        store_id = self.request.query_params.get('store', None)
        
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        
        return queryset

    def list(self, request, *args, **kwargs):
        """Override list method to provide debug information."""
        store_id = request.query_params.get('store', None)
        
        if not store_id:
            return Response({
                "error": "Store parameter is required",
                "debug_info": {
                    "available_stores": list(Store.objects.values('id', 'name'))
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Debug: Check if store exists
            store = Store.objects.filter(id=store_id).first()
            if not store:
                return Response({
                    "error": "Store not found",
                    "debug_info": {
                        "requested_store_id": store_id,
                        "available_stores": list(Store.objects.values('id', 'name'))
                    }
                }, status=status.HTTP_404_NOT_FOUND)

            # Get filtered products
            products = self.get_queryset()
            product_count = products.count()
            
            if product_count == 0:
                return Response({
                    "error": "No products found for this store",
                    "debug_info": {
                        "store_id": store_id,
                        "store_name": store.name,
                        "total_products_in_store": product_count,
                        "total_products_in_system": Product.objects.count()
                    }
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = self.get_serializer(products, many=True)
            return Response({
                "data": serializer.data,
                "debug_info": {
                    "store_id": store_id,
                    "store_name": store.name,
                    "total_products_found": product_count
                }
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                "error": "Invalid store ID",
                "debug_info": {
                    "error_details": str(e),
                    "requested_store_id": store_id
                }
            }, status=status.HTTP_400_BAD_REQUEST)