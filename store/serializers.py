from rest_framework import serializers
from .models import (
    Store, 
    StoreAnalytics,
    StoreStaff,

)
from product.models import Product, ProductVariant
from django.contrib.auth.models import User

class StoreStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreStaff
        fields = '__all__'

class StoreAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreAnalytics
        fields = '__all__'

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = '__all__'
  
