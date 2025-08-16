"""
Interest Rate Calculation Services
"""
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from djmoney.money import Money
from .models import Wallet, Transaction

logger = logging.getLogger(__name__)

class InterestRateCalculator:
    """
    Interest Rate Calculator with tiered structure:
    - 20% p.a. for balance up to 10,000 NGN
    - 16% p.a. for balance above 10,000 but within 100,000 NGN (first 10,000 at 20%, remaining at 16%)
    - 8% p.a. for balance above 100,000 NGN (first 10,000 at 20%, 10,000-100,000 at 16%, remaining at 8%)
    """
    
    # Tier thresholds in NGN
    TIER_1_THRESHOLD = Money(10000, 'NGN')  # 10,000 NGN
    TIER_2_THRESHOLD = Money(100000, 'NGN')  # 100,000 NGN
    
    # Interest rates per annum (as decimals)
    TIER_1_RATE = Decimal('0.20')  # 20% p.a.
    TIER_2_RATE = Decimal('0.16')  # 16% p.a.
    TIER_3_RATE = Decimal('0.08')  # 8% p.a.
    
    @classmethod
    def calculate_interest_for_balance(cls, balance: Money, days: int = 365) -> Money:
        """
        Calculate interest for a given balance over specified days.
        
        Args:
            balance: The balance amount in Money object
            days: Number of days to calculate interest for (default: 365 for annual)
            
        Returns:
            Money: Interest amount calculated
        """
        if not isinstance(balance, Money) or balance.amount <= 0:
            return Money(0, 'NGN')
        
        # Convert to Decimal for precise calculations
        balance_amount = Decimal(str(balance.amount))
        days_decimal = Decimal(str(days))
        
        # Calculate daily rate (annual rate / 365)
        daily_tier_1_rate = cls.TIER_1_RATE / Decimal('365')
        daily_tier_2_rate = cls.TIER_2_RATE / Decimal('365')
        daily_tier_3_rate = cls.TIER_3_RATE / Decimal('365')
        
        # Calculate interest for each tier
        interest = Decimal('0')
        
        if balance_amount <= cls.TIER_1_THRESHOLD.amount:
            # All balance in Tier 1 (20% p.a.)
            interest = balance_amount * daily_tier_1_rate * days_decimal
        elif balance_amount <= cls.TIER_2_THRESHOLD.amount:
            # First 10,000 at 20%, remaining at 16%
            tier_1_interest = cls.TIER_1_THRESHOLD.amount * daily_tier_1_rate * days_decimal
            tier_2_balance = balance_amount - cls.TIER_1_THRESHOLD.amount
            tier_2_interest = tier_2_balance * daily_tier_2_rate * days_decimal
            interest = tier_1_interest + tier_2_interest
        else:
            # First 10,000 at 20%, 10,000-100,000 at 16%, remaining at 6%
            tier_1_interest = cls.TIER_1_THRESHOLD.amount * daily_tier_1_rate * days_decimal
            tier_2_balance = cls.TIER_2_THRESHOLD.amount - cls.TIER_1_THRESHOLD.amount
            tier_2_interest = tier_2_balance * daily_tier_2_rate * days_decimal
            tier_3_balance = balance_amount - cls.TIER_2_THRESHOLD.amount
            tier_3_interest = tier_3_balance * daily_tier_3_rate * days_decimal
            interest = tier_1_interest + tier_2_interest + tier_3_interest
        
        return Money(interest, 'NGN')
    
    @classmethod
    def calculate_interest_breakdown(cls, balance: Money, days: int = 365) -> dict:
        """
        Calculate interest with detailed breakdown by tier.
        
        Args:
            balance: The balance amount in Money object
            days: Number of days to calculate interest for
            
        Returns:
            dict: Detailed breakdown of interest calculation
        """
        if not isinstance(balance, Money) or balance.amount <= 0:
            return {
                'total_interest': Money(0, 'NGN'),
                'breakdown': [],
                'effective_rate': Decimal('0')
            }
        
        balance_amount = Decimal(str(balance.amount))
        days_decimal = Decimal(str(days))
        
        # Calculate daily rates
        daily_tier_1_rate = cls.TIER_1_RATE / Decimal('365')
        daily_tier_2_rate = cls.TIER_2_RATE / Decimal('365')
        daily_tier_3_rate = cls.TIER_3_RATE / Decimal('365')
        
        breakdown = []
        total_interest = Decimal('0')
        
        if balance_amount <= cls.TIER_1_THRESHOLD.amount:
            # All in Tier 1
            tier_1_interest = balance_amount * daily_tier_1_rate * days_decimal
            breakdown.append({
                'tier': 1,
                'rate': cls.TIER_1_RATE,
                'balance_in_tier': Money(balance_amount, 'NGN'),
                'interest': Money(tier_1_interest, 'NGN'),
                'description': f'Balance up to {cls.TIER_1_THRESHOLD} at {cls.TIER_1_RATE*100}% p.a.'
            })
            total_interest = tier_1_interest
            
        elif balance_amount <= cls.TIER_2_THRESHOLD.amount:
            # Tier 1 + Tier 2
            tier_1_interest = cls.TIER_1_THRESHOLD.amount * daily_tier_1_rate * days_decimal
            tier_2_balance = balance_amount - cls.TIER_1_THRESHOLD.amount
            tier_2_interest = tier_2_balance * daily_tier_2_rate * days_decimal
            
            breakdown.append({
                'tier': 1,
                'rate': cls.TIER_1_RATE,
                'balance_in_tier': cls.TIER_1_THRESHOLD,
                'interest': Money(tier_1_interest, 'NGN'),
                'description': f'First {cls.TIER_1_THRESHOLD} at {cls.TIER_1_RATE*100}% p.a.'
            })
            breakdown.append({
                'tier': 2,
                'rate': cls.TIER_2_RATE,
                'balance_in_tier': Money(tier_2_balance, 'NGN'),
                'interest': Money(tier_2_interest, 'NGN'),
                'description': f'Balance {cls.TIER_1_THRESHOLD} - {cls.TIER_2_THRESHOLD} at {cls.TIER_2_RATE*100}% p.a.'
            })
            total_interest = tier_1_interest + tier_2_interest
            
        else:
            # All three tiers
            tier_1_interest = cls.TIER_1_THRESHOLD.amount * daily_tier_1_rate * days_decimal
            tier_2_balance = cls.TIER_2_THRESHOLD.amount - cls.TIER_1_THRESHOLD.amount
            tier_2_interest = tier_2_balance * daily_tier_2_rate * days_decimal
            tier_3_balance = balance_amount - cls.TIER_2_THRESHOLD.amount
            tier_3_interest = tier_3_balance * daily_tier_3_rate * days_decimal
            
            breakdown.append({
                'tier': 1,
                'rate': cls.TIER_1_RATE,
                'balance_in_tier': cls.TIER_1_THRESHOLD,
                'interest': Money(tier_1_interest, 'NGN'),
                'description': f'First {cls.TIER_1_THRESHOLD} at {cls.TIER_1_RATE*100}% p.a.'
            })
            breakdown.append({
                'tier': 2,
                'rate': cls.TIER_2_RATE,
                'balance_in_tier': Money(tier_2_balance, 'NGN'),
                'interest': Money(tier_2_interest, 'NGN'),
                'description': f'Balance {cls.TIER_1_THRESHOLD} - {cls.TIER_2_THRESHOLD} at {cls.TIER_2_RATE*100}% p.a.'
            })
            breakdown.append({
                'tier': 3,
                'rate': cls.TIER_3_RATE,
                'balance_in_tier': Money(tier_3_balance, 'NGN'),
                'interest': Money(tier_3_interest, 'NGN'),
                'description': f'Balance above {cls.TIER_2_THRESHOLD} at {cls.TIER_3_RATE*100}% p.a.'
            })
            total_interest = tier_1_interest + tier_2_interest + tier_3_interest
        
        # Calculate effective annual rate
        effective_rate = (total_interest / balance_amount) * (Decimal('365') / days_decimal) if balance_amount > 0 else Decimal('0')
        
        return {
            'total_interest': Money(total_interest, 'NGN'),
            'breakdown': breakdown,
            'effective_rate': effective_rate,
            'calculation_period_days': days
        }
    
    @classmethod
    def calculate_monthly_interest(cls, balance: Money, month: int = None, year: int = None) -> Money:
        """
        Calculate interest for a specific month.
        
        Args:
            balance: The balance amount
            month: Month number (1-12), if None uses current month
            year: Year, if None uses current year
            
        Returns:
            Money: Monthly interest amount
        """
        if month is None:
            month = timezone.now().month
        if year is None:
            year = timezone.now().year
        
        # Get number of days in the month
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        current_month = datetime(year, month, 1)
        days_in_month = (next_month - current_month).days
        
        return cls.calculate_interest_for_balance(balance, days_in_month)
    
    @classmethod
    def calculate_annual_interest(cls, balance: Money) -> Money:
        """
        Calculate annual interest for a balance.
        
        Args:
            balance: The balance amount
            
        Returns:
            Money: Annual interest amount
        """
        return cls.calculate_interest_for_balance(balance, 365)


class InterestAccrualService:
    """
    Service for managing interest accrual and application to wallets.
    """
    
    @classmethod
    def calculate_wallet_interest(cls, wallet: Wallet, from_date: datetime = None, to_date: datetime = None) -> dict:
        """
        Calculate interest for a wallet over a specific period.
        
        Args:
            wallet: The wallet to calculate interest for
            from_date: Start date for calculation (default: 30 days ago)
            to_date: End date for calculation (default: now)
            
        Returns:
            dict: Interest calculation results
        """
        if from_date is None:
            from_date = timezone.now() - timedelta(days=30)
        if to_date is None:
            to_date = timezone.now()
        
        # Get average balance for the period
        transactions = Transaction.objects.filter(
            wallet=wallet,
            timestamp__gte=from_date,
            timestamp__lte=to_date
        ).order_by('timestamp')
        
        if not transactions.exists():
            # No transactions in period, use current balance
            days = (to_date - from_date).days
            return InterestRateCalculator.calculate_interest_breakdown(wallet.balance, days)
        
        # Calculate average balance (simplified - in production you might want more sophisticated averaging)
        total_days = (to_date - from_date).days
        return InterestRateCalculator.calculate_interest_breakdown(wallet.balance, total_days)
    
    @classmethod
    def apply_interest_to_wallet(cls, wallet: Wallet, interest_amount: Money, description: str = "Interest credit") -> Transaction:
        """
        Apply interest to a wallet by creating a credit transaction.
        
        Args:
            wallet: The wallet to credit
            interest_amount: Amount of interest to apply
            description: Description for the transaction
            
        Returns:
            Transaction: The created interest transaction
        """
        if interest_amount.amount <= 0:
            logger.warning(f"Attempted to apply zero or negative interest to wallet {wallet.id}")
            return None
        
        try:
            # Create interest transaction
            transaction = Transaction.objects.create(
                wallet=wallet,
                amount=interest_amount,
                type='credit',
                channel='interest',
                description=description,
                status='success',
                balance_after=wallet.balance + interest_amount
            )
            
            # Update wallet balance
            wallet.balance = wallet.balance + interest_amount
            wallet.save()
            
            logger.info(f"Applied {interest_amount} interest to wallet {wallet.id}")
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to apply interest to wallet {wallet.id}: {str(e)}")
            raise
    
    @classmethod
    def process_monthly_interest(cls, wallet: Wallet) -> Transaction:
        """
        Process monthly interest for a wallet.
        
        Args:
            wallet: The wallet to process interest for
            
        Returns:
            Transaction: The created interest transaction
        """
        now = timezone.now()
        last_month = now.replace(day=1) - timedelta(days=1)
        last_month = last_month.replace(day=1)
        
        interest_calculation = cls.calculate_wallet_interest(wallet, last_month, now)
        interest_amount = interest_calculation['total_interest']
        
        if interest_amount.amount > 0:
            description = f"Monthly interest for {last_month.strftime('%B %Y')}"
            return cls.apply_interest_to_wallet(wallet, interest_amount, description)
        
        return None


class InterestReportService:
    """
    Service for generating interest reports and analytics.
    """
    
    @classmethod
    def generate_interest_report(cls, wallet: Wallet, start_date: datetime, end_date: datetime) -> dict:
        """
        Generate a comprehensive interest report for a wallet.
        
        Args:
            wallet: The wallet to generate report for
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            dict: Comprehensive interest report
        """
        # Get all interest transactions in the period
        interest_transactions = Transaction.objects.filter(
            wallet=wallet,
            channel='interest',
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            status='success'
        ).order_by('timestamp')
        
        total_interest_paid = sum(t.amount.amount for t in interest_transactions)
        
        # Calculate what interest should have been paid
        expected_interest = InterestRateCalculator.calculate_interest_breakdown(
            wallet.balance, 
            (end_date - start_date).days
        )
        
        return {
            'wallet_id': str(wallet.id),
            'account_number': wallet.account_number,
            'user': wallet.user.username,
            'report_period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': (end_date - start_date).days
            },
            'interest_summary': {
                'total_interest_paid': Money(total_interest_paid, 'NGN'),
                'expected_interest': expected_interest['total_interest'],
                'difference': Money(total_interest_paid, 'NGN') - expected_interest['total_interest'],
                'effective_rate': expected_interest['effective_rate']
            },
            'interest_breakdown': expected_interest['breakdown'],
            'transactions': [
                {
                    'id': str(t.id),
                    'amount': str(t.amount),
                    'timestamp': t.timestamp,
                    'description': t.description
                } for t in interest_transactions
            ]
        }
    
    @classmethod
    def get_interest_rates_info(cls) -> dict:
        """
        Get information about current interest rates.
        
        Returns:
            dict: Current interest rate information
        """
        return {
            'tier_1': {
                'threshold': str(InterestRateCalculator.TIER_1_THRESHOLD),
                'rate': f"{InterestRateCalculator.TIER_1_RATE * 100}% p.a.",
                'description': f"Balance up to {InterestRateCalculator.TIER_1_THRESHOLD}"
            },
            'tier_2': {
                'threshold': str(InterestRateCalculator.TIER_2_THRESHOLD),
                'rate': f"{InterestRateCalculator.TIER_2_RATE * 100}% p.a.",
                'description': f"Balance {InterestRateCalculator.TIER_1_THRESHOLD} - {InterestRateCalculator.TIER_2_THRESHOLD}"
            },
            'tier_3': {
                'rate': f"{InterestRateCalculator.TIER_3_RATE * 100}% p.a.",
                'description': f"Balance above {InterestRateCalculator.TIER_2_THRESHOLD}"
            }
        } 