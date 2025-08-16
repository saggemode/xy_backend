#!/usr/bin/env python
"""
Quick fix script to resolve UUID issues and test the system.
Run this with: python manage.py shell < quick_fix.py
"""

import os
import django
import sys

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from bank.models import BankTransfer, Transaction, Wallet

def quick_fix():
    """Quick fix for UUID issues."""
    
    print("🚀 Quick Fix for UUID Issues...")
    
    # Check if we can access the models
    models_to_check = [
        (BankTransfer, "BankTransfer"),
        (Transaction, "Transaction"), 
        (Wallet, "Wallet")
    ]
    
    for model_class, model_name in models_to_check:
        print(f"\n🔍 Checking {model_name}...")
        
        try:
            # Try to count records
            count = model_class.objects.count()
            print(f"   ✅ {model_name}: {count} records")
            
            # Try to get first record
            if count > 0:
                first_record = model_class.objects.first()
                print(f"   ✅ First record ID: {first_record.id}")
                
        except Exception as e:
            print(f"   ❌ Error with {model_name}: {str(e)}")
            
            if "badly formed hexadecimal UUID string" in str(e):
                print(f"   🔧 Attempting to fix {model_name}...")
                
                try:
                    with connection.cursor() as cursor:
                        table_name = model_class._meta.db_table
                        
                        # Check table structure
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        print(f"   📋 Table columns: {[col[1] for col in columns]}")
                        
                        # Try to get problematic records
                        cursor.execute(f"SELECT id FROM {table_name} LIMIT 5")
                        records = cursor.fetchall()
                        
                        if records:
                            print(f"   📊 Sample IDs: {[str(r[0]) for r in records]}")
                            
                            # Check for invalid UUIDs
                            for record in records:
                                try:
                                    import uuid
                                    uuid.UUID(str(record[0]))
                                    print(f"   ✅ Valid UUID: {record[0]}")
                                except:
                                    print(f"   ❌ Invalid UUID: {record[0]}")
                                    print(f"   💡 This record needs to be fixed or deleted")
                        else:
                            print(f"   ✅ No records found - no UUID issues")
                            
                except Exception as fix_error:
                    print(f"   ❌ Could not analyze {model_name}: {str(fix_error)}")
    
    print("\n🎉 Quick fix check completed!")
    print("\n💡 If you found invalid UUIDs, you can:")
    print("   1. Delete the problematic records")
    print("   2. Or restore from a backup")
    print("   3. Or recreate the data")

if __name__ == '__main__':
    quick_fix() 