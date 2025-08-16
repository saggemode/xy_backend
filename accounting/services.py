from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from djmoney.money import Money

from .models import Account, JournalEntry, JournalEntryLine

User = get_user_model()


class AccountingService:
    """Service for accounting operations"""
    
    @staticmethod
    @transaction.atomic
    def create_journal_entry(date, reference, memo, created_by, lines_data, source_document='', is_recurring=False):
        """Create a journal entry with multiple lines
        
        Args:
            date: Date of the journal entry
            reference: Unique reference for the journal entry
            memo: Description of the journal entry
            created_by: User creating the entry
            lines_data: List of dictionaries with account_id, description, debit_amount, credit_amount
            source_document: Reference to source document
            is_recurring: Whether this is a recurring entry
            
        Returns:
            The created JournalEntry instance
        """
        # Validate that debits equal credits
        total_debits = sum(Decimal(line.get('debit_amount', 0)) for line in lines_data)
        total_credits = sum(Decimal(line.get('credit_amount', 0)) for line in lines_data)
        
        if total_debits != total_credits:
            raise ValueError(f"Debits ({total_debits}) must equal credits ({total_credits})")
        
        # Create the journal entry
        journal_entry = JournalEntry.objects.create(
            date=date,
            reference=reference,
            memo=memo,
            created_by=created_by,
            source_document=source_document,
            is_recurring=is_recurring
        )
        
        # Create the journal entry lines
        for line_data in lines_data:
            account = Account.objects.get(id=line_data['account_id'])
            description = line_data.get('description', '')
            
            debit_amount = line_data.get('debit_amount')
            credit_amount = line_data.get('credit_amount')
            
            if debit_amount and Decimal(debit_amount) > 0:
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=account,
                    description=description,
                    debit_amount=Money(debit_amount, 'NGN'),
                    credit_amount=Money(0, 'NGN')
                )
            elif credit_amount and Decimal(credit_amount) > 0:
                JournalEntryLine.objects.create(
                    journal_entry=journal_entry,
                    account=account,
                    description=description,
                    debit_amount=Money(0, 'NGN'),
                    credit_amount=Money(credit_amount, 'NGN')
                )
        
        return journal_entry
    
    @staticmethod
    @transaction.atomic
    def post_journal_entry(journal_entry_id, user):
        """Post a journal entry
        
        Args:
            journal_entry_id: ID of the journal entry to post
            user: User posting the entry
            
        Returns:
            The posted JournalEntry instance
        """
        journal_entry = JournalEntry.objects.get(id=journal_entry_id)
        journal_entry.post(user)
        return journal_entry
    
    @staticmethod
    def get_account_balance(account_id, as_of_date=None):
        """Get the balance of an account as of a specific date
        
        Args:
            account_id: ID of the account
            as_of_date: Date to calculate balance as of (defaults to current date)
            
        Returns:
            Money object representing the account balance
        """
        account = Account.objects.get(id=account_id)
        
        if as_of_date is None:
            as_of_date = timezone.now().date()
        
        # Get all posted journal entries up to the specified date
        journal_lines = JournalEntryLine.objects.filter(
            account=account,
            journal_entry__status='posted',
            journal_entry__date__lte=as_of_date
        )
        
        # Calculate the balance based on account type
        total_debits = sum(line.debit_amount.amount for line in journal_lines if line.debit_amount)
        total_credits = sum(line.credit_amount.amount for line in journal_lines if line.credit_amount)
        
        if account.account_type in ['asset', 'expense']:
            # Debit accounts: debit increases, credit decreases
            balance = total_debits - total_credits
        else:
            # Credit accounts: credit increases, debit decreases
            balance = total_credits - total_debits
        
        return Money(balance, 'NGN')
    
    @staticmethod
    @transaction.atomic
    def create_transaction_journal_entry(transaction_id, transaction_type, amount, description, 
                                         from_account_id, to_account_id, user):
        """Create a journal entry for a financial transaction
        
        Args:
            transaction_id: ID of the transaction
            transaction_type: Type of transaction (transfer, payment, etc.)
            amount: Transaction amount
            description: Transaction description
            from_account_id: Source account ID
            to_account_id: Destination account ID
            user: User creating the transaction
            
        Returns:
            The created and posted JournalEntry instance
        """
        reference = f"{transaction_type.upper()}-{transaction_id}"
        date = timezone.now().date()
        
        from_account = Account.objects.get(id=from_account_id)
        to_account = Account.objects.get(id=to_account_id)
        
        lines_data = [
            {
                'account_id': to_account.id,
                'description': f"To: {to_account.name}",
                'debit_amount': str(amount),
                'credit_amount': None
            },
            {
                'account_id': from_account.id,
                'description': f"From: {from_account.name}",
                'debit_amount': None,
                'credit_amount': str(amount)
            }
        ]
        
        journal_entry = AccountingService.create_journal_entry(
            date=date,
            reference=reference,
            memo=description,
            created_by=user,
            lines_data=lines_data,
            source_document=f"Transaction {transaction_id}"
        )
        
        # Automatically post the entry
        journal_entry.post(user)
        
        return journal_entry