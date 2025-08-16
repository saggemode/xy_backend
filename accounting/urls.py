from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    JournalEntryViewSet,
    JournalEntryLineViewSet,
    ReconciliationRecordViewSet,
    ReconciliationItemViewSet
)

router = DefaultRouter()
router.register(r'accounts', AccountViewSet)
router.register(r'journal-entries', JournalEntryViewSet)
router.register(r'journal-lines', JournalEntryLineViewSet)
router.register(r'reconciliations', ReconciliationRecordViewSet)
router.register(r'reconciliation-items', ReconciliationItemViewSet)

app_name = 'accounting'

urlpatterns = [
    path('', include(router.urls)),
]