from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Address, UserVerification
from .serializers import (
    AddressSerializer, UserVerificationSerializer
   
)
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError

# Create your views here.

class AddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user addresses.
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify an address"""
        address = self.get_object()
        try:
            address.verify()
            return Response({'status': 'Address verified successfully'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def banking_valid(self, request):
        """Get addresses valid for banking purposes"""
        addresses = self.get_queryset().filter(is_valid_for_banking=True)
        serializer = self.get_serializer(addresses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set an address as default"""
        address = self.get_object()
        address.is_default = True
        address.save()
        return Response({'status': 'Address set as default'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate an address"""
        address = self.get_object()
        address.deactivate()
        return Response({'status': 'Address deactivated'})


class UserVerificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user verification.
    """
    serializer_class = UserVerificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserVerification.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def generate_otp(self, request):
        """Generate a new OTP"""
        verification = self.get_queryset().first()
        if not verification:
            verification = UserVerification.objects.create(user=request.user)
        
        if not verification.can_attempt_verification():
            return Response(
                {'error': 'Too many attempts. Please try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        otp = verification.generate_new_otp()
        # In a real application, send OTP via email/SMS
        return Response({'status': 'OTP generated successfully'})

    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        """Verify OTP"""
        otp = request.data.get('otp')
        if not otp:
            return Response(
                {'error': 'OTP is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {'error': 'No verification found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not verification.is_otp_valid():
            return Response(
                {'error': 'OTP has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if verification.otp != otp:
            verification.increment_attempts()
            return Response(
                {'error': 'Invalid OTP'},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification.mark_as_verified()
        return Response({'status': 'OTP verified successfully'})

    @action(detail=False, methods=['post'])
    def verify_security_questions(self, request):
        """Verify security questions"""
        answers = request.data.get('answers')
        if not answers:
            return Response(
                {'error': 'Answers are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {'error': 'No verification found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if verification.verify_security_questions(answers):
            verification.mark_as_verified()
            return Response({'status': 'Security questions verified successfully'})
        else:
            verification.increment_attempts()
            return Response(
                {'error': 'Invalid answers'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def verify_document(self, request):
        """Verify user document"""
        document_data = request.data.get('document_data')
        if not document_data:
            return Response(
                {'error': 'Document data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {'error': 'No verification found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if verification.verify_document(document_data):
            return Response({'status': 'Document verification in progress'})
        else:
            return Response(
                {'error': 'Document verification failed'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def verify_biometric(self, request):
        """Verify biometric data"""
        biometric_data = request.data.get('biometric_data')
        if not biometric_data:
            return Response(
                {'error': 'Biometric data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {'error': 'No verification found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if verification.verify_biometric(biometric_data):
            return Response({'status': 'Biometric verification in progress'})
        else:
            return Response(
                {'error': 'Biometric verification failed'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def verification_summary(self, request):
        """Get verification summary"""
        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {'error': 'No verification found'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(verification.get_verification_summary())

    @action(detail=False, methods=['post'])
    def reset_attempts(self, request):
        """Reset verification attempts"""
        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {'error': 'No verification found'},
                status=status.HTTP_404_NOT_FOUND
            )

        verification.reset_attempts()
        return Response({'status': 'Verification attempts reset successfully'})

