import logging
from rest_framework import status, viewsets, mixins, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from djmoney.money import Money

from .models import (
    XySaveAccount, XySaveTransaction, XySaveGoal, 
    XySaveInvestment, XySaveSettings
)
from .xysave_serializers import (
    XySaveAccountSerializer, XySaveTransactionSerializer, XySaveGoalSerializer,
    XySaveInvestmentSerializer, XySaveSettingsSerializer, XySaveAccountSummarySerializer,
    XySaveDepositSerializer, XySaveWithdrawalSerializer, XySaveAutoSaveSerializer,
    XySaveGoalCreateSerializer, XySaveInvestmentCreateSerializer,
    XySaveInterestForecastSerializer, XySaveDashboardSerializer
)
from .xysave_services import (
    XySaveAccountService, XySaveTransactionService, XySaveAutoSaveService,
    XySaveGoalService, XySaveInvestmentService, XySaveInterestService
)
from .transaction_security import TransactionSecurityService

logger = logging.getLogger(__name__)


class XySaveAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for XySave Account operations"""
    permission_classes = [IsAuthenticated]
    serializer_class = XySaveAccountSerializer
    
    def get_queryset(self):
        """Get XySave account for current user"""
        return XySaveAccount.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create XySave account for current user"""
        try:
            return XySaveAccountService.get_xysave_account(self.request.user)
        except Exception as e:
            logger.error(f"Error getting XySave account: {str(e)}")
            return Response(
                {"error": "Failed to get XySave account"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get comprehensive XySave account summary"""
        try:
            summary_data = XySaveAccountService.get_account_summary(request.user)
            serializer = XySaveAccountSummarySerializer(summary_data)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error getting XySave summary: {str(e)}")
            return Response(
                {"error": "Failed to get account summary"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get XySave dashboard data"""
        try:
            # Get account summary
            summary_data = XySaveAccountService.get_account_summary(request.user)
            
            # Get interest forecast
            interest_forecast = XySaveInterestService.get_interest_forecast(request.user)
            
            # Get recent transactions
            account = summary_data['account']
            recent_transactions = account.transactions.all()[:10]
            
            # Get active goals
            active_goals = request.user.xysave_goals.filter(is_active=True)
            
            # Get investments
            investments = account.investments.filter(is_active=True)
            
            dashboard_data = {
                'account_summary': summary_data,
                'interest_forecast': interest_forecast,
                'recent_activity': recent_transactions,
                'goals_progress': active_goals,
                'investment_portfolio': investments,
            }
            
            serializer = XySaveDashboardSerializer(dashboard_data)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error getting XySave dashboard: {str(e)}")
            return Response(
                {"error": "Failed to get dashboard data"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def deposit(self, request):
        """Deposit money to XySave account"""
        try:
            serializer = XySaveDepositSerializer(data=request.data)
            if serializer.is_valid():
                amount = serializer.validated_data['amount']
                description = serializer.validated_data.get('description', 'Deposit to XySave')
                
                transaction = XySaveTransactionService.deposit_to_xysave(
                    request.user, amount, description
                )
                
                return Response({
                    "message": f"Successfully deposited {amount} to XySave",
                    "transaction": XySaveTransactionSerializer(transaction).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error depositing to XySave: {str(e)}")
            return Response(
                {"error": "Failed to process deposit"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        """Withdraw money from XySave account"""
        try:
            serializer = XySaveWithdrawalSerializer(data=request.data)
            if serializer.is_valid():
                amount = serializer.validated_data['amount']
                description = serializer.validated_data.get('description', 'Withdrawal from XySave')
                
                transaction = XySaveTransactionService.withdraw_from_xysave(
                    request.user, amount, description
                )
                
                return Response({
                    "message": f"Successfully withdrew {amount} from XySave",
                    "transaction": XySaveTransactionSerializer(transaction).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error withdrawing from XySave: {str(e)}")
            return Response(
                {"error": "Failed to process withdrawal"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def interest_forecast(self, request):
        """Get interest forecast for XySave account"""
        try:
            days = int(request.query_params.get('days', 30))
            forecast = XySaveInterestService.get_interest_forecast(request.user, days)
            serializer = XySaveInterestForecastSerializer(forecast)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error getting interest forecast: {str(e)}")
            return Response(
                {"error": "Failed to get interest forecast"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def transaction_security(self, request):
        """Get basic security analysis for recent transactions"""
        try:
            account = XySaveAccountService.get_xysave_account(request.user)
            security_service = TransactionSecurityService()
            
            # Get recent transactions
            recent_transactions = account.transactions.all().order_by('-created_at')[:10]
            
            security_analysis = []
            for transaction in recent_transactions:
                security_result = security_service.check_transaction_risk(transaction, request.user)
                security_analysis.append({
                    'transaction_id': transaction.id,
                    'reference': transaction.reference,
                    'amount': str(transaction.amount),
                    'risk_level': security_result['risk_level'],
                    'risk_factors': security_result['risk_factors'],
                    'created_at': transaction.created_at
                })
            
            return Response({
                "security_analysis": security_analysis,
                "total_transactions_analyzed": len(security_analysis),
                "analysis_timestamp": timezone.now()
            })
        except Exception as e:
            logger.error(f"Error getting security analysis: {str(e)}")
            return Response(
                {"error": "Failed to get security analysis"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class XySaveTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for XySave Transaction operations"""
    permission_classes = [IsAuthenticated]
    serializer_class = XySaveTransactionSerializer
    
    def get_queryset(self):
        """Get XySave transactions for current user"""
        return XySaveTransaction.objects.filter(xysave_account__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get transactions filtered by type"""
        try:
            transaction_type = request.query_params.get('type')
            queryset = self.get_queryset()
            
            if transaction_type:
                queryset = queryset.filter(transaction_type=transaction_type)
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error getting transactions by type: {str(e)}")
            return Response(
                {"error": "Failed to get transactions"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class XySaveGoalViewSet(viewsets.ModelViewSet):
    """ViewSet for XySave Goal operations"""
    permission_classes = [IsAuthenticated]
    serializer_class = XySaveGoalSerializer
    
    def get_queryset(self):
        """Get XySave goals for current user"""
        return XySaveGoal.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create a new goal"""
        try:
            goal = XySaveGoalService.create_goal(
                user=self.request.user,
                name=serializer.validated_data['name'],
                target_amount=serializer.validated_data['target_amount'],
                target_date=serializer.validated_data.get('target_date')
            )
            return goal
        except Exception as e:
            logger.error(f"Error creating goal: {str(e)}")
            raise
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update goal progress"""
        try:
            goal = self.get_object()
            amount = Money(request.data.get('amount', 0), 'NGN')
            
            updated_goal = XySaveGoalService.update_goal_progress(
                request.user, goal.id, amount
            )
            
            return Response({
                "message": f"Updated progress for goal '{updated_goal.name}'",
                "goal": XySaveGoalSerializer(updated_goal).data
            })
            
        except Exception as e:
            logger.error(f"Error updating goal progress: {str(e)}")
            return Response(
                {"error": "Failed to update goal progress"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active goals only"""
        try:
            active_goals = self.get_queryset().filter(is_active=True)
            serializer = self.get_serializer(active_goals, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error getting active goals: {str(e)}")
            return Response(
                {"error": "Failed to get active goals"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class XySaveInvestmentViewSet(viewsets.ModelViewSet):
    """ViewSet for XySave Investment operations"""
    permission_classes = [IsAuthenticated]
    serializer_class = XySaveInvestmentSerializer
    
    def get_queryset(self):
        """Get XySave investments for current user"""
        return XySaveInvestment.objects.filter(xysave_account__user=self.request.user)
    
    def perform_create(self, serializer):
        """Create a new investment"""
        try:
            investment = XySaveInvestmentService.create_investment(
                user=self.request.user,
                investment_type=serializer.validated_data['investment_type'],
                amount_invested=serializer.validated_data['amount_invested'],
                expected_return_rate=serializer.validated_data['expected_return_rate'],
                maturity_date=serializer.validated_data.get('maturity_date')
            )
            return investment
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            logger.error(f"Error creating investment: {str(e)}")
            raise
    
    @action(detail=True, methods=['post'])
    def liquidate(self, request, pk=None):
        """Liquidate an investment"""
        try:
            investment = self.get_object()
            
            liquidated_investment = XySaveInvestmentService.liquidate_investment(
                request.user, investment.id
            )
            
            return Response({
                "message": f"Successfully liquidated {liquidated_investment.investment_type} investment",
                "investment": XySaveInvestmentSerializer(liquidated_investment).data
            })
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error liquidating investment: {str(e)}")
            return Response(
                {"error": "Failed to liquidate investment"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active investments only"""
        try:
            active_investments = self.get_queryset().filter(is_active=True)
            serializer = self.get_serializer(active_investments, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error getting active investments: {str(e)}")
            return Response(
                {"error": "Failed to get active investments"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class XySaveSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for XySave Settings operations"""
    permission_classes = [IsAuthenticated]
    serializer_class = XySaveSettingsSerializer
    
    def get_queryset(self):
        """Get XySave settings for current user"""
        return XySaveSettings.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create settings for current user"""
        try:
            return XySaveSettings.objects.get(user=self.request.user)
        except XySaveSettings.DoesNotExist:
            return XySaveSettings.objects.create(user=self.request.user)


class XySaveAutoSaveViewSet(viewsets.ViewSet):
    """ViewSet for XySave Auto-Save operations"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def enable(self, request):
        """Enable auto-save"""
        try:
            serializer = XySaveAutoSaveSerializer(data=request.data)
            if serializer.is_valid():
                enabled = serializer.validated_data['enabled']
                
                if enabled:
                    percentage = serializer.validated_data['percentage']
                    min_amount = serializer.validated_data['min_amount']
                    
                    account = XySaveAutoSaveService.enable_auto_save(
                        request.user, percentage, min_amount
                    )
                    
                    return Response({
                        "message": f"Auto-save enabled at {percentage}% with minimum amount {min_amount}",
                        "account": XySaveAccountSerializer(account).data
                    })
                else:
                    account = XySaveAutoSaveService.disable_auto_save(request.user)
                    return Response({
                        "message": "Auto-save disabled",
                        "account": XySaveAccountSerializer(account).data
                    })
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error configuring auto-save: {str(e)}")
            return Response(
                {"error": "Failed to configure auto-save"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get auto-save status"""
        try:
            account = XySaveAccountService.get_xysave_account(request.user)
            return Response({
                "enabled": account.auto_save_enabled,
                "percentage": account.auto_save_percentage,
                "min_amount": str(account.auto_save_min_amount)
            })
        except Exception as e:
            logger.error(f"Error getting auto-save status: {str(e)}")
            return Response(
                {"error": "Failed to get auto-save status"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 