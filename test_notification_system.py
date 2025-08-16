#!/usr/bin/env python
"""
Simple test script to verify the notification system is working.
Run this with: python manage.py shell < test_notification_system.py
"""

import os
import django
import sys

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from bank.models import Wallet, Transaction
from notification.models import Notification, NotificationType, NotificationLevel, NotificationStatus
from djmoney.money import Money
import uuid

def test_notification_creation():
    """Test creating a simple notification without UUID issues."""
    
    print("🧪 Testing Notification Creation...")
    
    # Get or create a test user
    try:
        user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        print("Creating test user...")
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    print(f"✅ Using user: {user.username}")
    
    # Test creating a simple notification
    try:
        notification = Notification.objects.create(
            recipient=user,
            title="Test Notification",
            message="This is a test notification to verify the system is working.",
            notification_type=NotificationType.SYSTEM_ALERT,
            level=NotificationLevel.INFO,
            status=NotificationStatus.SENT,
            source='test'
        )
        print(f"✅ Notification created successfully: {notification.id}")
        print(f"   Title: {notification.title}")
        print(f"   Message: {notification.message}")
        print(f"   Type: {notification.notification_type}")
        
        # Clean up
        notification.delete()
        print("✅ Test notification cleaned up")
        
    except Exception as e:
        print(f"❌ Error creating notification: {str(e)}")
        return False
    
    return True

def test_transaction_notification():
    """Test creating a transaction notification."""
    
    print("\n🧪 Testing Transaction Notification...")
    
    # Get or create test user and wallet
    try:
        user = User.objects.get(username='testuser')
        wallet = Wallet.objects.get(user=user)
    except (User.DoesNotExist, Wallet.DoesNotExist):
        print("Creating test user and wallet...")
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        wallet = Wallet.objects.create(
            user=user,
            account_number='1234567890',
            balance=Money(1000, 'NGN')
        )
    
    # Create a test transaction
    try:
        transaction = Transaction.objects.create(
            wallet=wallet,
            reference=str(uuid.uuid4()),
            amount=Money(100, 'NGN'),
            type='debit',
            channel='test',
            description='Test transaction for notification',
            status='success',
            balance_after=Money(900, 'NGN')
        )
        print(f"✅ Test transaction created: {transaction.id}")
        
        # Check if notification was created by the signal
        notifications = Notification.objects.filter(recipient=user)
        print(f"✅ Notifications found: {notifications.count()}")
        for notif in notifications:
            print(f"   - {notif.title}: {notif.message}")
        
        # Clean up
        transaction.delete()
        notifications.delete()
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"❌ Error in transaction test: {str(e)}")
        return False
    
    return True

if __name__ == '__main__':
    print("🚀 Starting Notification System Tests...")
    
    # Test 1: Basic notification creation
    if test_notification_creation():
        print("✅ Basic notification test passed")
    else:
        print("❌ Basic notification test failed")
    
    # Test 2: Transaction notification
    if test_transaction_notification():
        print("✅ Transaction notification test passed")
    else:
        print("❌ Transaction notification test failed")
    
    print("\n🎉 Notification system tests completed!")
    print("\nTo clean up test data, run:")
    print("   User.objects.filter(username='testuser').delete()") 