from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import Account, JournalEntry, JournalEntryLine, ReconciliationRecord, ReconciliationItem
from .serializers import (
    AccountSerializer, 
    JournalEntrySerializer, 
    JournalEntryLineSerializer,
    ReconciliationRecordSerializer,
    ReconciliationItemSerializer
)


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['account_type', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['code', 'name', 'account_type']


class JournalEntryViewSet(viewsets.ModelViewSet):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'date', 'is_recurring']
    search_fields = ['reference', 'memo', 'source_document']
    ordering_fields = ['date', 'reference', 'created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def post_entry(self, request, pk=None):
        journal_entry = self.get_object()
        
        try:
            journal_entry.post(request.user)
            return Response({'status': 'journal entry posted'}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JournalEntryLineViewSet(viewsets.ModelViewSet):
    queryset = JournalEntryLine.objects.all()
    serializer_class = JournalEntryLineSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['journal_entry', 'account']
    search_fields = ['description']
    
    def perform_create(self, serializer):
        # Validate that the entry is still in draft status
        journal_entry = serializer.validated_data.get('journal_entry')
        if journal_entry.status != 'draft':
            return Response(
                {'error': 'Cannot modify a posted or cancelled journal entry'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()


class ReconciliationRecordViewSet(viewsets.ModelViewSet):
    queryset = ReconciliationRecord.objects.all()
    serializer_class = ReconciliationRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'account']
    search_fields = ['notes']
    ordering_fields = ['start_date', 'end_date', 'account']
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        reconciliation = self.get_object()
        
        if reconciliation.status != 'in_progress':
            return Response(
                {'error': 'Only in-progress reconciliations can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        reconciliation.complete_reconciliation(request.user)
        return Response({'status': 'reconciliation completed'}, status=status.HTTP_200_OK)


class ReconciliationItemViewSet(viewsets.ModelViewSet):
    queryset = ReconciliationItem.objects.all()
    serializer_class = ReconciliationItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['reconciliation', 'is_reconciled']
    
    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        item = self.get_object()
        
        if item.reconciliation.status != 'in_progress':
            return Response(
                {'error': 'Cannot modify items in a completed or cancelled reconciliation'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        item.reconcile()
        return Response({'status': 'item reconciled'}, status=status.HTTP_200_OK)