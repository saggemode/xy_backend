from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, viewsets, permissions
from django.contrib.auth.models import User
from rest_framework.decorators import action
import logging
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import datetime
from .models import ShippingAddress
from .serializers import ShippingAddressSerializer

logger = logging.getLogger(__name__)

class ShippingAddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing shipping addresses.
    Fields: id (UUID), user, address, city, state, country, postal_code, phone, additional_phone, is_default, address_type, created_at, updated_at, full_address (computed).
    """
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        logger.info(f"User requesting shipping addresses: {user.username} (id: {user.id})")
        logger.info(f"Is superuser: {user.is_superuser}")
        
        try:
            if user.is_superuser:
                addresses = ShippingAddress.objects.all()
            else:
                addresses = ShippingAddress.objects.filter(user=user)
            
            logger.info(f"Found {addresses.count()} shipping addresses")
            return addresses
            
        except Exception as e:
            logger.error(f"Error fetching shipping addresses: {str(e)}")
            return ShippingAddress.objects.none()

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except Exception as e:
            logger.error(f"Error creating shipping address: {str(e)}")
            raise

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
