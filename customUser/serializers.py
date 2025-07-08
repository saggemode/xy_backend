from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomRegisterSerializer(RegisterSerializer):
    full_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data['full_name'] = self.validated_data.get('full_name', '')
        data['phone'] = self.validated_data.get('phone', '')
        return data

    def create(self, validated_data):
        user = super().create(validated_data)
        user.full_name = validated_data.get('full_name', '')
        user.phone = validated_data.get('phone', '')
        user.save()
        return user
