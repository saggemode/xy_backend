#!/usr/bin/env python
"""
Test script to verify interest calculation for 1,000,000 NGN
and identify discrepancy with expected values.
"""
import os
import sys
import django
from decimal import Decimal

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from djmoney.money import Money
from bank.interest_services import InterestRateCalculator

def test_1m_ngn_calculation():
    """Test interest calculation for 1,000,000 NGN."""
    print("=" * 60)
    print("INTEREST CALCULATION TEST FOR 1,000,000 NGN")
    print("=" * 60)
    
    balance = Money(1000000, 'NGN')
    
    print(f"\nBalance: {balance}")
    print(f"Tier 1 Threshold: {InterestRateCalculator.TIER_1_THRESHOLD} (20% p.a.)")
    print(f"Tier 2 Threshold: {InterestRateCalculator.TIER_2_THRESHOLD} (16% p.a.)")
    print(f"Tier 3 Rate: {InterestRateCalculator.TIER_3_RATE*100}% p.a.")
    
    # Calculate annual interest
    annual_result = InterestRateCalculator.calculate_interest_breakdown(balance, 365)
    
    print(f"\nANNUAL INTEREST BREAKDOWN:")
    print("-" * 40)
    print(f"Total Annual Interest: {annual_result['total_interest']}")
    print(f"Effective Annual Rate: {float(annual_result['effective_rate'] * 100):.2f}%")
    
    print(f"\nDetailed Breakdown:")
    for tier in annual_result['breakdown']:
        print(f"  Tier {tier['tier']}: {tier['balance_in_tier']} at {tier['rate']*100}% p.a. = {tier['interest']}")
    
    # Calculate different periods
    daily_interest = InterestRateCalculator.calculate_interest_for_balance(balance, 1)
    weekly_interest = InterestRateCalculator.calculate_interest_for_balance(balance, 7)
    monthly_interest = InterestRateCalculator.calculate_interest_for_balance(balance, 30)
    
    print(f"\nINTEREST FOR DIFFERENT PERIODS:")
    print("-" * 40)
    print(f"Daily Interest (1 day): {daily_interest}")
    print(f"Weekly Interest (7 days): {weekly_interest}")
    print(f"Monthly Interest (30 days): {monthly_interest}")
    print(f"Annual Interest (365 days): {annual_result['total_interest']}")
    
    # Manual calculation verification
    print(f"\nMANUAL CALCULATION VERIFICATION:")
    print("-" * 40)
    
    # For 1,000,000 NGN:
    # Tier 1: 10,000 at 20% p.a.
    # Tier 2: 90,000 at 16% p.a. (100,000 - 10,000)
    # Tier 3: 900,000 at 6% p.a. (1,000,000 - 100,000)
    
    tier_1_annual = Decimal('10000') * Decimal('0.20')  # 2,000
    tier_2_annual = Decimal('90000') * Decimal('0.16')  # 14,400
    tier_3_annual = Decimal('900000') * Decimal('0.08') # 72,000
    
    total_annual_manual = tier_1_annual + tier_2_annual + tier_3_annual  # 88,400
    
    print(f"Manual calculation:")
    print(f"  Tier 1 (10,000 × 20%): ₦{tier_1_annual:,.2f}")
    print(f"  Tier 2 (90,000 × 16%): ₦{tier_2_annual:,.2f}")
    print(f"  Tier 3 (900,000 × 8%): ₦{tier_3_annual:,.2f}")
    print(f"  Total Annual: ₦{total_annual_manual:,.2f}")
    
    # Calculate daily, weekly, monthly from manual annual
    daily_manual = total_annual_manual / Decimal('365')
    weekly_manual = daily_manual * Decimal('7')
    monthly_manual = daily_manual * Decimal('30')
    
    print(f"\nManual period calculations:")
    print(f"  Daily: ₦{daily_manual:,.2f}")
    print(f"  Weekly: ₦{weekly_manual:,.2f}")
    print(f"  Monthly: ₦{monthly_manual:,.2f}")
    print(f"  Annual: ₦{total_annual_manual:,.2f}")
    
    # Compare with your expected values
    print(f"\nCOMPARISON WITH YOUR EXPECTED VALUES:")
    print("-" * 40)
    print(f"Your expected values:")
    print(f"  Daily: ₦231.00")
    print(f"  Monthly: ₦6,969.09")
    print(f"  Yearly: ₦88,432.03")
    
    print(f"\nMy calculated values:")
    print(f"  Daily: ₦{daily_interest.amount:,.2f}")
    print(f"  Monthly: ₦{monthly_interest.amount:,.2f}")
    print(f"  Yearly: ₦{annual_result['total_interest'].amount:,.2f}")
    
    # Calculate what rate would give your expected annual value
    your_annual = Decimal('88432.03')
    effective_rate_for_your_value = (your_annual / Decimal('1000000')) * Decimal('100')
    
    print(f"\nANALYSIS:")
    print("-" * 40)
    print(f"Your expected annual interest: ₦{your_annual:,.2f}")
    print(f"This represents an effective rate of: {effective_rate_for_your_value:.2f}% p.a.")
    print(f"My calculated effective rate: {float(annual_result['effective_rate'] * 100):.2f}% p.a.")
    
    # Check if there's a different tier structure
    print(f"\nPOSSIBLE EXPLANATIONS:")
    print("-" * 40)
    print("1. Different tier thresholds (maybe 50,000 instead of 100,000?)")
    print("2. Different interest rates")
    print("3. Different calculation method (simple vs compound)")
    print("4. Different day count convention (365 vs 360 days)")
    
    # Test with different thresholds
    print(f"\nTESTING DIFFERENT THRESHOLDS:")
    print("-" * 40)
    
    # Test with 50,000 threshold
    print("If Tier 2 threshold was 50,000 instead of 100,000:")
    tier_1_alt = Decimal('10000') * Decimal('0.20')  # 2,000
    tier_2_alt = Decimal('40000') * Decimal('0.16')  # 6,400 (50,000 - 10,000)
    tier_3_alt = Decimal('950000') * Decimal('0.06') # 57,000 (1,000,000 - 50,000)
    total_alt = tier_1_alt + tier_2_alt + tier_3_alt  # 65,400
    
    print(f"  Annual interest would be: ₦{total_alt:,.2f}")
    print(f"  Daily interest would be: ₦{total_alt/365:,.2f}")
    
    # Test with 6.5% for tier 3
    print("\nIf Tier 3 rate was 6.5% instead of 6%:")
    tier_3_alt2 = Decimal('900000') * Decimal('0.065') # 58,500
    total_alt2 = tier_1_annual + tier_2_annual + tier_3_alt2  # 74,900
    
    print(f"  Annual interest would be: ₦{total_alt2:,.2f}")
    print(f"  Daily interest would be: ₦{total_alt2/365:,.2f}")

def test_alternative_calculation():
    """Test alternative calculation methods."""
    print(f"\n" + "=" * 60)
    print("ALTERNATIVE CALCULATION METHODS")
    print("=" * 60)
    
    balance = Money(1000000, 'NGN')
    
    # Method 1: Using 360 days instead of 365
    print(f"\nMethod 1: Using 360 days instead of 365")
    daily_rate_360 = Decimal('0.20') / Decimal('360')  # Tier 1 daily rate
    tier_1_daily_360 = Decimal('10000') * daily_rate_360
    tier_2_daily_360 = Decimal('90000') * (Decimal('0.16') / Decimal('360'))
    tier_3_daily_360 = Decimal('900000') * (Decimal('0.06') / Decimal('360'))
    total_daily_360 = tier_1_daily_360 + tier_2_daily_360 + tier_3_daily_360
    
    print(f"  Daily interest (360 days): ₦{total_daily_360:,.2f}")
    print(f"  Annual interest (360 days): ₦{total_daily_360 * 365:,.2f}")
    
    # Method 2: Simple interest calculation
    print(f"\nMethod 2: Simple interest (no daily compounding)")
    tier_1_simple = Decimal('10000') * Decimal('0.20')
    tier_2_simple = Decimal('90000') * Decimal('0.16')
    tier_3_simple = Decimal('900000') * Decimal('0.06')
    total_simple = tier_1_simple + tier_2_simple + tier_3_simple
    
    print(f"  Annual interest (simple): ₦{total_simple:,.2f}")
    print(f"  Daily interest (simple): ₦{total_simple/365:,.2f}")

if __name__ == "__main__":
    test_1m_ngn_calculation()
    test_alternative_calculation() 