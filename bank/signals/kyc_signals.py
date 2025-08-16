print('Loaded kyc_signals')
from django.db.models.signals import post_save
from django.dispatch import receiver
from bank.models import Wallet, generate_alternative_account_number, StaffProfile, StaffActivity
from accounts.models import KYCProfile
from django.utils import timezone
from djmoney.money import Money
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=KYCProfile)
def create_wallet_on_kyc_approval(sender, instance, created, **kwargs):
    """Create wallet automatically when KYC is approved."""
    print(f"KYC signal triggered - is_approved: {instance.is_approved}, created: {created}")
    logger.info(f"KYC signal triggered for user {instance.user.username} - is_approved: {instance.is_approved}, created: {created}")
    
    # Auto-approve KYC if BVN data is present
    if not instance.is_approved and instance.bvn:
        print("BVN data present, auto-approving KYC")
        logger.info(f"Auto-approving KYC for user {instance.user.username} due to BVN presence")
        instance.is_approved = True
        instance.save()
    
    if instance.is_approved:  # Create wallet when KYC is approved (new or updated)
        print("KYC is approved, checking for existing wallet")
        logger.info(f"KYC approved for user {instance.user.username}, checking for existing wallet")
        
        # Check if wallet already exists
        if not Wallet.objects.filter(user=instance.user).exists():
            print("No existing wallet found, creating new wallet")
            logger.info(f"Creating new wallet for user {instance.user.username}")
            
            # Use phone number as account number
            try:
                phone_number = instance.user.profile.phone
                if phone_number:
                    # Remove country code and get last 10 digits
                    phone_str = str(phone_number)
                    if phone_str.startswith('+234'):
                        phone_str = phone_str[4:]  # Remove +234
                    elif phone_str.startswith('234'):
                        phone_str = phone_str[3:]   # Remove 234
                    # Ensure it's 10 digits
                    if len(phone_str) >= 10:
                        account_number = phone_str[-10:]  # Take last 10 digits
                    else:
                        # Pad with zeros if less than 10 digits
                        account_number = phone_str.zfill(10)
                else:
                    # Generate a random account number if no phone number
                    import random
                    import string
                    account_number = ''.join(random.choices(string.digits, k=10))
                    logger.warning(f"No phone number found for user {instance.user.username}, generated random account number")
                
                # Create wallet with default balance
                wallet = Wallet.objects.create(
                    user=instance.user,
                    account_number=account_number,
                    alternative_account_number=generate_alternative_account_number(),
                    balance=Money(0, 'NGN')  # Set default balance to 0 NGN
                )
                print(f"Wallet created successfully for user {instance.user.username} with account number {account_number}")
                logger.info(f"Wallet created successfully for user {instance.user.username} with account number {account_number}")
                
            except Exception as e:
                print(f"Error creating wallet for user {instance.user.username}: {str(e)}")
                logger.error(f"Error creating wallet for user {instance.user.username}: {str(e)}")
        else:
            print(f"Wallet already exists for user {instance.user.username}")
            logger.info(f"Wallet already exists for user {instance.user.username}")

@receiver(post_save, sender=KYCProfile)
def handle_kyc_approval(sender, instance, created, **kwargs):
    """Handle KYC approval and log staff activity."""
    if not created and instance.is_approved:
        try:
            staff_member = StaffProfile.objects.filter(
                role__can_approve_kyc=True,
                is_active=True
            ).first()
            if staff_member:
                StaffActivity.objects.create(
                    staff=staff_member,
                    activity_type='kyc_approved',
                    description=f'KYC approved for user {instance.user.username}',
                    related_object=instance
                )
        except StaffProfile.DoesNotExist:
            pass 