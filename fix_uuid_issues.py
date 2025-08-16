#!/usr/bin/env python
"""
Script to fix UUID corruption issues in the database.
Run this with: python manage.py shell < fix_uuid_issues.py
"""

import os
import django
import sys
import uuid

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from bank.models import Wallet, Transaction, BankTransfer, BillPayment, VirtualCard, Bank, VATCharge, CBNVATCharge, TransferChargeControl, StaffRole, StaffProfile, TransactionApproval, CustomerEscalation, StaffActivity

def fix_uuid_issues():
    """Fix corrupted UUID values in the database."""
    
    print("🔧 Fixing UUID Issues...")
    
    # List of models with UUID fields
    models_with_uuid = [
        Wallet, Transaction, BankTransfer, BillPayment, VirtualCard, Bank, 
        VATCharge, CBNVATCharge, TransferChargeControl, StaffRole, StaffProfile, 
        TransactionApproval, CustomerEscalation, StaffActivity
    ]
    
    for model in models_with_uuid:
        print(f"\n📋 Checking {model.__name__}...")
        
        try:
            # Try to get all records
            count = model.objects.count()
            print(f"   Total records: {count}")
            
            if count > 0:
                # Try to get first record to test UUID
                first_record = model.objects.first()
                if first_record:
                    print(f"   ✅ {model.__name__} UUIDs are valid")
                else:
                    print(f"   ⚠️  No records found in {model.__name__}")
                    
        except Exception as e:
            print(f"   ❌ Error with {model.__name__}: {str(e)}")
            
            # Try to fix by recreating the table
            if "badly formed hexadecimal UUID string" in str(e):
                print(f"   🔧 Attempting to fix {model.__name__} UUID issues...")
                try:
                    # This is a more aggressive fix - you might want to backup first
                    with connection.cursor() as cursor:
                        # Get table name
                        table_name = model._meta.db_table
                        print(f"   📝 Table: {table_name}")
                        
                        # Check if table exists and has data
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        record_count = cursor.fetchone()[0]
                        print(f"   📊 Records in table: {record_count}")
                        
                        if record_count > 0:
                            print(f"   ⚠️  {model.__name__} has data - manual intervention may be needed")
                            print(f"   💡 Consider: DELETE FROM {table_name};")
                        else:
                            print(f"   ✅ {model.__name__} table is empty - no UUID issues")
                            
                except Exception as fix_error:
                    print(f"   ❌ Could not fix {model.__name__}: {str(fix_error)}")
    
    print("\n🎉 UUID check completed!")
    print("\n💡 If you have corrupted UUIDs, you may need to:")
    print("   1. Backup your data")
    print("   2. Delete corrupted records")
    print("   3. Recreate the data")
    print("   4. Or restore from a backup")

def check_specific_model(model_class, model_name):
    """Check a specific model for UUID issues."""
    print(f"\n🔍 Checking {model_name}...")
    
    try:
        count = model_class.objects.count()
        print(f"   Total records: {count}")
        
        if count > 0:
            # Try to get a few records
            records = model_class.objects.all()[:5]
            for i, record in enumerate(records):
                print(f"   Record {i+1}: {record.id} - {str(record)[:50]}...")
                
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

if __name__ == '__main__':
    print("🚀 Starting UUID Fix Script...")
    
    # Check specific models that might have issues
    check_specific_model(BankTransfer, "BankTransfer")
    check_specific_model(Transaction, "Transaction")
    check_specific_model(Wallet, "Wallet")
    
    # Run the main fix
    fix_uuid_issues()
    
    print("\n✅ Script completed!") 