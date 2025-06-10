from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Coupon
from .serializers import CouponSerializer

class CouponListCreateView(generics.ListCreateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

class CouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

class ValidateCouponView(generics.RetrieveAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'code'

    def retrieve(self, request, *args, **kwargs):
        coupon = self.get_object()
        if not coupon.is_valid:
            return Response(
                {"error": "Coupon is not valid"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(self.get_serializer(coupon).data) 