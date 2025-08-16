from django.contrib import admin
from .models import Account, JournalEntry, JournalEntryLine, ReconciliationRecord, ReconciliationItem


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 2


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('name', 'code', 'description')
    ordering = ('code',)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'date', 'status', 'created_by', 'posted_at')
    list_filter = ('status', 'date', 'is_recurring')
    search_fields = ('reference', 'memo', 'source_document')
    inlines = [JournalEntryLineInline]
    readonly_fields = ('posted_at', 'posted_by')
    date_hierarchy = 'date'


@admin.register(JournalEntryLine)
class JournalEntryLineAdmin(admin.ModelAdmin):
    list_display = ('journal_entry', 'account', 'debit_amount', 'credit_amount')
    list_filter = ('account',)
    search_fields = ('description', 'account__name')


class ReconciliationItemInline(admin.TabularInline):
    model = ReconciliationItem
    extra = 1
    readonly_fields = ('reconciled_at',)


@admin.register(ReconciliationRecord)
class ReconciliationRecordAdmin(admin.ModelAdmin):
    list_display = ('account', 'start_date', 'end_date', 'status', 'reconciled_by')
    list_filter = ('status', 'account')
    search_fields = ('account__name', 'notes')
    readonly_fields = ('completed_at', 'reconciled_by')
    date_hierarchy = 'end_date'
    inlines = [ReconciliationItemInline]


@admin.register(ReconciliationItem)
class ReconciliationItemAdmin(admin.ModelAdmin):
    list_display = ('reconciliation', 'journal_line', 'is_reconciled', 'reconciled_at')
    list_filter = ('is_reconciled', 'reconciliation')
    search_fields = ('notes', 'journal_line__description')
    readonly_fields = ('reconciled_at',)