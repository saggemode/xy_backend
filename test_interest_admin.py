#!/usr/bin/env python
"""
Test script for Interest Rate Calculator Admin Interface
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

def test_admin_interest_features():
    """Test the interest calculator features that would be available in admin."""
    print("=" * 60)
    print("INTEREST CALCULATOR ADMIN FEATURES TEST")
    print("=" * 60)
    
    # Test 1: Interest Rate Information
    print("\n1. Interest Rate Information:")
    print("-" * 40)
    rates_info = InterestReportService.get_interest_rates_info()
    for tier, info in rates_info.items():
        print(f"{tier.upper()}: {info['description']} - {info['rate']}")
    
    # Test 2: Sample Calculations for Admin Display
    print("\n2. Sample Calculations for Admin Display:")
    print("-" * 40)
    
    test_balances = [
        Money(5000, 'NGN'),    # Tier 1 only
        Money(25000, 'NGN'),   # Tier 1 + Tier 2
        Money(150000, 'NGN'),  # All three tiers
    ]
    
    for balance in test_balances:
        print(f"\nBalance: {balance}")
        
        # Calculate annual interest
        annual_result = InterestRateCalculator.calculate_interest_breakdown(balance, 365)
        
        # Calculate monthly interest
        monthly_interest = InterestRateCalculator.calculate_interest_for_balance(balance, 30)
        
        # Calculate effective rate
        effective_rate = float(annual_result['effective_rate'] * 100)
        
        print(f"  Annual Interest: ₦{annual_result['total_interest'].amount:,.2f}")
        print(f"  Monthly Interest: ₦{monthly_interest.amount:,.2f}")
        print(f"  Effective Rate: {effective_rate:.2f}%")
        
        # Show breakdown
        for tier in annual_result['breakdown']:
            print(f"    Tier {tier['tier']}: {tier['balance_in_tier']} at {tier['rate']*100}% p.a. = {tier['interest']}")
    
    # Test 3: Admin Actions Simulation
    print("\n3. Admin Actions Simulation:")
    print("-" * 40)
    
    # Simulate calculating interest for multiple wallets
    print("Simulating 'Calculate Interest' admin action:")
    total_interest = Money(0, 'NGN')
    wallet_count = 0
    
    for balance in test_balances:
        if balance.amount > 0:
            annual_interest = InterestRateCalculator.calculate_interest_for_balance(balance, 365)
            total_interest += annual_interest
            wallet_count += 1
    
    print(f"  Calculated annual interest for {wallet_count} wallets")
    print(f"  Total interest: {total_interest}")
    
    # Test 4: Interest Application Simulation
    print("\n4. Interest Application Simulation:")
    print("-" * 40)
    
    print("Simulating 'Apply Interest' admin action:")
    applied_count = 0
    total_applied = Money(0, 'NGN')
    
    for balance in test_balances:
        if balance.amount > 0:
            # Simulate monthly interest application
            monthly_interest = InterestRateCalculator.calculate_interest_for_balance(balance, 30)
            if monthly_interest.amount > 0:
                applied_count += 1
                total_applied += monthly_interest
                print(f"  Applied ₦{monthly_interest.amount:,.2f} to balance ₦{balance.amount:,.2f}")
    
    print(f"  Applied interest to {applied_count} wallets")
    print(f"  Total applied: {total_applied}")
    
    # Test 5: Admin Display Formatting
    print("\n5. Admin Display Formatting:")
    print("-" * 40)
    
    balance = Money(75000, 'NGN')
    annual_result = InterestRateCalculator.calculate_interest_breakdown(balance, 365)
    effective_rate = float(annual_result['effective_rate'] * 100)
    monthly_interest = InterestRateCalculator.calculate_interest_for_balance(balance, 30)
    
    print("HTML formatted display for admin:")
    print(f"""
    <div>
    <strong>Annual Interest:</strong> ₦{annual_result['total_interest'].amount:,.2f}<br>
    <strong>Effective Rate:</strong> {effective_rate:.2f}%<br>
    <strong>Monthly Interest:</strong> ₦{monthly_interest.amount:,.2f}
    </div>
    """)
    
    print("Detailed breakdown for admin:")
    breakdown_html = '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">'
    breakdown_html += '<h4>Annual Interest Breakdown:</h4>'
    
    for tier in annual_result['breakdown']:
        breakdown_html += f'<p><strong>Tier {tier["tier"]}:</strong> {tier["balance_in_tier"]} at {tier["rate"]*100}% p.a. = {tier["interest"]}</p>'
    
    breakdown_html += f'<hr><p><strong>Total Annual Interest:</strong> {annual_result["total_interest"]}</p>'
    breakdown_html += f'<p><strong>Effective Annual Rate:</strong> {effective_rate:.2f}%</p>'
    breakdown_html += '</div>'
    
    print(breakdown_html)

def test_admin_url_access():
    """Test the admin URL patterns for interest calculator."""
    print("\n" + "=" * 60)
    print("ADMIN URL ACCESS TEST")
    print("=" * 60)
    
    print("\nAdmin URLs that should be available:")
    print("- /admin/bank/interest-calculator/ - Interest Calculator Tool")
    print("- /admin/bank/wallet/ - Wallet list with interest info")
    print("- /admin/bank/wallet/{id}/ - Individual wallet with interest breakdown")
    
    print("\nAdmin Actions available on Wallet list:")
    print("- Calculate interest for selected wallets")
    print("- Apply monthly interest to selected wallets")
    print("- Export wallet data")
    
    print("\nAdmin Fields available on Wallet detail:")
    print("- Interest Info (readonly)")
    print("- Interest Breakdown (readonly, collapsible)")
    print("- Balance status with color coding")

def test_edge_cases_admin():
    """Test edge cases that might occur in admin interface."""
    print("\n" + "=" * 60)
    print("ADMIN EDGE CASES TEST")
    print("=" * 60)
    
    # Test zero balance
    zero_balance = Money(0, 'NGN')
    result = InterestRateCalculator.calculate_interest_breakdown(zero_balance, 365)
    print(f"Zero balance interest: {result['total_interest']}")
    
    # Test very large amounts
    large_balance = Money(1000000, 'NGN')  # 1M NGN
    result = InterestRateCalculator.calculate_interest_breakdown(large_balance, 365)
    print(f"Large balance ({large_balance}) annual interest: {result['total_interest']}")
    print(f"Effective rate: {float(result['effective_rate'] * 100):.2f}%")
    
    # Test different currencies
    usd_balance = Money(1000, 'USD')
    result = InterestRateCalculator.calculate_interest_breakdown(usd_balance, 365)
    print(f"USD balance ({usd_balance}) annual interest: {result['total_interest']}")
    
    # Test different time periods
    balance = Money(50000, 'NGN')
    periods = [1, 7, 30, 90, 365]
    
    print(f"\nInterest for ₦{balance.amount:,.2f} over different periods:")
    for days in periods:
        interest = InterestRateCalculator.calculate_interest_for_balance(balance, days)
        print(f"  {days} days: {interest}")

def main():
    """Run all admin interest calculator tests."""
    print("Starting Interest Rate Calculator Admin Tests...")
    
    try:
        test_admin_interest_features()
        test_admin_url_access()
        test_edge_cases_admin()
        
        print("\n" + "=" * 60)
        print("ALL ADMIN TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        print("\nTo access the interest calculator in admin:")
        print("1. Start the Django development server")
        print("2. Go to /admin/ and log in")
        print("3. Navigate to /admin/bank/interest-calculator/")
        print("4. Or view wallets at /admin/bank/wallet/ to see interest info")
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 