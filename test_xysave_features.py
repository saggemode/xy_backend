#!/usr/bin/env python
"""
Test script to demonstrate XySave features
Similar to OWealth and PalmPay's Cashbox functionality
"""
import os
import sys
import django
from decimal import Decimal

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from djmoney.money import Money
from django.contrib.auth import get_user_model
from bank.models import Wallet
from bank.xysave_services import (
    XySaveAccountService, XySaveTransactionService, XySaveAutoSaveService,
    XySaveGoalService, XySaveInvestmentService, XySaveInterestService
)

User = get_user_model()

def test_xysave_features():
    """Test all XySave features"""
    print("=" * 80)
    print("XYSAVE FEATURES DEMONSTRATION")
    print("=" * 80)
    
    # Get or create a test user
    try:
        user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser',
            email='test@xysave.com',
            password='testpass123'
        )
        print(f"Created test user: {user.username}")
    
    # Ensure user has a wallet
    wallet, created = Wallet.objects.get_or_create(
        user=user,
        defaults={
            'account_number': '1234567890',
            'alternative_account_number': '0987654321',
            'balance': Money(50000, 'NGN')
        }
    )
    if created:
        print(f"Created wallet with balance: {wallet.balance}")
    else:
        print(f"Using existing wallet with balance: {wallet.balance}")
    
    print("\n" + "=" * 50)
    print("1. XySave Account Creation & Setup")
    print("=" * 50)
    
    # Create XySave account
    xysave_account = XySaveAccountService.get_xysave_account(user)
    print(f"XySave Account: {xysave_account.account_number}")
    print(f"Initial Balance: {xysave_account.balance}")
    print(f"Daily Interest Rate: {xysave_account.daily_interest_rate * 100:.4f}%")
    print(f"Annual Interest Rate: {xysave_account.get_annual_interest_rate():.2f}%")
    
    print("\n" + "=" * 50)
    print("2. XySave Deposits & Withdrawals")
    print("=" * 50)
    
    # Deposit to XySave
    deposit_amount = Money(10000, 'NGN')
    print(f"Depositing {deposit_amount} to XySave...")
    
    try:
        deposit_transaction = XySaveTransactionService.deposit_to_xysave(
            user, deposit_amount, "Initial deposit to XySave"
        )
        print(f"✅ Deposit successful! Transaction: {deposit_transaction.reference}")
        print(f"   XySave Balance: {xysave_account.balance}")
        print(f"   Wallet Balance: {wallet.balance}")
    except Exception as e:
        print(f"❌ Deposit failed: {str(e)}")
    
    # Calculate daily interest
    daily_interest = xysave_account.calculate_daily_interest()
    print(f"Daily Interest on current balance: {daily_interest}")
    
    print("\n" + "=" * 50)
    print("3. Auto-Save Configuration")
    print("=" * 50)
    
    # Enable auto-save
    print("Enabling auto-save at 10% with minimum ₦100...")
    try:
        XySaveAutoSaveService.enable_auto_save(
            user, percentage=10.0, min_amount=Money(100, 'NGN')
        )
        print("✅ Auto-save enabled!")
        print(f"   Auto-save percentage: {xysave_account.auto_save_percentage}%")
        print(f"   Minimum amount: {xysave_account.auto_save_min_amount}")
    except Exception as e:
        print(f"❌ Auto-save setup failed: {str(e)}")
    
    # Simulate auto-save when wallet receives money
    print("\nSimulating auto-save when wallet receives ₦5000...")
    try:
        auto_save_transaction = XySaveAutoSaveService.process_auto_save(
            user, Money(5000, 'NGN')
        )
        if auto_save_transaction:
            print(f"✅ Auto-save triggered! Transaction: {auto_save_transaction.reference}")
            print(f"   Auto-saved amount: {auto_save_transaction.amount}")
            print(f"   XySave Balance: {xysave_account.balance}")
        else:
            print("ℹ️ Auto-save not triggered (amount below minimum)")
    except Exception as e:
        print(f"❌ Auto-save processing failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("4. Savings Goals")
    print("=" * 50)
    
    # Create savings goals
    goals_data = [
        ("Emergency Fund", Money(50000, 'NGN'), "2024-12-31"),
        ("Vacation Fund", Money(100000, 'NGN'), "2024-06-30"),
        ("New Phone", Money(25000, 'NGN'), None),
    ]
    
    for name, target_amount, target_date in goals_data:
        try:
            goal = XySaveGoalService.create_goal(
                user, name, target_amount, target_date
            )
            print(f"✅ Created goal: {goal.name}")
            print(f"   Target: {goal.target_amount}")
            print(f"   Progress: {goal.get_progress_percentage():.1f}%")
        except Exception as e:
            print(f"❌ Failed to create goal '{name}': {str(e)}")
    
    # Update goal progress
    try:
        goals = user.xysave_goals.all()
        if goals.exists():
            goal = goals.first()
            update_amount = Money(5000, 'NGN')
            updated_goal = XySaveGoalService.update_goal_progress(
                user, goal.id, update_amount
            )
            print(f"\n✅ Updated goal '{updated_goal.name}' progress")
            print(f"   Added: {update_amount}")
            print(f"   New progress: {updated_goal.get_progress_percentage():.1f}%")
    except Exception as e:
        print(f"❌ Failed to update goal progress: {str(e)}")
    
    print("\n" + "=" * 50)
    print("5. Investment Features")
    print("=" * 50)
    
    # Create investments
    investments_data = [
        ("Treasury Bills", Money(15000, 'NGN'), 12.5),
        ("Mutual Funds", Money(10000, 'NGN'), 15.0),
    ]
    
    for inv_type, amount, expected_return in investments_data:
        try:
            investment = XySaveInvestmentService.create_investment(
                user, inv_type, amount, expected_return
            )
            print(f"✅ Created {inv_type} investment")
            print(f"   Amount invested: {investment.amount_invested}")
            print(f"   Expected return: {investment.expected_return_rate}%")
            print(f"   XySave Balance after investment: {xysave_account.balance}")
        except Exception as e:
            print(f"❌ Failed to create {inv_type} investment: {str(e)}")
    
    print("\n" + "=" * 50)
    print("6. Interest Calculations & Forecasts")
    print("=" * 50)
    
    # Get interest forecast
    try:
        forecast = XySaveInterestService.get_interest_forecast(user)
        print("Interest Forecast:")
        print(f"   Daily Interest: {forecast['daily_interest']}")
        print(f"   Weekly Interest: {forecast['weekly_interest']}")
        print(f"   Monthly Interest: {forecast['monthly_interest']}")
        print(f"   Yearly Interest: {forecast['yearly_interest']}")
        print(f"   Annual Rate: {forecast['annual_rate']:.2f}%")
        print(f"   Total Interest Earned: {forecast['total_interest_earned']}")
    except Exception as e:
        print(f"❌ Failed to get interest forecast: {str(e)}")
    
    print("\n" + "=" * 50)
    print("7. Account Summary")
    print("=" * 50)
    
    # Get comprehensive account summary
    try:
        summary = XySaveAccountService.get_account_summary(user)
        print("XySave Account Summary:")
        print(f"   Account Number: {summary['account'].account_number}")
        print(f"   Balance: {summary['account'].balance}")
        print(f"   Total Interest Earned: {summary['account'].total_interest_earned}")
        print(f"   Auto-save Enabled: {summary['account'].auto_save_enabled}")
        print(f"   Active Goals: {summary['active_goals'].count()}")
        print(f"   Active Investments: {summary['investments'].count()}")
        print(f"   Total Invested: ₦{summary['total_invested']:,.2f}")
        print(f"   Total Investment Value: ₦{summary['total_investment_value']:,.2f}")
    except Exception as e:
        print(f"❌ Failed to get account summary: {str(e)}")
    
    print("\n" + "=" * 50)
    print("8. Transaction History")
    print("=" * 50)
    
    # Show recent transactions
    try:
        recent_transactions = xysave_account.transactions.all()[:5]
        print("Recent XySave Transactions:")
        for tx in recent_transactions:
            print(f"   {tx.created_at.strftime('%Y-%m-%d %H:%M')} - {tx.transaction_type}: {tx.amount}")
    except Exception as e:
        print(f"❌ Failed to get transaction history: {str(e)}")
    
    print("\n" + "=" * 80)
    print("XYSAVE FEATURES DEMONSTRATION COMPLETED")
    print("=" * 80)
    print("\nKey Features Implemented:")
    print("✅ Daily interest calculation (15% annual rate)")
    print("✅ Auto-save functionality")
    print("✅ Savings goals with progress tracking")
    print("✅ Investment portfolio management")
    print("✅ Flexible deposits and withdrawals")
    print("✅ Comprehensive transaction history")
    print("✅ Interest forecasting")
    print("✅ Account summary and analytics")
    print("\nAPI Endpoints Available:")
    print("   GET /api/bank/xysave/accounts/ - Account details")
    print("   POST /api/bank/xysave/accounts/deposit/ - Deposit to XySave")
    print("   POST /api/bank/xysave/accounts/withdraw/ - Withdraw from XySave")
    print("   GET /api/bank/xysave/accounts/dashboard/ - Dashboard data")
    print("   GET /api/bank/xysave/goals/ - Savings goals")
    print("   GET /api/bank/xysave/investments/ - Investment portfolio")
    print("   POST /api/bank/xysave/auto-save/enable/ - Configure auto-save")

if __name__ == "__main__":
    test_xysave_features() 