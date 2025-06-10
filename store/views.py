from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets, permissions
from django.contrib.auth.models import User
import random
from django.db.models import Avg
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import datetime

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

class StoreStaffViewSet(viewsets.ModelViewSet):
    queryset = StoreStaff.objects.all()
    serializer_class = StoreStaffSerializer


class FilterProductsByStore(APIView):
    def get(self, request):
        query = request.query_params.get('store', None)
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

                # Debug: Get products and check count
                products = Product.objects.filter(store_id=query)
                product_count = products.count()
                
                if product_count == 0:
                    return Response({
                        "error": "No products found for this store",
                        "debug_info": {
                            "store_id": query,
                            "store_name": store.name,
                            "total_products_in_store": product_count,
                            "total_products_in_system": Product.objects.count()
                        }
                    }, status=status.HTTP_404_NOT_FOUND)

                serializer = ProductSerializer(products, many=True)
                return Response({
                    "data": serializer.data,
                    "debug_info": {
                        "store_id": query,
                        "store_name": store.name,
                        "total_products_found": product_count
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
                "error": "Store parameter is required",
                "debug_info": {
                    "available_stores": list(Store.objects.values('id', 'name'))
                }
            }, status=status.HTTP_400_BAD_REQUEST)

class FilterStoreById(APIView):
    def get(self, request):
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
                serializer = StoreSerializer(store)
                
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