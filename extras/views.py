from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Address, UserVerification
from .serializers import AddressSerializer, UserVerificationSerializer

class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get user's default address"""
        address = self.get_queryset().filter(is_default=True).first()
        if not address:
            return Response(
                {"error": "No default address found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(address)
        return Response(serializer.data)

    # @action(detail=True, methods=['post'])
    # def set_default(self, request, pk=None):
    #     """Set an address as default"""
    #     address = self.get_object()
    #     address.is_default = True
    #     address.save()
    #     serializer = self.get_serializer(address)
    #     return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set an address as default"""
        # Get all addresses for this user and set is_default to False
        self.get_queryset().update(is_default=False)
        
        # Set the selected address as default
        address = self.get_object()
        address.is_default = True
        address.save()
        
        serializer = self.get_serializer(address)
        return Response(serializer.data)




class UserVerificationViewSet(viewsets.ModelViewSet):
    serializer_class = UserVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserVerification.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def generate_otp(self, request):
        """Generate a new OTP"""
        verification = self.get_queryset().first()
        if not verification:
            verification = UserVerification.objects.create(
                user=request.user
            )
        
        if not verification.can_attempt_verification():
            return Response(
                {"error": "Too many attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        otp = verification.generate_new_otp()
        # Here you would typically send the OTP via email/SMS
        return Response({
            "message": "OTP generated successfully",
            "expires_in": 600  # 10 minutes
        })

    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        """Verify OTP"""
        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {"error": "No verification found"},
                status=status.HTTP_404_NOT_FOUND
            )

        otp = request.data.get('otp')
        if not otp:
            return Response(
                {"error": "OTP is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not verification.is_otp_valid():
            return Response(
                {"error": "OTP has expired"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if verification.otp != otp:
            verification.increment_attempts()
            return Response(
                {"error": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification.mark_as_verified()
        return Response({
            "message": "OTP verified successfully",
            "is_verified": verification.is_verified
        })

    @action(detail=False, methods=['post'])
    def verify_security_questions(self, request):
        """Verify security questions"""
        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {"error": "No verification found"},
                status=status.HTTP_404_NOT_FOUND
            )

        answers = request.data.get('answers')
        if not answers:
            return Response(
                {"error": "Answers are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if verification.verify_security_questions(answers):
            verification.mark_as_verified()
            return Response({
                "message": "Security questions verified successfully",
                "is_verified": verification.is_verified
            })
        return Response(
            {"error": "Invalid answers"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['post'])
    def verify_document(self, request):
        """Verify document"""
        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {"error": "No verification found"},
                status=status.HTTP_404_NOT_FOUND
            )

        document_data = request.data
        if verification.verify_document(document_data):
            return Response({
                "message": "Document verification initiated",
                "status": verification.verification_status
            })
        return Response(
            {"error": "Invalid document data"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['post'])
    def verify_biometric(self, request):
        """Verify biometric data"""
        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {"error": "No verification found"},
                status=status.HTTP_404_NOT_FOUND
            )

        biometric_data = request.data
        if verification.verify_biometric(biometric_data):
            return Response({
                "message": "Biometric verification initiated",
                "status": verification.verification_status
            })
        return Response(
            {"error": "Invalid biometric data"},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get verification status"""
        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {"error": "No verification found"},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(verification.get_verification_summary())

    @action(detail=False, methods=['post'])
    def reset_attempts(self, request):
        """Reset verification attempts"""
        verification = self.get_queryset().first()
        if not verification:
            return Response(
                {"error": "No verification found"},
                status=status.HTTP_404_NOT_FOUND
            )
        verification.reset_attempts()
        return Response({'status': 'Verification attempts reset successfully'})
