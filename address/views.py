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
        Debug endpoint to check authentication and user status
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
