"""
Interest Rate Calculator API Views
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from djmoney.money import Money

from .models import Wallet
from .interest_services import (
    InterestRateCalculator, 
    InterestAccrualService, 
    InterestReportService
)

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_interest(request):
    """
    Calculate interest for a given balance amount.
    
    Expected payload:
    {
        "balance": 50000,
        "days": 30,
        "currency": "NGN"
    }
    """
    try:
        balance_amount = request.data.get('balance', 0)
        days = request.data.get('days', 365)
        currency = request.data.get('currency', 'NGN')
        
        if balance_amount <= 0:
            return Response({
                'error': 'Balance must be greater than 0'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if days <= 0:
            return Response({
                'error': 'Days must be greater than 0'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        balance = Money(balance_amount, currency)
        
        # Calculate interest with breakdown
        result = InterestRateCalculator.calculate_interest_breakdown(balance, days)
        
        return Response({
            'success': True,
            'data': {
                'balance': str(balance),
                'calculation_period_days': days,
                'total_interest': str(result['total_interest']),
                'effective_rate': float(result['effective_rate'] * 100),  # Convert to percentage
                'breakdown': result['breakdown']
            }
        })
        
    except Exception as e:
        logger.error(f"Error calculating interest: {str(e)}")
        return Response({
            'error': 'Failed to calculate interest',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_interest_rates(request):
    """
    Get current interest rate information.
    """
    try:
        rates_info = InterestReportService.get_interest_rates_info()
        
        return Response({
            'success': True,
            'data': rates_info
        })
        
    except Exception as e:
        logger.error(f"Error getting interest rates: {str(e)}")
        return Response({
            'error': 'Failed to get interest rates',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculate_wallet_interest(request):
    """
    Calculate interest for the authenticated user's wallet.
    
    Query parameters:
    - days: Number of days to calculate for (default: 30)
    - from_date: Start date (YYYY-MM-DD format)
    - to_date: End date (YYYY-MM-DD format)
    """
    try:
        user = request.user
        
        # Get user's wallet
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return Response({
                'error': 'Wallet not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Parse date parameters
        days = request.GET.get('days', 30)
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        
        if from_date_str and to_date_str:
            try:
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                to_date = datetime.strptime(to_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                days = (to_date - from_date).days
            except ValueError:
                return Response({
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            from_date = timezone.now() - timedelta(days=int(days))
            to_date = timezone.now()
        
        # Calculate interest
        result = InterestAccrualService.calculate_wallet_interest(wallet, from_date, to_date)
        
        return Response({
            'success': True,
            'data': {
                'wallet_id': str(wallet.id),
                'account_number': wallet.account_number,
                'current_balance': str(wallet.balance),
                'calculation_period': {
                    'from_date': from_date.isoformat(),
                    'to_date': to_date.isoformat(),
                    'days': days
                },
                'interest_calculation': result
            }
        })
        
    except Exception as e:
        logger.error(f"Error calculating wallet interest: {str(e)}")
        return Response({
            'error': 'Failed to calculate wallet interest',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_interest_to_wallet(request):
    """
    Apply interest to the authenticated user's wallet.
    
    Expected payload:
    {
        "amount": 1000,
        "description": "Monthly interest credit"
    }
    """
    try:
        user = request.user
        
        # Get user's wallet
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return Response({
                'error': 'Wallet not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        amount = request.data.get('amount', 0)
        description = request.data.get('description', 'Interest credit')
        
        if amount <= 0:
            return Response({
                'error': 'Interest amount must be greater than 0'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        interest_amount = Money(amount, wallet.currency)
        
        # Apply interest
        transaction = InterestAccrualService.apply_interest_to_wallet(
            wallet, interest_amount, description
        )
        
        if transaction:
            return Response({
                'success': True,
                'data': {
                    'transaction_id': str(transaction.id),
                    'amount_applied': str(interest_amount),
                    'new_balance': str(wallet.balance),
                    'description': transaction.description,
                    'timestamp': transaction.timestamp.isoformat()
                }
            })
        else:
            return Response({
                'error': 'Failed to apply interest'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error applying interest to wallet: {str(e)}")
        return Response({
            'error': 'Failed to apply interest',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_interest_report(request):
    """
    Get interest report for the authenticated user's wallet.
    
    Query parameters:
    - start_date: Start date (YYYY-MM-DD format, default: 30 days ago)
    - end_date: End date (YYYY-MM-DD format, default: today)
    """
    try:
        user = request.user
        
        # Get user's wallet
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return Response({
                'error': 'Wallet not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Parse date parameters
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                return Response({
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
        
        # Generate report
        report = InterestReportService.generate_interest_report(wallet, start_date, end_date)
        
        return Response({
            'success': True,
            'data': report
        })
        
    except Exception as e:
        logger.error(f"Error generating interest report: {str(e)}")
        return Response({
            'error': 'Failed to generate interest report',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_monthly_interest(request):
    """
    Process monthly interest for the authenticated user's wallet.
    """
    try:
        user = request.user
        
        # Get user's wallet
        try:
            wallet = Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            return Response({
                'error': 'Wallet not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Process monthly interest
        transaction = InterestAccrualService.process_monthly_interest(wallet)
        
        if transaction:
            return Response({
                'success': True,
                'data': {
                    'transaction_id': str(transaction.id),
                    'amount_applied': str(transaction.amount),
                    'new_balance': str(wallet.balance),
                    'description': transaction.description,
                    'timestamp': transaction.timestamp.isoformat()
                }
            })
        else:
            return Response({
                'message': 'No interest to apply for this period',
                'data': {
                    'current_balance': str(wallet.balance)
                }
            })
        
    except Exception as e:
        logger.error(f"Error processing monthly interest: {str(e)}")
        return Response({
            'error': 'Failed to process monthly interest',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def interest_calculator_demo(request):
    """
    Demo endpoint showing interest calculations for different balance amounts.
    """
    try:
        demo_balances = [
            Money(5000, 'NGN'),   # Tier 1 only
            Money(25000, 'NGN'),  # Tier 1 + Tier 2
            Money(150000, 'NGN'), # All three tiers
            Money(500000, 'NGN')  # All three tiers
        ]
        
        demo_results = []
        
        for balance in demo_balances:
            # Calculate annual interest
            annual_result = InterestRateCalculator.calculate_interest_breakdown(balance, 365)
            
            # Calculate monthly interest
            monthly_result = InterestRateCalculator.calculate_interest_breakdown(balance, 30)
            
            demo_results.append({
                'balance': str(balance),
                'annual_interest': str(annual_result['total_interest']),
                'monthly_interest': str(monthly_result['total_interest']),
                'effective_annual_rate': f"{float(annual_result['effective_rate'] * 100):.2f}%",
                'breakdown': annual_result['breakdown']
            })
        
        return Response({
            'success': True,
            'data': {
                'demo_calculations': demo_results,
                'rate_structure': InterestReportService.get_interest_rates_info()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in interest calculator demo: {str(e)}")
        return Response({
            'error': 'Failed to generate demo calculations',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 