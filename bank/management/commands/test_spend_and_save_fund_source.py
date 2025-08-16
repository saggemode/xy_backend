from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from djmoney.money import Money
from bank.models import Wallet, XySaveAccount, SpendAndSaveAccount
from bank.spend_and_save_services import SpendAndSaveService

User = get_user_model()


class Command(BaseCommand):
    help = 'Test Spend and Save fund source functionality'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='Username to test with')
        parser.add_argument('--fund-source', type=str, choices=['wallet', 'xysave', 'both'], default='wallet', help='Fund source to test')
        parser.add_argument('--amount', type=float, default=1000.0, help='Initial amount to transfer (for single source)')
        parser.add_argument('--wallet-amount', type=float, default=0.0, help='Amount to transfer from wallet (for both source)')
        parser.add_argument('--xysave-amount', type=float, default=0.0, help='Amount to transfer from XySave (for both source)')

    def handle(self, *args, **options):
        username = options['username']
        fund_source = options['fund_source']
        amount = options['amount']
        wallet_amount = options['wallet_amount']
        xysave_amount = options['xysave_amount']

        try:
            # Get or create user
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@test.com'}
            )
            
            if created:
                self.stdout.write(f"Created user: {username}")
            
            # Check if user has wallet and XySave account
            wallet, wallet_created = Wallet.objects.get_or_create(
                user=user,
                defaults={
                    'account_number': f'7{username[-8:]}',
                    'alternative_account_number': f'7{username[-8:]}1',
                    'balance': Money(5000, 'NGN')
                }
            )
            
            if wallet_created:
                self.stdout.write(f"Created wallet with balance: {wallet.balance}")
            else:
                # Add some balance if wallet exists
                wallet.balance += Money(2000, 'NGN')
                wallet.save()
                self.stdout.write(f"Updated wallet balance: {wallet.balance}")
            
            # Create XySave account if needed
            xysave_account, xysave_created = XySaveAccount.objects.get_or_create(
                user=user,
                defaults={
                    'account_number': f'9{username[-8:]}',
                    'balance': Money(3000, 'NGN')
                }
            )
            
            if xysave_created:
                self.stdout.write(f"Created XySave account with balance: {xysave_account.balance}")
            else:
                # Add some balance if account exists
                xysave_account.balance += Money(1500, 'NGN')
                xysave_account.save()
                self.stdout.write(f"Updated XySave balance: {xysave_account.balance}")
            
            # Check if Spend and Save account already exists
            existing_account = SpendAndSaveAccount.objects.filter(user=user).first()
            if existing_account:
                self.stdout.write(f"Spend and Save account already exists: {existing_account.account_number}")
                self.stdout.write(f"Current balance: {existing_account.balance}")
                self.stdout.write(f"Is active: {existing_account.is_active}")
                
                if existing_account.is_active:
                    self.stdout.write("Account is already active. Deactivating first...")
                    SpendAndSaveService.deactivate_spend_and_save(user)
            
            # Test activation with fund source
            self.stdout.write(f"\nTesting activation with fund source: {fund_source}")
            
            if fund_source == 'both':
                self.stdout.write(f"Wallet amount: {wallet_amount}")
                self.stdout.write(f"XySave amount: {xysave_amount}")
                
                account = SpendAndSaveService.activate_spend_and_save(
                    user=user,
                    savings_percentage=5.0,
                    fund_source=fund_source,
                    wallet_amount=wallet_amount if wallet_amount > 0 else None,
                    xysave_amount=xysave_amount if xysave_amount > 0 else None
                )
            else:
                self.stdout.write(f"Initial amount: {amount}")
                
                account = SpendAndSaveService.activate_spend_and_save(
                    user=user,
                    savings_percentage=5.0,
                    fund_source=fund_source,
                    initial_amount=amount
                )
            
            self.stdout.write(f"✅ Successfully activated Spend and Save account!")
            self.stdout.write(f"Account number: {account.account_number}")
            self.stdout.write(f"Balance: {account.balance}")
            self.stdout.write(f"Savings percentage: {account.savings_percentage}%")
            self.stdout.write(f"Is active: {account.is_active}")
            
            # Check updated balances
            wallet.refresh_from_db()
            xysave_account.refresh_from_db()
            
            self.stdout.write(f"\nUpdated balances:")
            self.stdout.write(f"Wallet: {wallet.balance}")
            self.stdout.write(f"XySave: {xysave_account.balance}")
            self.stdout.write(f"Spend and Save: {account.balance}")
            
            # Test account summary
            summary = SpendAndSaveService.get_account_summary(user)
            if summary:
                self.stdout.write(f"\nAccount summary retrieved successfully")
                self.stdout.write(f"Total saved from spending: {summary['account']['total_saved_from_spending']}")
                self.stdout.write(f"Total interest earned: {summary['account']['total_interest_earned']}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc())) 