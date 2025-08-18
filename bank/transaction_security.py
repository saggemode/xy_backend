"""
Simple security checks for XySave transactions
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg

logger = logging.getLogger(__name__)

class TransactionSecurityService:
    """Simple rule-based security checks"""
    
    def check_transaction_risk(self, transaction, user):
        """Check transaction risk using basic rules"""
        try:
            # Get user's transaction history
            recent_transactions = user.xysave_account.transactions.all().order_by('-created_at')[:10]
            
            # Calculate transaction patterns
            avg_amount = recent_transactions.aggregate(avg=Avg('amount'))['avg'] or 0
            transaction_count_24h = recent_transactions.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            # Time-based checks
            hour = transaction.created_at.hour
            is_odd_hour = hour < 6 or hour > 22
            is_weekend = transaction.created_at.weekday() >= 5
            
            # Amount-based checks
            amount = transaction.amount.amount
            balance = transaction.xysave_account.balance.amount
            is_large_amount = amount > 100000  # > ₦100k
            amount_ratio = amount / max(balance, 1)
            
            # Risk assessment
            risk_factors = []
            
            if is_large_amount:
                risk_factors.append("Large transaction amount")
            
            if is_odd_hour and is_weekend:
                risk_factors.append("Unusual transaction time")
                
            if amount > (avg_amount * 3) and amount > 50000:
                risk_factors.append("Amount significantly above average")
                
            if transaction_count_24h > 10:
                risk_factors.append("High transaction frequency")
                
            if amount_ratio > 0.8:
                risk_factors.append("Large portion of balance")
            
            # Determine risk level
            risk_level = 'low'
            if len(risk_factors) >= 3:
                risk_level = 'high'
            elif len(risk_factors) >= 1:
                risk_level = 'medium'
            
            return {
                'is_suspicious': risk_level == 'high',
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'requires_review': risk_level == 'high'
            }
            
        except Exception as e:
            logger.error(f"Error checking transaction risk: {str(e)}")
            return {
                'is_suspicious': False,
                'risk_level': 'medium',
                'risk_factors': ['Error in risk assessment'],
                'requires_review': False
            }
