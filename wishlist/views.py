from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.response import Response        
from rest_framework.views import APIView
from product.models import Product

from .models import Wishlist
from .serializers import WishlistSerializer, WishlistCreateSerializer

class GetWishList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist = Wishlist.objects.filter(user=request.user)
        serializer = WishlistSerializer(wishlist, many=True)
        return Response(serializer.data)

class ToggleWishlist(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            wishlist_item.delete()
            return Response(
                {"message": "Product removed from wishlist"},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {"message": "Product added to wishlist"},
            status=status.HTTP_201_CREATED
        )