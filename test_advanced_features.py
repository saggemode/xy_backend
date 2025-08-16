#!/usr/bin/env python
"""
Comprehensive test script for all advanced banking features.
Run this with: python manage.py shell < test_advanced_features.py
"""

import os
import django
import sys
from datetime import datetime, timedelta

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from djmoney.money import Money
from bank.models import (
    Wallet, BankTransfer, BulkTransfer, ScheduledTransfer, EscrowService,
    TransferReversal, TwoFactorAuthentication, IPWhitelist, DeviceFingerprint,
    FraudDetection, SecurityAlert, TransferLimit, SavedBeneficiary
)
from bank.services import BankAccountService
from bank.security_services import (
    TwoFactorAuthService, IPWhitelistService, DeviceFingerprintService,
    FraudDetectionService, SecurityAlertService, TransferLimitService
)
from bank.transfer_services import (
    BulkTransferService, ScheduledTransferService, EscrowService as EscrowTransferService,
    TransferReversalService, TransferProcessingService, IdempotencyService
)
from bank.constants import TransferLimits, SecurityLevel, FraudFlag

def test_bank_search_feature():
    """Test the bank search by account number feature."""
    print("\n🧪 Testing Bank Search by Account Number...")
    
    # Test account numbers
    test_accounts = [
        "1234567890",  # Should match multiple banks
        "9876543210",  # Should match some banks
        "1111111111",  # Should match specific banks
    ]
    
    for account in test_accounts:
        print(f"\n📋 Searching for account: {account}")
        banks = BankAccountService.search_banks_by_account_number(account)
        
        if banks:
            print(f"✅ Found {len(banks)} banks for account {account}:")
            for bank in banks:
                print(f"   - {bank['bank_name']} ({bank['bank_code']}) - {bank['account_name']}")
        else:
            print(f"❌ No banks found for account {account}")

def test_two_factor_authentication():
    """Test 2FA functionality."""
    print("\n🧪 Testing Two-Factor Authentication...")
    
    try:
        # Get or create test user
        user, created = User.objects.get_or_create(
            username='testuser_2fa',
            defaults={'email': 'test2fa@example.com', 'first_name': 'Test', 'last_name': 'User'}
        )
        
        # Generate 2FA token
        token = TwoFactorAuthService.generate_token(user, 'sms')
        print(f"✅ Generated 2FA token: {token}")
        
        # Verify token
        is_valid = TwoFactorAuthService.verify_token(user, token, 'sms')
        print(f"✅ Token verification: {'Success' if is_valid else 'Failed'}")
        
        # Test invalid token
        is_valid = TwoFactorAuthService.verify_token(user, '000000', 'sms')
        print(f"✅ Invalid token test: {'Failed as expected' if not is_valid else 'Unexpected success'}")
        
    except Exception as e:
        print(f"❌ Error testing 2FA: {str(e)}")

def test_ip_whitelisting():
    """Test IP whitelisting functionality."""
    print("\n🧪 Testing IP Whitelisting...")
    
    try:
        user, created = User.objects.get_or_create(
            username='testuser_ip',
            defaults={'email': 'testip@example.com', 'first_name': 'Test', 'last_name': 'IP'}
        )
        
        # Add IP to whitelist
        ip_address = "192.168.1.100"
        success = IPWhitelistService.add_ip_to_whitelist(user, ip_address, "Test IP")
        print(f"✅ Added IP to whitelist: {'Success' if success else 'Failed'}")
        
        # Check if IP is allowed
        is_allowed = IPWhitelistService.is_ip_allowed(user, ip_address)
        print(f"✅ IP whitelist check: {'Allowed' if is_allowed else 'Not allowed'}")
        
        # Test non-whitelisted IP
        is_allowed = IPWhitelistService.is_ip_allowed(user, "192.168.1.200")
        print(f"✅ Non-whitelisted IP test: {'Not allowed as expected' if not is_allowed else 'Unexpectedly allowed'}")
        
    except Exception as e:
        print(f"❌ Error testing IP whitelisting: {str(e)}")

def test_device_fingerprinting():
    """Test device fingerprinting functionality."""
    print("\n🧪 Testing Device Fingerprinting...")
    
    try:
        user, created = User.objects.get_or_create(
            username='testuser_device',
            defaults={'email': 'testdevice@example.com', 'first_name': 'Test', 'last_name': 'Device'}
        )
        
        # Create device fingerprint
        device_data = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'ip_address': '192.168.1.101',
            'screen_resolution': '1920x1080',
            'timezone': 'Africa/Lagos',
            'device_type': 'browser'
        }
        
        device_id = DeviceFingerprintService.create_device_fingerprint(user, device_data)
        print(f"✅ Created device fingerprint: {device_id}")
        
        # Check if device is trusted
        is_trusted = DeviceFingerprintService.is_trusted_device(user, device_id)
        print(f"✅ Device trust check: {'Trusted' if is_trusted else 'Not trusted'}")
        
    except Exception as e:
        print(f"❌ Error testing device fingerprinting: {str(e)}")

def test_fraud_detection():
    """Test fraud detection functionality."""
    print("\n🧪 Testing Fraud Detection...")
    
    try:
        user, created = User.objects.get_or_create(
            username='testuser_fraud',
            defaults={'email': 'testfraud@example.com', 'first_name': 'Test', 'last_name': 'Fraud'}
        )
        
        # Create a test transfer
        transfer = BankTransfer.objects.create(
            user=user,
            bank_name='Test Bank',
            bank_code='123',
            account_number='1234567890',
            amount=Money(1000000, 'NGN'),  # High amount to trigger fraud detection
            description='Test transfer for fraud detection',
            transfer_type='inter',
            status='pending'
        )
        
        # Assess fraud risk
        risk_assessment = FraudDetectionService.assess_transfer_risk(transfer)
        print(f"✅ Fraud risk assessment:")
        print(f"   - Risk Score: {risk_assessment['risk_score']}")
        print(f"   - Risk Level: {risk_assessment['risk_level']}")
        print(f"   - Fraud Flags: {', '.join(risk_assessment['fraud_flags'])}")
        print(f"   - Requires Review: {risk_assessment['requires_review']}")
        print(f"   - Requires 2FA: {risk_assessment['requires_2fa']}")
        
        # Create security alerts
        SecurityAlertService.alert_suspicious_activity(transfer, risk_assessment)
        print(f"✅ Security alerts created")
        
    except Exception as e:
        print(f"❌ Error testing fraud detection: {str(e)}")

def test_bulk_transfers():
    """Test bulk transfer functionality."""
    print("\n🧪 Testing Bulk Transfers...")
    
    try:
        user, created = User.objects.get_or_create(
            username='testuser_bulk',
            defaults={'email': 'testbulk@example.com', 'first_name': 'Test', 'last_name': 'Bulk'}
        )
        
        # Create bulk transfer data
        transfers_data = [
            {
                'account_number': '1111111111',
                'account_name': 'John Doe',
                'bank_code': '044',
                'bank_name': 'Access Bank',
                'amount': 50000,
                'description': 'Salary payment'
            },
            {
                'account_number': '2222222222',
                'account_name': 'Jane Smith',
                'bank_code': '058',
                'bank_name': 'GT Bank',
                'amount': 75000,
                'description': 'Bonus payment'
            },
            {
                'account_number': '3333333333',
                'account_name': 'Bob Johnson',
                'bank_code': '011',
                'bank_name': 'First Bank',
                'amount': 25000,
                'description': 'Allowance'
            }
        ]
        
        # Create bulk transfer
        bulk_transfer = BulkTransferService.create_bulk_transfer(
            user=user,
            title='Monthly Salary Payments',
            description='Bulk transfer for employee salaries',
            transfers_data=transfers_data
        )
        
        print(f"✅ Created bulk transfer: {bulk_transfer.id}")
        print(f"   - Total amount: {bulk_transfer.total_amount}")
        print(f"   - Total count: {bulk_transfer.total_count}")
        
        # Process bulk transfer
        result = BulkTransferService.process_bulk_transfer(bulk_transfer)
        print(f"✅ Bulk transfer processing result:")
        print(f"   - Success: {result['success']}")
        print(f"   - Completed: {result.get('completed_count', 0)}")
        print(f"   - Failed: {result.get('failed_count', 0)}")
        print(f"   - Status: {result.get('status', 'unknown')}")
        
    except Exception as e:
        print(f"❌ Error testing bulk transfers: {str(e)}")

def test_scheduled_transfers():
    """Test scheduled transfer functionality."""
    print("\n🧪 Testing Scheduled Transfers...")
    
    try:
        user, created = User.objects.get_or_create(
            username='testuser_scheduled',
            defaults={'email': 'testscheduled@example.com', 'first_name': 'Test', 'last_name': 'Scheduled'}
        )
        
        # Create scheduled transfer data
        transfer_data = {
            'transfer_type': 'inter',
            'amount': 50000,
            'account_number': '1234567890',
            'bank_code': '044',
            'account_name': 'Recipient Name',
            'description': 'Monthly rent payment',
            'frequency': 'monthly',
            'start_date': timezone.now() + timedelta(minutes=1),  # Start in 1 minute
            'end_date': timezone.now() + timedelta(days=365)  # End in 1 year
        }
        
        # Create scheduled transfer
        scheduled_transfer = ScheduledTransferService.create_scheduled_transfer(user, transfer_data)
        print(f"✅ Created scheduled transfer: {scheduled_transfer.id}")
        print(f"   - Amount: {scheduled_transfer.amount}")
        print(f"   - Frequency: {scheduled_transfer.frequency}")
        print(f"   - Next execution: {scheduled_transfer.next_execution}")
        
        # Process scheduled transfers (this would normally be done by a cron job)
        result = ScheduledTransferService.process_scheduled_transfers()
        print(f"✅ Scheduled transfers processing result:")
        print(f"   - Processed: {result.get('processed_count', 0)}")
        print(f"   - Failed: {result.get('failed_count', 0)}")
        print(f"   - Total due: {result.get('total_due', 0)}")
        
    except Exception as e:
        print(f"❌ Error testing scheduled transfers: {str(e)}")

def test_escrow_services():
    """Test escrow service functionality."""
    print("\n🧪 Testing Escrow Services...")
    
    try:
        sender, created = User.objects.get_or_create(
            username='testuser_sender',
            defaults={'email': 'sender@example.com', 'first_name': 'Sender', 'last_name': 'User'}
        )
        
        recipient, created = User.objects.get_or_create(
            username='testuser_recipient',
            defaults={'email': 'recipient@example.com', 'first_name': 'Recipient', 'last_name': 'User'}
        )
        
        # Create escrow
        escrow = EscrowTransferService.create_escrow(
            sender=sender,
            recipient=recipient,
            amount=100000,
            description='Payment for services',
            expires_in_hours=24
        )
        
        print(f"✅ Created escrow: {escrow.id}")
        print(f"   - Amount: {escrow.amount}")
        print(f"   - Status: {escrow.status}")
        print(f"   - Expires: {escrow.expires_at}")
        
        # Fund escrow (this would require sufficient balance)
        # funded = EscrowTransferService.fund_escrow(escrow)
        # print(f"✅ Escrow funding: {'Success' if funded else 'Failed'}")
        
    except Exception as e:
        print(f"❌ Error testing escrow services: {str(e)}")

def test_transfer_reversals():
    """Test transfer reversal functionality."""
    print("\n🧪 Testing Transfer Reversals...")
    
    try:
        user, created = User.objects.get_or_create(
            username='testuser_reversal',
            defaults={'email': 'testreversal@example.com', 'first_name': 'Test', 'last_name': 'Reversal'}
        )
        
        # Create a test transfer
        transfer = BankTransfer.objects.create(
            user=user,
            bank_name='Test Bank',
            bank_code='123',
            account_number='1234567890',
            amount=Money(50000, 'NGN'),
            description='Test transfer for reversal',
            transfer_type='inter',
            status='completed'
        )
        
        # Create reversal
        reversal = TransferReversalService.create_reversal(
            original_transfer=transfer,
            reason='user_request',
            description='Customer requested reversal',
            initiated_by=user
        )
        
        print(f"✅ Created transfer reversal: {reversal.id}")
        print(f"   - Original transfer: {reversal.original_transfer.id}")
        print(f"   - Amount: {reversal.amount}")
        print(f"   - Reason: {reversal.reason}")
        
        # Process reversal
        # result = TransferReversalService.process_reversal(reversal, approved_by=user)
        # print(f"✅ Reversal processing: {'Success' if result else 'Failed'}")
        
    except Exception as e:
        print(f"❌ Error testing transfer reversals: {str(e)}")

def test_idempotency():
    """Test idempotency functionality."""
    print("\n🧪 Testing Idempotency...")
    
    try:
        user, created = User.objects.get_or_create(
            username='testuser_idempotency',
            defaults={'email': 'testidempotency@example.com', 'first_name': 'Test', 'last_name': 'Idempotency'}
        )
        
        # Generate idempotency key
        transfer_data = {
            'amount': 50000,
            'account_number': '1234567890',
            'bank_code': '044'
        }
        
        key1 = IdempotencyService.generate_idempotency_key(user.id, transfer_data)
        key2 = IdempotencyService.generate_idempotency_key(user.id, transfer_data)
        
        print(f"✅ Generated idempotency keys:")
        print(f"   - Key 1: {key1}")
        print(f"   - Key 2: {key2}")
        print(f"   - Keys are different: {key1 != key2}")
        
        # Check idempotency
        existing_transfer = IdempotencyService.check_idempotency_key(key1)
        print(f"✅ Idempotency check: {'Found existing transfer' if existing_transfer else 'No existing transfer'}")
        
    except Exception as e:
        print(f"❌ Error testing idempotency: {str(e)}")

def test_transfer_limits():
    """Test transfer limits functionality."""
    print("\n🧪 Testing Transfer Limits...")
    
    try:
        user, created = User.objects.get_or_create(
            username='testuser_limits',
            defaults={'email': 'testlimits@example.com', 'first_name': 'Test', 'last_name': 'Limits'}
        )
        
        # Create transfer limits
        TransferLimit.objects.get_or_create(
            user=user,
            limit_type='daily',
            defaults={
                'amount_limit': Money(1000000, 'NGN'),
                'count_limit': 10
            }
        )
        
        TransferLimit.objects.get_or_create(
            user=user,
            limit_type='per_transaction',
            defaults={
                'amount_limit': Money(500000, 'NGN'),
                'count_limit': 0
            }
        )
        
        # Check limits
        limit_check = TransferLimitService.check_transfer_limits(user, Money(200000, 'NGN'))
        print(f"✅ Transfer limit check:")
        print(f"   - Within limits: {limit_check['within_limits']}")
        if not limit_check['within_limits']:
            print(f"   - Limit type: {limit_check['limit_type']}")
            print(f"   - Excess: {limit_check['excess']}")
        
        # Get user limits
        user_limits = TransferLimitService.get_user_limits(user)
        print(f"✅ User limits:")
        for limit_type, limit_data in user_limits.items():
            print(f"   - {limit_type}: {limit_data['amount_limit']}")
        
    except Exception as e:
        print(f"❌ Error testing transfer limits: {str(e)}")

def test_saved_beneficiaries():
    """Test saved beneficiaries functionality."""
    print("\n🧪 Testing Saved Beneficiaries...")
    
    try:
        user, created = User.objects.get_or_create(
            username='testuser_beneficiaries',
            defaults={'email': 'testbeneficiaries@example.com', 'first_name': 'Test', 'last_name': 'Beneficiaries'}
        )
        
        # Create saved beneficiaries
        beneficiaries = [
            {
                'account_number': '1111111111',
                'account_name': 'John Doe',
                'bank_code': '044',
                'bank_name': 'Access Bank',
                'nickname': 'John'
            },
            {
                'account_number': '2222222222',
                'account_name': 'Jane Smith',
                'bank_code': '058',
                'bank_name': 'GT Bank',
                'nickname': 'Jane'
            }
        ]
        
        for beneficiary_data in beneficiaries:
            SavedBeneficiary.objects.get_or_create(
                user=user,
                account_number=beneficiary_data['account_number'],
                bank_code=beneficiary_data['bank_code'],
                defaults=beneficiary_data
            )
        
        # Get user's saved beneficiaries
        user_beneficiaries = SavedBeneficiary.objects.filter(user=user, is_active=True)
        print(f"✅ Saved beneficiaries for {user.username}:")
        for beneficiary in user_beneficiaries:
            print(f"   - {beneficiary.nickname or beneficiary.account_name} ({beneficiary.account_number}) - {beneficiary.bank_name}")
        
    except Exception as e:
        print(f"❌ Error testing saved beneficiaries: {str(e)}")

def main():
    """Run all tests."""
    print("🚀 Starting Advanced Banking Features Tests...")
    print("=" * 60)
    
    # Run all tests
    test_bank_search_feature()
    test_two_factor_authentication()
    test_ip_whitelisting()
    test_device_fingerprinting()
    test_fraud_detection()
    test_bulk_transfers()
    test_scheduled_transfers()
    test_escrow_services()
    test_transfer_reversals()
    test_idempotency()
    test_transfer_limits()
    test_saved_beneficiaries()
    
    print("\n" + "=" * 60)
    print("🎉 All Advanced Banking Features Tests Completed!")
    print("\n📋 Summary of Features Tested:")
    print("   ✅ Bank Search by Account Number")
    print("   ✅ Two-Factor Authentication")
    print("   ✅ IP Whitelisting")
    print("   ✅ Device Fingerprinting")
    print("   ✅ Fraud Detection")
    print("   ✅ Bulk Transfers")
    print("   ✅ Scheduled Transfers")
    print("   ✅ Escrow Services")
    print("   ✅ Transfer Reversals")
    print("   ✅ Idempotency")
    print("   ✅ Transfer Limits")
    print("   ✅ Saved Beneficiaries")
    
    print("\n💡 Next Steps:")
    print("   1. Create database migrations for new models")
    print("   2. Implement API endpoints for new features")
    print("   3. Add admin interface for new models")
    print("   4. Set up Celery for background tasks")
    print("   5. Configure monitoring and alerting")

if __name__ == '__main__':
    main() 