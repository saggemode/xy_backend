from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets, permissions, filters
from django.contrib.auth.models import User
from rest_framework.decorators import action
import logging
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import datetime
from .models import ShippingAddress
from .serializers import ShippingAddressSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.throttling import UserRateThrottle
from django.utils import timezone

logger = logging.getLogger(__name__)

class ShippingAddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing shipping addresses.
    Now with filtering, searching, ordering, pagination, rate limiting, soft delete, audit logging, and bulk operations.
    Fields: id (UUID), user, address, city, state, country, postal_code, phone, additional_phone, is_default, address_type, created_at, updated_at, full_address (computed), latitude, longitude.
    """
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'state', 'country', 'is_default', 'address_type', 'is_deleted', 'created_at']
    search_fields = ['address', 'city', 'state', 'country', 'postal_code', 'phone']
    ordering_fields = ['created_at', 'updated_at', 'city', 'is_default', 'is_deleted']
    ordering = ['-is_default', '-created_at']
    throttle_classes = [UserRateThrottle]
    pagination_class = None  # Use DRF default or set custom if needed

    def get_queryset(self):
        user = self.request.user
        qs = ShippingAddress.objects.filter(user=user, is_deleted=False)
        if user.is_superuser:
            qs = ShippingAddress.objects.all()
        # Filtering for soft delete
        show_deleted = self.request.query_params.get('show_deleted')
        if show_deleted == '1' and user.is_superuser:
            return ShippingAddress.objects.all()
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        try:
            instance = serializer.save(user=user, created_by=user, updated_by=user)
            logger.info(f"Shipping address created by {user}: {instance}")
        except ValidationError as e:
            logger.error(f"Validation error creating address: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating address: {str(e)}")
            raise

    def perform_update(self, serializer):
        user = self.request.user
        try:
            instance = serializer.save(updated_by=user)
            logger.info(f"Shipping address updated by {user}: {instance}")
        except ValidationError as e:
            logger.error(f"Validation error updating address: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating address: {str(e)}")
            raise

    def perform_destroy(self, instance):
        user = self.request.user
        try:
            instance.soft_delete(user=user)
            logger.info(f"Shipping address soft deleted by {user}: {instance}")
        except Exception as e:
            logger.error(f"Error soft deleting address: {str(e)}")
            raise

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        """Restore a soft-deleted address."""
        try:
            address = self.get_object()
            user = request.user
            if not (user.is_superuser or address.user == user):
                return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
            address.restore(user=user)
            serializer = self.get_serializer(address)
            logger.info(f"Shipping address restored by {user}: {address}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error restoring address: {str(e)}")
            return Response({'detail': 'An error occurred.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='bulk_delete')
    def bulk_delete(self, request):
        """Bulk soft delete addresses by IDs."""
        ids = request.data.get('ids', [])
        user = request.user
        if not ids:
            return Response({'detail': 'No IDs provided.'}, status=status.HTTP_400_BAD_REQUEST)
        addresses = ShippingAddress.objects.filter(id__in=ids, user=user, is_deleted=False)
        count = 0
        for address in addresses:
            address.soft_delete(user=user)
            count += 1
        logger.info(f"Bulk soft deleted {count} addresses by {user}.")
        return Response({'deleted_count': count})

    def create(self, request, *args, **kwargs):
        """Override create to handle validation errors gracefully"""
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            return Response(
                {"error": "Validation error", "details": e.message_dict if hasattr(e, 'message_dict') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Override update to handle validation errors gracefully"""
        try:
            return super().update(request, *args, **kwargs)
        except ValidationError as e:
            return Response(
                {"error": "Validation error", "details": e.message_dict if hasattr(e, 'message_dict') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def with_coordinates(self, request):
        """
        Get addresses that have coordinates (latitude and longitude).
        """
        user = request.user
        if user.is_superuser:
            addresses = ShippingAddress.objects.filter(latitude__isnull=False, longitude__isnull=False)
        else:
            addresses = ShippingAddress.objects.filter(
                user=user, 
                latitude__isnull=False, 
                longitude__isnull=False
            )
        
        serializer = self.get_serializer(addresses, many=True)
        return Response({
            "count": addresses.count(),
            "results": serializer.data
        })

    @action(detail=False, methods=['get'])
    def default(self, request):
        """
        Get the default address for the current user.
        """
        user = request.user
        try:
            default_address = ShippingAddress.objects.get(user=user, is_default=True)
            serializer = self.get_serializer(default_address)
            return Response(serializer.data)
        except ShippingAddress.DoesNotExist:
            return Response(
                {"error": "No default address found for this user"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def debug_info(self, request):
        """
        Debug endpoint to check authentication and user status.
        """
        if not request.user.is_superuser:
            return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
            
        return Response({
            "user_info": {
                "username": request.user.username,
                "id": request.user.id,
                "is_authenticated": request.user.is_authenticated,
                "is_superuser": request.user.is_superuser,
            },
            "request_info": {
                "method": request.method,
                "headers": dict(request.headers),
                "query_params": dict(request.query_params),
            }
        })

    @action(detail=True, methods=['post'], url_path='set_default')
    def set_default(self, request, pk=None):
        """
        Set this address as the default for the current user. Only the owner or a superuser can perform this action.
        """
        try:
            address = self.get_object()
            user = request.user
            if not (user.is_superuser or address.user == user):
                return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
            # Unset other defaults for this user
            ShippingAddress.objects.filter(user=address.user, is_default=True).update(is_default=False)
            address.is_default = True
            address.save()
            serializer = self.get_serializer(address)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ShippingAddress.DoesNotExist:
            return Response({'detail': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error setting default address: {str(e)}")
            return Response({'detail': 'An error occurred.'}, status=status.HTTP_400_BAD_REQUEST)
