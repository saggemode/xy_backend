from django.db import models
import uuid
from django.contrib.auth import get_user_model
from djmoney.models.fields import MoneyField
from django.utils import timezone

User = get_user_model()

class Account(models.Model):
    """Ledger account for double-entry accounting"""
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        ordering = ['code']

class JournalEntry(models.Model):
    """Journal entry for recording transactions"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(default=timezone.now)
    reference = models.CharField(max_length=100, unique=True)
    memo = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_journal_entries')
    posted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='posted_journal_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    source_document = models.CharField(max_length=100, blank=True, help_text="Reference to source document or transaction")
    is_recurring = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Journal Entry {self.reference}"
    
    def post(self, user):
        """Post the journal entry"""
        if self.status == 'draft':
            # Verify that debits equal credits
            debit_sum = sum(line.debit_amount.amount for line in self.lines.all() if line.debit_amount)
            credit_sum = sum(line.credit_amount.amount for line in self.lines.all() if line.credit_amount)
            
            if debit_sum != credit_sum:
                raise ValueError("Debits must equal credits")
                
            self.status = 'posted'
            self.posted_by = user
            self.posted_at = timezone.now()
            self.save()
    
    class Meta:
        verbose_name_plural = "Journal Entries"
        ordering = ['-date', '-created_at']

class JournalEntryLine(models.Model):
    """Line item for journal entries"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_lines')
    description = models.CharField(max_length=255, blank=True)
    debit_amount = MoneyField(max_digits=15, decimal_places=2, default_currency='NGN', null=True, blank=True)
    credit_amount = MoneyField(max_digits=15, decimal_places=2, default_currency='NGN', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.debit_amount and self.debit_amount.amount > 0:
            return f"{self.account.name} - Debit {self.debit_amount}"
        return f"{self.account.name} - Credit {self.credit_amount}"
    
    def clean(self):
        """Ensure either debit or credit is set, but not both"""
        if (self.debit_amount and self.debit_amount.amount > 0) and (self.credit_amount and self.credit_amount.amount > 0):
            raise ValueError("A line item cannot have both debit and credit amounts")
        if not (self.debit_amount and self.debit_amount.amount > 0) and not (self.credit_amount and self.credit_amount.amount > 0):
            raise ValueError("A line item must have either a debit or credit amount")
    
    class Meta:
        ordering = ['journal_entry', 'id']

class ReconciliationRecord(models.Model):
    """Record for account reconciliation"""
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='reconciliations')
    start_date = models.DateField()
    end_date = models.DateField()
    statement_balance = MoneyField(max_digits=15, decimal_places=2, default_currency='NGN')
    reconciled_balance = MoneyField(max_digits=15, decimal_places=2, default_currency='NGN', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    notes = models.TextField(blank=True)
    reconciled_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Reconciliation for {self.account.name} ({self.start_date} to {self.end_date})"
    
    def complete_reconciliation(self, user):
        """Mark reconciliation as complete"""
        self.status = 'completed'
        self.reconciled_by = user
        self.completed_at = timezone.now()
        self.save()
    
    class Meta:
        ordering = ['-end_date', 'account']

class ReconciliationItem(models.Model):
    """Individual item in a reconciliation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reconciliation = models.ForeignKey(ReconciliationRecord, on_delete=models.CASCADE, related_name='items')
    journal_line = models.ForeignKey(JournalEntryLine, on_delete=models.PROTECT)
    is_reconciled = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Reconciliation Item for {self.journal_line}"
    
    def reconcile(self):
        """Mark item as reconciled"""
        self.is_reconciled = True
        self.reconciled_at = timezone.now()
        self.save()
    
    class Meta:
        ordering = ['reconciliation', 'journal_line']