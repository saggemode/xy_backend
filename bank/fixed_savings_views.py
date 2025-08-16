from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import (
    FixedSavingsAccount, FixedSavingsTransaction, FixedSavingsSettings,
    FixedSavingsPurpose, FixedSavingsSource
)
from .fixed_savings_serializers import (
    FixedSavingsAccountSerializer, FixedSavingsAccountCreateSerializer,
    FixedSavingsAccountDetailSerializer, FixedSavingsTransactionSerializer,
    FixedSavingsSettingsSerializer, FixedSavingsSummarySerializer,
    FixedSavingsPayoutSerializer, FixedSavingsAutoRenewalSerializer,
    FixedSavingsInterestRateSerializer, FixedSavingsChoicesSerializer
)
from .fixed_savings_services import FixedSavingsService, FixedSavingsNotificationService

class FixedSavingsAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Fixed Savings Account management
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get fixed savings accounts for the current user"""
        return FixedSavingsAccount.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'create':
            return FixedSavingsAccountCreateSerializer
        elif self.action == 'retrieve':
            return FixedSavingsAccountDetailSerializer
        return FixedSavingsAccountSerializer
    
    def perform_create(self, serializer):
        """Create fixed savings account"""
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get user's fixed savings summary"""
        try:
            summary = FixedSavingsService.get_user_fixed_savings_summary(request.user)
            serializer = FixedSavingsSummarySerializer(summary)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def choices(self, request):
        """Get fixed savings choices (purposes, sources)"""
        serializer = FixedSavingsChoicesSerializer({})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def calculate_interest(self, request):
        """Calculate interest rate for fixed savings"""
        serializer = FixedSavingsInterestRateSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def pay_out(self, request, pk=None):
        """Pay out matured fixed savings"""
        try:
            fixed_savings = self.get_object()
            
            if not fixed_savings.can_be_paid_out:
                return Response(
                    {'error': 'Fixed savings cannot be paid out'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            success = FixedSavingsService.process_maturity_payout(fixed_savings)
            if success:
                return Response({'message': 'Fixed savings paid out successfully'})
            else:
                return Response(
                    {'error': 'Failed to pay out fixed savings'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def auto_renew(self, request, pk=None):
        """Auto-renew fixed savings"""
        try:
            fixed_savings = self.get_object()
            
            if not fixed_savings.auto_renewal_enabled:
                return Response(
                    {'error': 'Auto-renewal is not enabled for this fixed savings'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not fixed_savings.is_mature:
                return Response(
                    {'error': 'Fixed savings has not matured yet'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            new_fixed_savings = FixedSavingsService.process_auto_renewal(fixed_savings)
            if new_fixed_savings:
                serializer = FixedSavingsAccountSerializer(new_fixed_savings)
                return Response({
                    'message': 'Fixed savings auto-renewed successfully',
                    'new_fixed_savings': serializer.data
                })
            else:
                return Response(
                    {'error': 'Failed to auto-renew fixed savings'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active fixed savings accounts"""
        queryset = self.get_queryset().filter(is_active=True, is_matured=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def matured(self, request):
        """Get matured fixed savings accounts"""
        queryset = self.get_queryset().filter(is_matured=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def matured_unpaid(self, request):
        """Get matured but unpaid fixed savings accounts"""
        queryset = self.get_queryset().filter(
            is_matured=True, 
            is_paid_out=False
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search fixed savings accounts"""
        query = request.query_params.get('q', '')
        purpose = request.query_params.get('purpose', '')
        source = request.query_params.get('source', '')
        status_filter = request.query_params.get('status', '')
        
        queryset = self.get_queryset()
        
        # Apply filters
        if query:
            queryset = queryset.filter(
                Q(account_number__icontains=query) |
                Q(purpose_description__icontains=query)
            )
        
        if purpose:
            queryset = queryset.filter(purpose=purpose)
        
        if source:
            queryset = queryset.filter(source=source)
        
        if status_filter:
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True, is_matured=False)
            elif status_filter == 'matured':
                queryset = queryset.filter(is_matured=True)
            elif status_filter == 'paid_out':
                queryset = queryset.filter(is_paid_out=True)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class FixedSavingsTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Fixed Savings Transaction (read-only)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FixedSavingsTransactionSerializer
    
    def get_queryset(self):
        """Get transactions for user's fixed savings accounts"""
        return FixedSavingsTransaction.objects.filter(
            fixed_savings_account__user=self.request.user
        )
    
    @action(detail=False, methods=['get'])
    def by_account(self, request):
        """Get transactions by fixed savings account"""
        account_id = request.query_params.get('account_id')
        if not account_id:
            return Response(
                {'error': 'account_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify the account belongs to the user
            account = FixedSavingsAccount.objects.get(
                id=account_id, 
                user=request.user
            )
            transactions = FixedSavingsTransaction.objects.filter(
                fixed_savings_account=account
            )
            serializer = self.get_serializer(transactions, many=True)
            return Response(serializer.data)
        except FixedSavingsAccount.DoesNotExist:
            return Response(
                {'error': 'Fixed savings account not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get transactions by type"""
        transaction_type = request.query_params.get('type')
        if not transaction_type:
            return Response(
                {'error': 'type parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(transaction_type=transaction_type)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent transactions"""
        limit = int(request.query_params.get('limit', 10))
        queryset = self.get_queryset().order_by('-created_at')[:limit]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class FixedSavingsSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Fixed Savings Settings
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FixedSavingsSettingsSerializer
    
    def get_queryset(self):
        """Get settings for the current user"""
        return FixedSavingsSettings.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create settings for the current user"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_settings(self, request):
        """Get current user's settings"""
        try:
            settings = FixedSavingsSettings.objects.get(user=request.user)
            serializer = self.get_serializer(settings)
            return Response(serializer.data)
        except FixedSavingsSettings.DoesNotExist:
            # Create default settings if they don't exist
            settings = FixedSavingsSettings.objects.create(user=request.user)
            serializer = self.get_serializer(settings)
            return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def update_notifications(self, request):
        """Update notification preferences"""
        try:
            settings = FixedSavingsSettings.objects.get(user=request.user)
        except FixedSavingsSettings.DoesNotExist:
            settings = FixedSavingsSettings.objects.create(user=request.user)
        
        # Update notification preferences
        notification_fields = [
            'maturity_notifications', 'interest_notifications', 'auto_renewal_notifications'
        ]
        
        for field in notification_fields:
            if field in request.data:
                setattr(settings, field, request.data[field])
        
        settings.save()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def update_preferences(self, request):
        """Update user preferences"""
        try:
            settings = FixedSavingsSettings.objects.get(user=request.user)
        except FixedSavingsSettings.DoesNotExist:
            settings = FixedSavingsSettings.objects.create(user=request.user)
        
        # Update preferences
        preference_fields = [
            'default_auto_renewal', 'default_renewal_duration', 'default_source'
        ]
        
        for field in preference_fields:
            if field in request.data:
                setattr(settings, field, request.data[field])
        
        settings.save()
        serializer = self.get_serializer(settings)
        return Response(serializer.data) 