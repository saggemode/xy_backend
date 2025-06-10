from django.shortcuts import render
from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from .models import Inventory
from .serializers import InventorySerializer
from .permissions import IsStoreStaff

# Create your views here.

class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated, IsStoreStaff]

    def get_queryset(self):
        return Inventory.objects.filter(store__staff=self.request.user)

    def perform_create(self, serializer):
        serializer.save(store=self.request.user.store)
