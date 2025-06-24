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
        try:
            user = self.request.user
            logger.info(f"User requesting shipping addresses: {user.username} (id: {user.id})")
            logger.info(f"Is superuser: {user.is_superuser}")
            
            if user.is_superuser:
                addresses = ShippingAddress.objects.all()
            else:
                addresses = ShippingAddress.objects.filter(user=user)
            
            logger.info(f"Found {addresses.count()} shipping addresses")
            return addresses
            
        except Exception as e:
            logger.error(f"Error fetching shipping addresses: {str(e)}")
            return ShippingAddress.objects.none()

    def list(self, request, *args, **kwargs):
        """Override list method to add error handling"""
        try:
            logger.info("Starting list method")
            queryset = self.get_queryset()
            logger.info(f"Queryset count: {queryset.count()}")
            
            # Test serialization of first item
            if queryset.exists():
                first_item = queryset.first()
                logger.info(f"First item ID: {first_item.id}")
                try:
                    serializer = self.get_serializer(first_item)
                    logger.info("Serialization test successful")
                except Exception as ser_error:
                    logger.error(f"Serialization error: {str(ser_error)}")
                    raise ser_error
            
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in list method: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {"error": f"An error occurred while fetching addresses: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve method to add error handling"""
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in retrieve method: {str(e)}")
            return Response(
                {"error": "Address not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except Exception as e:
            logger.error(f"Error creating shipping address: {str(e)}")
            raise

    def perform_update(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            logger.error(f"Error updating shipping address: {str(e)}")
            raise

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except Exception as e:
            logger.error(f"Error deleting shipping address: {str(e)}")
            raise

    @action(detail=False, methods=['get'])
    def simple_list(self, request):
        """
        Simple list endpoint that manually handles serialization
        """
        try:
            user = request.user
            logger.info(f"Simple list - User: {user.username} (id: {user.id})")
            
            # Get addresses
            if user.is_superuser:
                addresses = ShippingAddress.objects.all()
            else:
                addresses = ShippingAddress.objects.filter(user=user)
            
            logger.info(f"Simple list - Found {addresses.count()} addresses")
            
            # Manual serialization
            serialized_addresses = []
            for address in addresses:
                try:
                    address_data = {
                        'id': str(address.id),
                        'user': address.user.id,
                        'address': address.address,
                        'city': address.city,
                        'state': address.state,
                        'country': address.country,
                        'postal_code': address.postal_code,
                        'phone': address.phone,
                        'additional_phone': address.additional_phone,
                        'is_default': address.is_default,
                        'address_type': address.address_type,
                        'created_at': address.created_at.isoformat() if address.created_at else None,
                        'updated_at': address.updated_at.isoformat() if address.updated_at else None,
                        'full_address': address.full_address
                    }
                    serialized_addresses.append(address_data)
                except Exception as e:
                    logger.error(f"Simple list - Error serializing address {address.id}: {str(e)}")
                    # Skip problematic addresses
                    continue
            
            logger.info(f"Simple list - Successfully serialized {len(serialized_addresses)} addresses")
            
            return Response({
                "count": len(serialized_addresses),
                "results": serialized_addresses
            })
            
        except Exception as e:
            logger.error(f"Simple list error: {str(e)}")
            import traceback
            logger.error(f"Simple list traceback: {traceback.format_exc()}")
            return Response({
                "error": str(e),
                "error_type": type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def test(self, request):
        """
        Simple test endpoint to debug issues
        """
        try:
            user = request.user
            logger.info(f"Test endpoint - User: {user.username} (id: {user.id})")
            
            # Test basic query
            addresses = ShippingAddress.objects.filter(user=user)
            logger.info(f"Test endpoint - Found {addresses.count()} addresses")
            
            # Test basic data
            if addresses.exists():
                first = addresses.first()
                logger.info(f"Test endpoint - First address: {first.id}, {first.address}, {first.city}")
                
                # Test full_address property
                try:
                    full_addr = first.full_address
                    logger.info(f"Test endpoint - Full address: {full_addr}")
                except Exception as e:
                    logger.error(f"Test endpoint - Full address error: {str(e)}")
                
                # Test __str__ method
                try:
                    str_repr = str(first)
                    logger.info(f"Test endpoint - String repr: {str_repr}")
                except Exception as e:
                    logger.error(f"Test endpoint - String repr error: {str(e)}")
                
                # Test serialization
                try:
                    serializer = self.get_serializer(first)
                    serialized_data = serializer.data
                    logger.info(f"Test endpoint - Serialization successful: {serialized_data}")
                except Exception as e:
                    logger.error(f"Test endpoint - Serialization error: {str(e)}")
                    import traceback
                    logger.error(f"Test endpoint - Serialization traceback: {traceback.format_exc()}")
                    return Response({
                        "status": "serialization_error",
                        "error": str(e),
                        "error_type": type(e).__name__
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                "status": "success",
                "user": user.username,
                "address_count": addresses.count(),
                "message": "Test completed successfully"
            })
            
        except Exception as e:
            logger.error(f"Test endpoint error: {str(e)}")
            import traceback
            logger.error(f"Test endpoint traceback: {traceback.format_exc()}")
            return Response({
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def debug_info(self, request):
        """
        Debug endpoint to check authentication and user status.
        """
        try:
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
        except Exception as e:
            logger.error(f"Error in debug_info: {str(e)}")
            return Response({"error": "Debug info error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
