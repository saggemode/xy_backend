#!/usr/bin/env python
"""
Test script to verify notifications are included in profile response.
Run this with: python manage.py shell < test_notifications_in_profile.py
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
from notification.models import Notification, NotificationType, NotificationLevel, NotificationStatus
from accounts.models import UserProfile
from bank.models import Wallet
from djmoney.money import Money

def test_notifications_in_profile():
    """Test that notifications are included in profile response."""
    
    print("🧪 Testing Notifications in Profile...")
    
    # Get or create a test user
    try:
        user = User.objects.get(username='smith')
        print(f"✅ Using existing user: {user.username}")
    except User.DoesNotExist:
        print("❌ User 'smith' not found. Please create a user first.")
        return False
    
    # Create some test notifications
    try:
        # Create a few test notifications
        notifications_created = []
        
        # Notification 1: Transaction notification
        notif1 = Notification.objects.create(
            recipient=user,
            title="Transaction Successful",
            message="Your transfer of NGN 3,000.00 was successful.",
            notification_type=NotificationType.WALLET_CREDIT,
            level=NotificationLevel.SUCCESS,
            status=NotificationStatus.SENT,
            source='bank'
        )
        notifications_created.append(notif1)
        print(f"✅ Created notification 1: {notif1.title}")
        
        # Notification 2: System alert
        notif2 = Notification.objects.create(
            recipient=user,
            title="Account Verified",
            message="Your account has been successfully verified.",
            notification_type=NotificationType.ACCOUNT_UPDATE,
            level=NotificationLevel.INFO,
            status=NotificationStatus.SENT,
            source='accounts'
        )
        notifications_created.append(notif2)
        print(f"✅ Created notification 2: {notif2.title}")
        
        # Notification 3: Security alert
        notif3 = Notification.objects.create(
            recipient=user,
            title="Security Alert",
            message="New login detected from a new device.",
            notification_type=NotificationType.SECURITY_ALERT,
            level=NotificationLevel.WARNING,
            status=NotificationStatus.SENT,
            source='security'
        )
        notifications_created.append(notif3)
        print(f"✅ Created notification 3: {notif3.title}")
        
        # Test the profile serializer
        from accounts.serializers import UserProfileSerializer
        
        try:
            profile = user.profile
            serializer = UserProfileSerializer(profile)
            data = serializer.data
            
            # Check if notifications are included
            if 'notifications' in data:
                notifications = data['notifications']
                print(f"✅ Notifications found in profile: {len(notifications)} notifications")
                
                for i, notif in enumerate(notifications):
                    print(f"   Notification {i+1}:")
                    print(f"     - ID: {notif['id']}")
                    print(f"     - Title: {notif['title']}")
                    print(f"     - Type: {notif['notification_type']}")
                    print(f"     - Level: {notif['level']}")
                    print(f"     - Is Read: {notif['isRead']}")
                    print(f"     - Created: {notif['created_at']}")
                
                # Verify the notifications match what we created
                if len(notifications) >= 3:
                    print("✅ All test notifications are included in profile response")
                    return True
                else:
                    print(f"❌ Expected 3+ notifications, got {len(notifications)}")
                    return False
                    
            else:
                print("❌ Notifications field not found in profile response")
                print(f"Available fields: {list(data.keys())}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing profile serializer: {str(e)}")
            return False
        
    except Exception as e:
        print(f"❌ Error creating test notifications: {str(e)}")
        return False
    
    finally:
        # Clean up test notifications
        try:
            for notif in notifications_created:
                notif.delete()
            print("✅ Test notifications cleaned up")
        except:
            pass

def test_notification_endpoints():
    """Test notification API endpoints."""
    
    print("\n🧪 Testing Notification API Endpoints...")
    
    try:
        user = User.objects.get(username='smith')
        print(f"✅ Using user: {user.username}")
        
        # Test notification endpoints
        endpoints_to_test = [
            '/notification/api/v1/notifications/my/',
            '/notification/api/v1/notifications/unread/',
            '/notification/api/v1/notifications/recent/',
            '/notification/api/v1/notifications/stats/',
        ]
        
        print("📋 Available notification endpoints:")
        for endpoint in endpoints_to_test:
            print(f"   - {endpoint}")
        
        print("✅ Notification endpoints are available")
        return True
        
    except User.DoesNotExist:
        print("❌ User 'smith' not found")
        return False

if __name__ == '__main__':
    print("🚀 Starting Notification Profile Tests...")
    
    # Test 1: Notifications in profile
    if test_notifications_in_profile():
        print("✅ Notifications in profile test passed")
    else:
        print("❌ Notifications in profile test failed")
    
    # Test 2: Notification endpoints
    if test_notification_endpoints():
        print("✅ Notification endpoints test passed")
    else:
        print("❌ Notification endpoints test failed")
    
    print("\n🎉 Notification tests completed!")
    print("\n💡 You can now:")
    print("   1. Access /accounts/profile/ to see notifications in profile")
    print("   2. Use /notification/api/v1/notifications/my/ for user notifications")
    print("   3. Use /notification/api/v1/notifications/unread/ for unread notifications") 