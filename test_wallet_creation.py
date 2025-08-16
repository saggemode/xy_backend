#!/usr/bin/env python
"""
Test script to verify wallet creation when KYC is approved with BVN/NIN
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile, KYCProfile
from bank.models import Wallet
from accounts.views import validate_bvn, validate_nin
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate
import json

def test_wallet_creation():
    """Test that wallet is created when KYC is approved with BVN/NIN"""
    
    # Create a test user
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    
    # Create user profile
    profile = UserProfile.objects.create(
        user=user,
        phone='+2348012345678'
    )
    
    print(f"Created test user: {user.username}")
    print(f"User profile phone: {profile.phone}")
    
    # Check if wallet exists before KYC
    wallet_before = Wallet.objects.filter(user=user).exists()
    print(f"Wallet exists before KYC: {wallet_before}")
    
    # Test BVN validation
    factory = APIRequestFactory()
    
    # Test with a valid BVN from dummy data
    bvn_request = factory.post('/accounts/kyc/validate-bvn/', {
        'bvn': '1234567890'
    }, content_type='application/json')
    force_authenticate(bvn_request, user=user)
    
    try:
        from accounts.views import validate_bvn
        response = validate_bvn(bvn_request)
        print(f"BVN validation response status: {response.status_code}")
        if response.status_code == 200:
            print("BVN validation successful")
        else:
            print(f"BVN validation failed: {response.data}")
    except Exception as e:
        print(f"Error during BVN validation: {e}")
    
    # Check if KYC profile was created and approved
    try:
        kyc_profile = KYCProfile.objects.get(user=user)
        print(f"KYC Profile created: {kyc_profile}")
        print(f"KYC Profile approved: {kyc_profile.is_approved}")
        print(f"KYC Profile BVN: {kyc_profile.bvn}")
    except KYCProfile.DoesNotExist:
        print("KYC Profile was not created")
        return
    
    # Check if wallet was created after KYC approval
    wallet_after = Wallet.objects.filter(user=user).exists()
    print(f"Wallet exists after KYC: {wallet_after}")
    
    if wallet_after:
        wallet = Wallet.objects.get(user=user)
        print(f"Wallet created successfully!")
        print(f"Account number: {wallet.account_number}")
        print(f"Alternative account number: {wallet.alternative_account_number}")
        print(f"Balance: {wallet.balance}")
    else:
        print("Wallet was not created!")
    
    # Clean up
    user.delete()
    print("Test completed and cleaned up")

if __name__ == '__main__':
    test_wallet_creation() 