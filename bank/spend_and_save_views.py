from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from djmoney.money import Money
from .models import (
    SpendAndSaveAccount, SpendAndSaveTransaction, SpendAndSaveSettings,
    Transaction, calculate_tiered_interest_rate
)
from .spend_and_save_serializers import (
    SpendAndSaveAccountSerializer, SpendAndSaveTransactionSerializer,
    SpendAndSaveSettingsSerializer, ActivateSpendAndSaveSerializer,
    DeactivateSpendAndSaveSerializer, WithdrawFromSpendAndSaveSerializer,
    UpdateSpendAndSaveSettingsSerializer, SpendAndSaveAccountSummarySerializer,
    InterestForecastSerializer, TieredInterestBreakdownSerializer,
    SpendAndSaveDashboardSerializer, ProcessSpendingTransactionSerializer,
    SpendAndSaveStatisticsSerializer, InterestCalculationSerializer
)
from .spend_and_save_services import SpendAndSaveService, SpendAndSaveInterestService
from .spend_and_save_notifications import SpendAndSaveNotificationService


class SpendAndSaveAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Spend and Save accounts
    """
    serializer_class = SpendAndSaveAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SpendAndSaveAccount.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'], serializer_class=ActivateSpendAndSaveSerializer)
    def activate(self, request):
        """Activate Spend and Save for the current user"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            account = SpendAndSaveService.activate_spend_and_save(
                user=request.user,
                savings_percentage=serializer.validated_data['savings_percentage'],
                fund_source=serializer.validated_data.get('fund_source', 'wallet'),
                initial_amount=serializer.validated_data.get('initial_amount', 0.00),
                wallet_amount=serializer.validated_data.get('wallet_amount'),
                xysave_amount=serializer.validated_data.get('xysave_amount')
            )
            
            return Response({
                'message': 'Spend and Save activated successfully',
                'account': SpendAndSaveAccountSerializer(account).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], serializer_class=DeactivateSpendAndSaveSerializer)
    def deactivate(self, request):
        """Deactivate Spend and Save for the current user"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            account = SpendAndSaveService.deactivate_spend_and_save(request.user)
            
            return Response({
                'message': 'Spend and Save deactivated successfully',
                'account': SpendAndSaveAccountSerializer(account).data
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get comprehensive account summary"""
        summary = SpendAndSaveService.get_account_summary(request.user)
        
        if summary is None:
            return Response({
                'error': 'Spend and Save account not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = SpendAndSaveAccountSummarySerializer(summary)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard data for Spend and Save"""
        try:
            # Get account summary
            summary = SpendAndSaveService.get_account_summary(request.user)
            if summary is None:
                return Response({
                    'error': 'Spend and Save account not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get interest forecast
            forecast = SpendAndSaveInterestService.get_interest_forecast(request.user)
            
            # Get tiered rates info
            tiered_rates_info = {
                'tier_1': {
                    'threshold': 10000,
                    'rate': 20,
                    'description': 'First ₦10,000 at 20% p.a'
                },
                'tier_2': {
                    'threshold': 100000,
                    'rate': 16,
                    'description': '₦10,001 - ₦100,000 at 16% p.a'
                },
                'tier_3': {
                    'rate': 8,
                    'description': 'Above ₦100,000 at 8% p.a'
                }
            }
            
            # Get recent activity
            account = SpendAndSaveAccount.objects.get(user=request.user)
            recent_activity = account.transactions.all()[:5]
            
            # Calculate savings progress
            total_saved = account.total_saved_from_spending.amount
            total_interest = account.total_interest_earned.amount
            total_balance = account.balance.amount
            
            savings_progress = {
                'total_saved_from_spending': str(account.total_saved_from_spending),
                'total_interest_earned': str(account.total_interest_earned),
                'current_balance': str(account.balance),
                'savings_percentage': float(account.savings_percentage),
                'total_transactions_processed': account.total_transactions_processed
            }
            
            dashboard_data = {
                'account_summary': summary,
                'interest_forecast': forecast,
                'tiered_rates_info': tiered_rates_info,
                'recent_activity': SpendAndSaveTransactionSerializer(recent_activity, many=True).data,
                'savings_progress': savings_progress
            }
            
            serializer = SpendAndSaveDashboardSerializer(dashboard_data)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], serializer_class=WithdrawFromSpendAndSaveSerializer)
    def withdraw(self, request):
        """Withdraw from Spend and Save account"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            amount = Money(serializer.validated_data['amount'], 'NGN')
            destination = serializer.validated_data['destination']
            
            withdrawal_tx = SpendAndSaveService.withdraw_from_spend_and_save(
                user=request.user,
                amount=amount,
                destination=destination
            )
            
            return Response({
                'message': f'Successfully withdrew {amount} to {destination}',
                'transaction': SpendAndSaveTransactionSerializer(withdrawal_tx).data
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def interest_forecast(self, request):
        """Get interest forecast for the account"""
        forecast = SpendAndSaveInterestService.get_interest_forecast(request.user)
        
        if forecast is None:
            return Response({
                'error': 'Spend and Save account not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = InterestForecastSerializer(forecast)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def interest_breakdown(self, request):
        """Get detailed interest breakdown by tier"""
        try:
            account = SpendAndSaveAccount.objects.get(user=request.user)
            breakdown = account.get_interest_breakdown()
            
            serializer = TieredInterestBreakdownSerializer(breakdown)
            return Response(serializer.data)
            
        except SpendAndSaveAccount.DoesNotExist:
            return Response({
                'error': 'Spend and Save account not found'
            }, status=status.HTTP_404_NOT_FOUND)


class SpendAndSaveTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Spend and Save transactions
    """
    serializer_class = SpendAndSaveTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SpendAndSaveTransaction.objects.filter(
            spend_and_save_account__user=self.request.user
        )
    
    @action(detail=False, methods=['post'], serializer_class=ProcessSpendingTransactionSerializer)
    def process_spending(self, request):
        """Process a spending transaction for auto-save"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            transaction_id = serializer.validated_data['transaction_id']
            transaction = Transaction.objects.get(id=transaction_id)
            
            auto_save_tx = SpendAndSaveService.process_spending_transaction(transaction)
            
            if auto_save_tx is None:
                return Response({
                    'message': 'No auto-save processed (account inactive or amount below threshold)'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'message': 'Auto-save processed successfully',
                'transaction': SpendAndSaveTransactionSerializer(auto_save_tx).data
            }, status=status.HTTP_200_OK)
            
        except Transaction.DoesNotExist:
            return Response({
                'error': 'Transaction not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SpendAndSaveSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Spend and Save settings
    """
    serializer_class = SpendAndSaveSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SpendAndSaveSettings.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['patch'], serializer_class=UpdateSpendAndSaveSettingsSerializer)
    def update_settings(self, request):
        """Update Spend and Save settings"""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        try:
            settings = SpendAndSaveService.update_settings(
                user=request.user,
                **serializer.validated_data
            )
            
            return Response({
                'message': 'Settings updated successfully',
                'settings': SpendAndSaveSettingsSerializer(settings).data
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SpendAndSaveInterestViewSet(viewsets.ViewSet):
    """
    ViewSet for interest-related operations
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def calculate_interest(self, request):
        """Calculate interest for a given balance amount"""
        serializer = InterestCalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            balance_amount = serializer.validated_data['balance_amount']
            breakdown = calculate_tiered_interest_rate(balance_amount)
            
            return Response({
                'balance_amount': str(Money(balance_amount, 'NGN')),
                'daily_interest': breakdown['total_interest'],
                'monthly_interest': breakdown['total_interest'] * 30,
                'annual_interest': breakdown['total_interest'] * 365,
                'tier_breakdown': breakdown
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def credit_interest(self, request):
        """Credit daily interest to user's account"""
        try:
            interest_tx = SpendAndSaveService.calculate_and_credit_interest(request.user)
            
            if interest_tx is None:
                return Response({
                    'message': 'No interest to credit (zero balance)'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'message': 'Interest credited successfully',
                'transaction': SpendAndSaveTransactionSerializer(interest_tx).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def tiered_rates_info(self, request):
        """Get information about tiered interest rates"""
        tiered_rates_info = {
            'tier_1': {
                'threshold': 10000,
                'rate': 20,
                'daily_rate': 0.000548,
                'description': 'First ₦10,000 at 20% p.a',
                'example': '₦10,000 earns ₦5.48 daily interest'
            },
            'tier_2': {
                'threshold': 100000,
                'rate': 16,
                'daily_rate': 0.000438,
                'description': '₦10,001 - ₦100,000 at 16% p.a',
                'example': '₦90,000 earns ₦39.42 daily interest'
            },
            'tier_3': {
                'rate': 8,
                'daily_rate': 0.000219,
                'description': 'Above ₦100,000 at 8% p.a',
                'example': '₦50,000 earns ₦10.95 daily interest'
            },
            'calculation_method': 'Daily interest is calculated and credited automatically',
            'payout_frequency': 'Daily at 11:00 AM',
            'minimum_balance': 'No minimum balance required'
        }
        
        return Response(tiered_rates_info)


class SpendAndSaveStatisticsViewSet(viewsets.ViewSet):
    """
    ViewSet for Spend and Save statistics (admin/staff only)
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get overview statistics for Spend and Save"""
        try:
            # Check if user is staff
            if not request.user.is_staff:
                return Response({
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            total_users = SpendAndSaveAccount.objects.count()
            active_accounts = SpendAndSaveAccount.objects.filter(is_active=True).count()
            
            # Calculate totals
            total_saved_amount = sum(
                account.total_saved_from_spending.amount 
                for account in SpendAndSaveAccount.objects.all()
            )
            total_interest_paid = sum(
                account.total_interest_earned.amount 
                for account in SpendAndSaveAccount.objects.all()
            )
            total_transactions_processed = sum(
                account.total_transactions_processed 
                for account in SpendAndSaveAccount.objects.all()
            )
            
            # Calculate average savings percentage
            active_accounts_with_percentage = SpendAndSaveAccount.objects.filter(
                is_active=True, savings_percentage__isnull=False
            )
            if active_accounts_with_percentage.exists():
                average_savings_percentage = sum(
                    account.savings_percentage 
                    for account in active_accounts_with_percentage
                ) / active_accounts_with_percentage.count()
            else:
                average_savings_percentage = 0
            
            statistics = {
                'total_users': total_users,
                'active_accounts': active_accounts,
                'total_saved_amount': str(Money(total_saved_amount, 'NGN')),
                'total_interest_paid': str(Money(total_interest_paid, 'NGN')),
                'average_savings_percentage': round(average_savings_percentage, 2),
                'total_transactions_processed': total_transactions_processed,
                'daily_interest_payouts': active_accounts,  # Each active account gets daily interest
                'monthly_growth_rate': 0  # Would need historical data to calculate
            }
            
            serializer = SpendAndSaveStatisticsSerializer(statistics)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get transaction analytics for Spend and Save"""
        try:
            account = SpendAndSaveAccount.objects.get(user=request.user)
            
            # Get date range from query params
            days = int(request.query_params.get('days', 30))
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Get transactions in date range
            transactions = SpendAndSaveTransaction.objects.filter(
                spend_and_save_account=account,
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            # Calculate analytics
            total_saved = sum(tx.amount.amount for tx in transactions.filter(transaction_type='auto_save'))
            total_withdrawn = sum(tx.amount.amount for tx in transactions.filter(transaction_type='withdrawal'))
            total_interest = sum(tx.amount.amount for tx in transactions.filter(transaction_type='interest_credit'))
            
            # Daily breakdown
            daily_data = {}
            for tx in transactions:
                date = tx.created_at.date()
                if date not in daily_data:
                    daily_data[date] = {
                        'saved': 0,
                        'withdrawn': 0,
                        'interest': 0,
                        'transactions': 0
                    }
                
                if tx.transaction_type == 'auto_save':
                    daily_data[date]['saved'] += tx.amount.amount
                elif tx.transaction_type == 'withdrawal':
                    daily_data[date]['withdrawn'] += tx.amount.amount
                elif tx.transaction_type == 'interest_credit':
                    daily_data[date]['interest'] += tx.amount.amount
                
                daily_data[date]['transactions'] += 1
            
            analytics = {
                'period': {
                    'start_date': start_date.date(),
                    'end_date': end_date.date(),
                    'days': days
                },
                'summary': {
                    'total_saved': total_saved,
                    'total_withdrawn': total_withdrawn,
                    'total_interest': total_interest,
                    'net_savings': total_saved + total_interest - total_withdrawn,
                    'total_transactions': transactions.count()
                },
                'daily_breakdown': [
                    {
                        'date': str(date),
                        'saved': data['saved'],
                        'withdrawn': data['withdrawn'],
                        'interest': data['interest'],
                        'transactions': data['transactions']
                    }
                    for date, data in sorted(daily_data.items())
                ]
            }
            
            return Response(analytics)
            
        except SpendAndSaveAccount.DoesNotExist:
            return Response({
                'error': 'Spend and Save account not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export transaction history as CSV"""
        try:
            account = SpendAndSaveAccount.objects.get(user=request.user)
            
            # Get date range from query params
            days = int(request.query_params.get('days', 90))
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            transactions = SpendAndSaveTransaction.objects.filter(
                spend_and_save_account=account,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).order_by('-created_at')
            
            # Prepare CSV data
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Date', 'Type', 'Amount', 'Balance Before', 'Balance After',
                'Reference', 'Description'
            ])
            
            # Write data
            for tx in transactions:
                writer.writerow([
                    tx.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    tx.transaction_type,
                    tx.amount.amount,
                    tx.balance_before.amount,
                    tx.balance_after.amount,
                    tx.reference,
                    tx.description
                ])
            
            from django.http import HttpResponse
            response = HttpResponse(
                output.getvalue(),
                content_type='text/csv'
            )
            response['Content-Disposition'] = f'attachment; filename="spend_and_save_transactions_{start_date.date()}_to_{end_date.date()}.csv"'
            
            return response
            
        except SpendAndSaveAccount.DoesNotExist:
            return Response({
                'error': 'Spend and Save account not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def notifications(self, request):
        """Get user's Spend and Save related notifications"""
        try:
            from notification.models import Notification
            
            # Get notifications related to spend and save
            notifications = Notification.objects.filter(
                recipient=request.user,
                source='spend_and_save'
            ).order_by('-created_at')[:20]
            
            from notification.serializers import NotificationSerializer
            serializer = NotificationSerializer(notifications, many=True)
            
            return Response({
                'notifications': serializer.data,
                'unread_count': notifications.filter(isRead=False).count()
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def weekly_summary(self, request):
        """Get weekly savings summary"""
        try:
            account = SpendAndSaveAccount.objects.get(user=request.user)
            
            # Calculate weekly stats
            week_ago = timezone.now() - timedelta(days=7)
            weekly_transactions = SpendAndSaveTransaction.objects.filter(
                spend_and_save_account=account,
                created_at__gte=week_ago,
                transaction_type='auto_save'
            )
            
            total_saved = sum(tx.amount.amount for tx in weekly_transactions)
            transactions_count = weekly_transactions.count()
            
            # Get spending transactions that triggered saves
            original_transactions = Transaction.objects.filter(
                wallet__user=request.user,
                type='debit',
                created_at__gte=week_ago
            )
            total_spent = sum(tx.amount.amount for tx in original_transactions)
            
            weekly_stats = {
                'total_spent': total_spent,
                'total_saved': total_saved,
                'transactions_count': transactions_count,
                'savings_rate': (total_saved / total_spent * 100) if total_spent > 0 else 0,
                'week_start': week_ago.date(),
                'week_end': timezone.now().date()
            }
            
            return Response(weekly_stats)
            
        except SpendAndSaveAccount.DoesNotExist:
            return Response({
                'error': 'Spend and Save account not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def savings_goals(self, request):
        """Get user's savings goals and progress"""
        try:
            account = SpendAndSaveAccount.objects.get(user=request.user)
            
            # Define milestone goals
            milestones = [
                {'amount': 100, 'name': 'First ₦100', 'icon': '💰'},
                {'amount': 500, 'name': '₦500 Milestone', 'icon': '🎯'},
                {'amount': 1000, 'name': '₦1,000 Goal', 'icon': '🏆'},
                {'amount': 5000, 'name': '₦5,000 Target', 'icon': '💎'},
                {'amount': 10000, 'name': '₦10,000 Achievement', 'icon': '👑'},
                {'amount': 50000, 'name': '₦50,000 Dream', 'icon': '🚀'},
                {'amount': 100000, 'name': '₦100,000 Master', 'icon': '💫'}
            ]
            
            current_saved = account.total_saved_from_spending.amount
            goals = []
            
            for milestone in milestones:
                progress = min(100, (current_saved / milestone['amount']) * 100)
                achieved = current_saved >= milestone['amount']
                
                goals.append({
                    'name': milestone['name'],
                    'icon': milestone['icon'],
                    'target_amount': milestone['amount'],
                    'current_amount': current_saved,
                    'progress': round(progress, 1),
                    'achieved': achieved,
                    'remaining': max(0, milestone['amount'] - current_saved)
                })
            
            return Response({
                'goals': goals,
                'total_saved': current_saved,
                'next_goal': next((g for g in goals if not g['achieved']), None)
            })
            
        except SpendAndSaveAccount.DoesNotExist:
            return Response({
                'error': 'Spend and Save account not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def send_weekly_summary(self, request):
        """Send weekly savings summary notification"""
        try:
            account = SpendAndSaveAccount.objects.get(user=request.user)
            
            # Calculate weekly stats
            week_ago = timezone.now() - timedelta(days=7)
            weekly_transactions = SpendAndSaveTransaction.objects.filter(
                spend_and_save_account=account,
                created_at__gte=week_ago,
                transaction_type='auto_save'
            )
            
            total_saved = sum(tx.amount.amount for tx in weekly_transactions)
            transactions_count = weekly_transactions.count()
            
            # Get spending transactions
            original_transactions = Transaction.objects.filter(
                wallet__user=request.user,
                type='debit',
                created_at__gte=week_ago
            )
            total_spent = sum(tx.amount.amount for tx in original_transactions)
            
            weekly_stats = {
                'total_spent': total_spent,
                'total_saved': total_saved,
                'transactions_count': transactions_count
            }
            
            # Send weekly summary notification
            SpendAndSaveNotificationService.send_weekly_savings_summary(
                request.user, account, weekly_stats
            )
            
            return Response({
                'message': 'Weekly summary notification sent successfully',
                'weekly_stats': weekly_stats
            })
            
        except SpendAndSaveAccount.DoesNotExist:
            return Response({
                'error': 'Spend and Save account not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def process_daily_interest(self, request):
        """Process daily interest payout for all active accounts (admin only)"""
        try:
            # Check if user is staff
            if not request.user.is_staff:
                return Response({
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            processed_count = SpendAndSaveInterestService.process_daily_interest_payout()
            
            return Response({
                'message': f'Processed daily interest for {processed_count} accounts',
                'processed_count': processed_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 