from rest_framework import serializers
from .models import Account, JournalEntry, JournalEntryLine, ReconciliationRecord, ReconciliationItem


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class JournalEntryLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntryLine
        fields = '__all__'
        read_only_fields = ('id', 'created_at')


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalEntryLineSerializer(many=True, read_only=True)
    
    class Meta:
        model = JournalEntry
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'posted_at', 'posted_by')


class ReconciliationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationItem
        fields = '__all__'
        read_only_fields = ('id', 'reconciled_at')


class ReconciliationRecordSerializer(serializers.ModelSerializer):
    items = ReconciliationItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = ReconciliationRecord
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'completed_at', 'reconciled_by')