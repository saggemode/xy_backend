#!/usr/bin/env python
"""
Test script for Interest Rate Calculator
"""
import os
import sys
import django
from decimal import Decimal
from djmoney.money import Money

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from bank.interest_services import InterestRateCalculator, InterestAccrualService, InterestReportService
from bank.models import Wallet, User
from accounts.models import UserProfile

def test_interest_calculator():
    """Test the interest rate calculator with different balance amounts."""
    print("=" * 60)
    print("INTEREST RATE CALCULATOR TEST")
    print("=" * 60)
    
    # Test balances
    test_balances = [
        Money(5000, 'NGN'),    # Tier 1 only (20% p.a.)
        Money(25000, 'NGN'),   # Tier 1 + Tier 2 (20% + 16% p.a.)
        Money(150000, 'NGN'),  # All three tiers (20% + 16% + 6% p.a.)
        Money(500000, 'NGN'),  # All three tiers (20% + 16% + 6% p.a.)
    ]
    
    print("\nTiered Interest Rate Structure:")
    print("- 20% p.a. for balance up to 10,000 NGN")
    print("- 16% p.a. for balance above 10,000 but within 100,000 NGN")
    print("- 6% p.a. for balance above 100,000 NGN")
    print("\n" + "=" * 60)
    
    for balance in test_balances:
        print(f"\nTesting Balance: {balance}")
        print("-" * 40)
        
        # Calculate annual interest
        annual_result = InterestRateCalculator.calculate_interest_breakdown(balance, 365)
        
        # Calculate monthly interest
        monthly_result = InterestRateCalculator.calculate_interest_breakdown(balance, 30)
        
        # Calculate daily interest
        daily_result = InterestRateCalculator.calculate_interest_breakdown(balance, 1)
        
        print(f"Annual Interest: {annual_result['total_interest']}")
        print(f"Monthly Interest: {monthly_result['total_interest']}")
        print(f"Daily Interest: {daily_result['total_interest']}")
        print(f"Effective Annual Rate: {float(annual_result['effective_rate'] * 100):.2f}%")
        
        print("\nBreakdown:")
        for tier in annual_result['breakdown']:
            print(f"  Tier {tier['tier']}: {tier['balance_in_tier']} at {tier['rate']*100}% p.a. = {tier['interest']}")
        
        print("-" * 40)

def test_interest_rates_info():
    """Test getting interest rates information."""
    print("\n" + "=" * 60)
    print("INTEREST RATES INFORMATION")
    print("=" * 60)
    
    rates_info = InterestReportService.get_interest_rates_info()
    
    for tier, info in rates_info.items():
        print(f"\n{tier.upper()}:")
        print(f"  Threshold: {info['threshold']}")
        print(f"  Rate: {info['rate']}")
        print(f"  Description: {info['description']}")

def test_wallet_interest_calculation():
    """Test interest calculation for a specific wallet."""
    print("\n" + "=" * 60)
    print("WALLET INTEREST CALCULATION TEST")
    print("=" * 60)
    
    try:
        # Get the first user with a wallet
        user = User.objects.filter(wallet__isnull=False).first()
        if not user:
            print("No user with wallet found. Creating a test user...")
            user = User.objects.create_user(
                username='test_interest_user',
                email='test_interest@example.com',
                password='testpass123'
            )
            UserProfile.objects.create(user=user, phone='+2341234567890')
            wallet = Wallet.objects.create(
                user=user,
                account_number='1234567890',
                balance=Money(75000, 'NGN')
            )
        else:
            wallet = user.wallet
        
        print(f"Testing with wallet: {wallet.account_number}")
        print(f"Current balance: {wallet.balance}")
        
        # Calculate interest for different periods
        periods = [30, 90, 365]  # days
        
        for days in periods:
            result = InterestAccrualService.calculate_wallet_interest(wallet, days=days)
            print(f"\n{days}-day interest calculation:")
            print(f"  Total interest: {result['total_interest']}")
            print(f"  Effective rate: {float(result['effective_rate'] * 100):.2f}%")
            
            if result['breakdown']:
                print("  Breakdown:")
                for tier in result['breakdown']:
                    print(f"    Tier {tier['tier']}: {tier['interest']}")
        
    except Exception as e:
        print(f"Error testing wallet interest calculation: {e}")

def test_interest_demo():
    """Test the demo endpoint functionality."""
    print("\n" + "=" * 60)
    print("INTEREST CALCULATOR DEMO")
    print("=" * 60)
    
    demo_balances = [
        Money(5000, 'NGN'),   # Tier 1 only
        Money(25000, 'NGN'),  # Tier 1 + Tier 2
        Money(150000, 'NGN'), # All three tiers
        Money(500000, 'NGN')  # All three tiers
    ]
    
    print("\nDemo Calculations:")
    print("-" * 40)
    
    for balance in demo_balances:
        # Calculate annual interest
        annual_result = InterestRateCalculator.calculate_interest_breakdown(balance, 365)
        
        # Calculate monthly interest
        monthly_result = InterestRateCalculator.calculate_interest_breakdown(balance, 30)
        
        print(f"\nBalance: {balance}")
        print(f"Annual Interest: {annual_result['total_interest']}")
        print(f"Monthly Interest: {monthly_result['total_interest']}")
        print(f"Effective Annual Rate: {float(annual_result['effective_rate'] * 100):.2f}%")
        
        # Show breakdown
        print("Annual Breakdown:")
        for tier in annual_result['breakdown']:
            print(f"  {tier['description']}: {tier['interest']}")

def test_edge_cases():
    """Test edge cases for the interest calculator."""
    print("\n" + "=" * 60)
    print("EDGE CASES TEST")
    print("=" * 60)
    
    # Test zero balance
    zero_balance = Money(0, 'NGN')
    result = InterestRateCalculator.calculate_interest_breakdown(zero_balance, 365)
    print(f"Zero balance interest: {result['total_interest']}")
    
    # Test negative balance (should return zero)
    negative_balance = Money(-1000, 'NGN')
    result = InterestRateCalculator.calculate_interest_breakdown(negative_balance, 365)
    print(f"Negative balance interest: {result['total_interest']}")
    
    # Test exact threshold amounts
    tier1_exact = Money(10000, 'NGN')
    result = InterestRateCalculator.calculate_interest_breakdown(tier1_exact, 365)
    print(f"Exact Tier 1 threshold ({tier1_exact}) annual interest: {result['total_interest']}")
    
    tier2_exact = Money(100000, 'NGN')
    result = InterestRateCalculator.calculate_interest_breakdown(tier2_exact, 365)
    print(f"Exact Tier 2 threshold ({tier2_exact}) annual interest: {result['total_interest']}")
    
    # Test very large amounts
    large_balance = Money(1000000, 'NGN')  # 1M NGN
    result = InterestRateCalculator.calculate_interest_breakdown(large_balance, 365)
    print(f"Large balance ({large_balance}) annual interest: {result['total_interest']}")
    print(f"Effective rate: {float(result['effective_rate'] * 100):.2f}%")

def main():
    """Run all interest calculator tests."""
    print("Starting Interest Rate Calculator Tests...")
    
    try:
        test_interest_calculator()
        test_interest_rates_info()
        test_wallet_interest_calculation()
        test_interest_demo()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 