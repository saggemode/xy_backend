from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.response import Response        
from rest_framework.views import APIView
from core.models import Product

from .models import Wishlist
from .serializers import WishlistSerializer, WishlistCreateSerializer

class GetWishList(generics.ListAPIView):
    """
    API view to retrieve the wishlist of the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistSerializer

    def get_queryset(self):
        return Wishlist.objects.filter(userId=self.request.user)

class ToggleWishlist(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        product_id = request.query_params.get('id') 

        if not user_id or not product_id:
            return Response({"error": "User ID and Product ID are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        
        wishlist_item, created = Wishlist.objects.get_or_create(userId=request.user)
        if created:
            wishlist_item.product.add(product)
            return Response({"message": "Product added to wishlist."}, status=status.HTTP_201_CREATED)
        else:
            wishlist_item.product.remove(product)
            return Response({"message": "Product removed from wishlist."}, status=status.HTTP_204_NO_CONTENT)