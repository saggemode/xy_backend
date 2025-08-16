#!/usr/bin/env python
"""
Script to find the exact interest rates that would produce the expected values.
"""
import os
import sys
import django
from decimal import Decimal

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from djmoney.money import Money

def find_correct_tier_3_rate():
    """Find what Tier 3 rate would give the expected annual interest."""
    print("=" * 60)
    print("FINDING CORRECT TIER 3 RATE")
    print("=" * 60)
    
    balance = Decimal('1000000')
    tier_1_interest = Decimal('10000') * Decimal('0.20')  # 2,000
    tier_2_interest = Decimal('90000') * Decimal('0.16')  # 14,400
    tier_3_balance = Decimal('900000')
    
    expected_annual = Decimal('88432.03')
    required_tier_3_interest = expected_annual - tier_1_interest - tier_2_interest
    
    print(f"Expected annual interest: ₦{expected_annual:,.2f}")
    print(f"Tier 1 interest (10,000 × 20%): ₦{tier_1_interest:,.2f}")
    print(f"Tier 2 interest (90,000 × 16%): ₦{tier_2_interest:,.2f}")
    print(f"Required Tier 3 interest: ₦{required_tier_3_interest:,.2f}")
    
    # Calculate the rate needed for Tier 3
    tier_3_rate = required_tier_3_interest / tier_3_balance
    tier_3_rate_percent = tier_3_rate * Decimal('100')
    
    print(f"\nTier 3 rate needed: {tier_3_rate_percent:.2f}%")
    print(f"Current Tier 3 rate: 6.00%")
    print(f"Difference: {tier_3_rate_percent - Decimal('6.00'):.2f}%")
    
    # Verify the calculation
    calculated_annual = tier_1_interest + tier_2_interest + (tier_3_balance * tier_3_rate)
    print(f"\nVerification:")
    print(f"Calculated annual: ₦{calculated_annual:,.2f}")
    print(f"Expected annual: ₦{expected_annual:,.2f}")
    print(f"Match: {calculated_annual == expected_annual}")
    
    return tier_3_rate

def test_alternative_tier_structure():
    """Test alternative tier structures."""
    print(f"\n" + "=" * 60)
    print("ALTERNATIVE TIER STRUCTURES")
    print("=" * 60)
    
    balance = Decimal('1000000')
    expected_annual = Decimal('88432.03')
    
    # Test 1: Different Tier 2 threshold (50,000 instead of 100,000)
    print("Test 1: Tier 2 threshold = 50,000")
    tier_1_alt1 = Decimal('10000') * Decimal('0.20')  # 2,000
    tier_2_alt1 = Decimal('40000') * Decimal('0.16')  # 6,400 (50,000 - 10,000)
    tier_3_alt1 = Decimal('950000') * Decimal('0.06') # 57,000 (1,000,000 - 50,000)
    total_alt1 = tier_1_alt1 + tier_2_alt1 + tier_3_alt1
    print(f"  Annual interest: ₦{total_alt1:,.2f}")
    print(f"  Difference from expected: ₦{expected_annual - total_alt1:,.2f}")
    
    # Test 2: Higher Tier 2 rate
    print("\nTest 2: Tier 2 rate = 18%")
    tier_1_alt2 = Decimal('10000') * Decimal('0.20')  # 2,000
    tier_2_alt2 = Decimal('90000') * Decimal('0.18')  # 16,200
    tier_3_alt2 = Decimal('900000') * Decimal('0.06') # 54,000
    total_alt2 = tier_1_alt2 + tier_2_alt2 + tier_3_alt2
    print(f"  Annual interest: ₦{total_alt2:,.2f}")
    print(f"  Difference from expected: ₦{expected_annual - total_alt2:,.2f}")
    
    # Test 3: Compound interest (daily compounding)
    print("\nTest 3: Daily compound interest")
    daily_rate_1 = Decimal('0.20') / Decimal('365')
    daily_rate_2 = Decimal('0.16') / Decimal('365')
    daily_rate_3 = Decimal('0.06') / Decimal('365')
    
    # Calculate compound interest for 365 days
    tier_1_compound = Decimal('10000') * ((Decimal('1') + daily_rate_1) ** Decimal('365') - Decimal('1'))
    tier_2_compound = Decimal('90000') * ((Decimal('1') + daily_rate_2) ** Decimal('365') - Decimal('1'))
    tier_3_compound = Decimal('900000') * ((Decimal('1') + daily_rate_3) ** Decimal('365') - Decimal('1'))
    total_compound = tier_1_compound + tier_2_compound + tier_3_compound
    print(f"  Annual compound interest: ₦{total_compound:,.2f}")
    print(f"  Difference from expected: ₦{expected_annual - total_compound:,.2f}")

def calculate_with_corrected_rate():
    """Calculate interest using the corrected Tier 3 rate."""
    print(f"\n" + "=" * 60)
    print("CALCULATION WITH CORRECTED RATE")
    print("=" * 60)
    
    # Use the rate we found
    tier_3_rate = Decimal('0.0782578111111111111111111111')  # ~7.83%
    
    balance = Money(1000000, 'NGN')
    
    # Manual calculation with corrected rate
    tier_1_annual = Decimal('10000') * Decimal('0.20')  # 2,000
    tier_2_annual = Decimal('90000') * Decimal('0.16')  # 14,400
    tier_3_annual = Decimal('900000') * tier_3_rate     # 70,432.03
    
    total_annual = tier_1_annual + tier_2_annual + tier_3_annual
    
    print(f"Tier 1 (10,000 × 20%): ₦{tier_1_annual:,.2f}")
    print(f"Tier 2 (90,000 × 16%): ₦{tier_2_annual:,.2f}")
    print(f"Tier 3 (900,000 × {tier_3_rate*100:.2f}%): ₦{tier_3_annual:,.2f}")
    print(f"Total Annual: ₦{total_annual:,.2f}")
    
    # Calculate periods
    daily = total_annual / Decimal('365')
    weekly = daily * Decimal('7')
    monthly = daily * Decimal('30')
    
    print(f"\nPeriod calculations:")
    print(f"Daily: ₦{daily:,.2f}")
    print(f"Weekly: ₦{weekly:,.2f}")
    print(f"Monthly: ₦{monthly:,.2f}")
    print(f"Annual: ₦{total_annual:,.2f}")
    
    print(f"\nExpected values:")
    print(f"Daily: ₦231.00")
    print(f"Monthly: ₦6,969.09")
    print(f"Annual: ₦88,432.03")
    
    print(f"\nMatch check:")
    print(f"Daily match: {abs(daily - Decimal('231.00')) < Decimal('0.01')}")
    print(f"Monthly match: {abs(monthly - Decimal('6969.09')) < Decimal('0.01')}")
    print(f"Annual match: {abs(total_annual - Decimal('88432.03')) < Decimal('0.01')}")

if __name__ == "__main__":
    find_correct_tier_3_rate()
    test_alternative_tier_structure()
    calculate_with_corrected_rate() 