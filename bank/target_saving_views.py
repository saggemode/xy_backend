from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Q, Sum, Avg, Count
from django.http import HttpResponse
import csv
import io

from .models import TargetSaving, TargetSavingDeposit, TargetSavingCategory, TargetSavingFrequency
from .target_saving_services import TargetSavingService, TargetSavingNotificationService
from .target_saving_serializers import (
    TargetSavingSerializer, TargetSavingCreateSerializer, TargetSavingUpdateSerializer,
    TargetSavingDepositSerializer, TargetSavingDepositCreateSerializer
)
from notification.models import Notification, NotificationType
from notification.serializers import NotificationSerializer


class TargetSavingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing target savings
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TargetSavingSerializer
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return TargetSavingCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TargetSavingUpdateSerializer
        return TargetSavingSerializer
    
    def get_queryset(self):
        """Filter queryset to show only user's target savings"""
        return TargetSaving.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create target saving with service layer"""
        data = serializer.validated_data
        
        # Convert dates if they're strings
        if isinstance(data.get('start_date'), str):
            data['start_date'] = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if isinstance(data.get('end_date'), str):
            data['end_date'] = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        result = TargetSavingService.create_target_saving(self.request.user, **data)
        
        if result['success']:
            serializer.instance = result['target_saving']
        else:
            raise ValidationError(result['message'])
    
    def perform_update(self, serializer):
        """Update target saving with service layer"""
        target_id = self.get_object().id
        data = serializer.validated_data
        
        result = TargetSavingService.update_target_saving(self.request.user, target_id, **data)
        
        if result['success']:
            serializer.instance = result['target_saving']
        else:
            raise ValidationError(result['message'])
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get available target saving categories"""
        categories = [
            {'value': choice[0], 'label': choice[1]} 
            for choice in TargetSavingCategory.choices
        ]
        return Response({
            'success': True,
            'categories': categories
        })
    
    @action(detail=False, methods=['get'])
    def frequencies(self, request):
        """Get available frequency options"""
        frequencies = [
            {'value': choice[0], 'label': choice[1]} 
            for choice in TargetSavingFrequency.choices
        ]
        return Response({
            'success': True,
            'frequencies': frequencies
        })
    
    @action(detail=False, methods=['get'])
    def deposit_days(self, request):
        """Get available deposit days for weekly/monthly frequency"""
        days = [
            {'value': 'monday', 'label': 'Monday'},
            {'value': 'tuesday', 'label': 'Tuesday'},
            {'value': 'wednesday', 'label': 'Wednesday'},
            {'value': 'thursday', 'label': 'Thursday'},
            {'value': 'friday', 'label': 'Friday'},
            {'value': 'saturday', 'label': 'Saturday'},
            {'value': 'sunday', 'label': 'Sunday'},
        ]
        return Response({
            'success': True,
            'days': days
        })
    
    @action(detail=False, methods=['get'])
    def notifications(self, request):
        """Get target saving related notifications for the user"""
        notifications = Notification.objects.filter(
            recipient=request.user,
            source='target_saving'
        ).order_by('-created_at')[:50]
        
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            'success': True,
            'notifications': serializer.data,
            'count': notifications.count()
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of user's target savings"""
        targets = self.get_queryset()
        
        # Calculate summary statistics
        total_targets = targets.count()
        active_targets = targets.filter(is_active=True).count()
        completed_targets = targets.filter(is_completed=True).count()
        overdue_targets = targets.filter(is_active=True, end_date__lt=timezone.now().date()).count()
        
        # Calculate total amounts
        total_target_amount = targets.aggregate(Sum('target_amount'))['target_amount__sum'] or 0
        total_current_amount = targets.aggregate(Sum('current_amount'))['current_amount__sum'] or 0
        total_progress = (total_current_amount / total_target_amount * 100) if total_target_amount > 0 else 0
        
        # Get category breakdown
        category_breakdown = targets.values('category').annotate(
            count=Count('id'),
            total_target=Sum('target_amount'),
            total_current=Sum('current_amount')
        )
        
        return Response({
            'success': True,
            'summary': {
                'total_targets': total_targets,
                'active_targets': active_targets,
                'completed_targets': completed_targets,
                'overdue_targets': overdue_targets,
                'total_target_amount': float(total_target_amount),
                'total_current_amount': float(total_current_amount),
                'total_progress_percentage': float(total_progress),
                'category_breakdown': list(category_breakdown)
            }
        })
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue target savings"""
        overdue_targets = self.get_queryset().filter(
            is_active=True,
            end_date__lt=timezone.now().date(),
            is_completed=False
        )
        
        return Response({
            'success': True,
            'overdue_targets': self.get_serializer(overdue_targets, many=True).data,
            'count': overdue_targets.count()
        })
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get completed target savings"""
        completed_targets = self.get_queryset().filter(is_completed=True)
        
        return Response({
            'success': True,
            'completed_targets': self.get_serializer(completed_targets, many=True).data,
            'count': completed_targets.count()
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a target saving"""
        target = self.get_object()
        result = TargetSavingService.deactivate_target(request.user, target.id)
        
        if result['success']:
            return Response({
                'success': True,
                'message': 'Target saving deactivated successfully'
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def make_deposit(self, request, pk=None):
        """Make a deposit to a target saving"""
        target = self.get_object()
        amount = request.data.get('amount')
        notes = request.data.get('notes', '')
        
        if not amount:
            return Response({
                'success': False,
                'message': 'Amount is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = TargetSavingService.make_deposit(request.user, target.id, amount, notes)
        
        if result['success']:
            return Response({
                'success': True,
                'message': 'Deposit made successfully',
                'deposit': {
                    'id': str(result['deposit'].id),
                    'amount': float(result['deposit'].amount),
                    'notes': result['deposit'].notes,
                    'deposit_date': result['deposit'].deposit_date.isoformat()
                },
                'target_saving': {
                    'id': str(result['target_saving'].id),
                    'name': result['target_saving'].name,
                    'current_amount': float(result['target_saving'].current_amount),
                    'progress_percentage': float(result['target_saving'].progress_percentage),
                    'is_completed': result['target_saving'].is_completed
                }
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Get detailed information about a target saving"""
        target = self.get_object()
        result = TargetSavingService.get_target_details(request.user, target.id)
        
        if result['success']:
            # Get recent deposits
            recent_deposits = []
            for deposit in result['recent_deposits']:
                recent_deposits.append({
                    'id': str(deposit.id),
                    'amount': float(deposit.amount),
                    'notes': deposit.notes,
                    'deposit_date': deposit.deposit_date.isoformat()
                })
            
            return Response({
                'success': True,
                'target_saving': self.get_serializer(result['target_saving']).data,
                'recent_deposits': recent_deposits,
                'total_deposits': result['total_deposits'],
                'progress_percentage': float(result['progress_percentage']),
                'remaining_amount': float(result['remaining_amount']),
                'days_remaining': result['days_remaining']
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for a target saving"""
        target = self.get_object()
        result = TargetSavingService.get_target_analytics(request.user, target.id)
        
        if result['success']:
            return Response({
                'success': True,
                'analytics': result['analytics']
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def deposits(self, request, pk=None):
        """Get all deposits for a target saving"""
        target = self.get_object()
        deposits = target.deposits.all().order_by('-deposit_date')
        
        # Pagination
        page = self.paginate_queryset(deposits)
        if page is not None:
            deposit_data = []
            for deposit in page:
                deposit_data.append({
                    'id': str(deposit.id),
                    'amount': float(deposit.amount),
                    'notes': deposit.notes,
                    'deposit_date': deposit.deposit_date.isoformat()
                })
            
            return self.get_paginated_response({
                'success': True,
                'deposits': deposit_data
            })
        
        # No pagination
        deposit_data = []
        for deposit in deposits:
            deposit_data.append({
                'id': str(deposit.id),
                'amount': float(deposit.amount),
                'notes': deposit.notes,
                'deposit_date': deposit.deposit_date.isoformat()
            })
        
        return Response({
            'success': True,
            'deposits': deposit_data,
            'count': deposits.count()
        })
    
    @action(detail=True, methods=['get'])
    def export_deposits(self, request, pk=None):
        """Export deposits as CSV"""
        target = self.get_object()
        deposits = target.deposits.all().order_by('-deposit_date')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{target.name}_deposits.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Amount', 'Notes'])
        
        for deposit in deposits:
            writer.writerow([
                deposit.deposit_date.strftime('%Y-%m-%d %H:%M:%S'),
                float(deposit.amount),
                deposit.notes or ''
            ])
        
        return response
    
    @action(detail=False, methods=['post'])
    def send_reminder(self, request):
        """Send reminder notification for target savings"""
        target_id = request.data.get('target_id')
        reminder_type = request.data.get('reminder_type', 'weekly')
        
        if not target_id:
            return Response({
                'success': False,
                'message': 'Target ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            target = TargetSaving.objects.get(id=target_id, user=request.user)
            TargetSavingNotificationService.send_target_reminder_notification(
                request.user, target, reminder_type
            )
            
            return Response({
                'success': True,
                'message': f'{reminder_type.title()} reminder sent successfully'
            })
        except TargetSaving.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Target saving not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TargetSavingDepositViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing target saving deposits
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TargetSavingDepositSerializer
    
    def get_queryset(self):
        """Filter queryset to show only deposits for user's target savings"""
        return TargetSavingDeposit.objects.filter(
            target_saving__user=self.request.user
        )
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get deposit analytics across all targets"""
        deposits = self.get_queryset()
        
        # Date range filter
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            deposits = deposits.filter(deposit_date__date__gte=start_date)
        if end_date:
            deposits = deposits.filter(deposit_date__date__lte=end_date)
        
        # Calculate analytics
        total_deposits = deposits.count()
        total_amount = deposits.aggregate(Sum('amount'))['amount__sum'] or 0
        average_deposit = deposits.aggregate(Avg('amount'))['amount__avg'] or 0
        
        # Monthly breakdown
        monthly_breakdown = deposits.extra(
            select={'month': "EXTRACT(month FROM deposit_date)"}
        ).values('month').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('month')
        
        # Target breakdown
        target_breakdown = deposits.values(
            'target_saving__name', 'target_saving__category'
        ).annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')
        
        return Response({
            'success': True,
            'analytics': {
                'total_deposits': total_deposits,
                'total_amount': float(total_amount),
                'average_deposit': float(average_deposit),
                'monthly_breakdown': list(monthly_breakdown),
                'target_breakdown': list(target_breakdown)
            }
        })
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export all deposits as CSV"""
        deposits = self.get_queryset()
        
        # Date range filter
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            deposits = deposits.filter(deposit_date__date__gte=start_date)
        if end_date:
            deposits = deposits.filter(deposit_date__date__lte=end_date)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="target_saving_deposits.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Target Name', 'Category', 'Amount', 'Notes'])
        
        for deposit in deposits:
            writer.writerow([
                deposit.deposit_date.strftime('%Y-%m-%d %H:%M:%S'),
                deposit.target_saving.name,
                deposit.target_saving.get_category_display(),
                float(deposit.amount),
                deposit.notes or ''
            ])
        
        return response
