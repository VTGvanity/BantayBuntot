#!/usr/bin/env python3
"""
Script to delete all pinned locations from Supabase database.
Run this to clear all pinned locations for testing.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BantayBuntot.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from supabase_client import supabase_manager
from supabase_config import PINNED_LOCATIONS_TABLE

def delete_all_pinned_locations():
    """Delete all pinned locations from the database"""
    print("Deleting all pinned locations from Supabase...")
    
    try:
        # Use service role client to bypass RLS
        client = supabase_manager.get_client(use_service_role=True)
        
        # First, get all records to check if table has any rows
        result = client.table(PINNED_LOCATIONS_TABLE).select('id').execute()
        
        if result.data:
            print(f"Found {len(result.data)} pinned locations to delete")
            # Delete records one by one since UUID comparison is tricky
            for record in result.data:
                client.table(PINNED_LOCATIONS_TABLE).delete().eq('id', record['id']).execute()
            print(f"✓ Successfully deleted {len(result.data)} pinned locations")
        else:
            print("✓ No pinned locations to delete (table is empty)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error deleting pinned locations: {e}")
        return False

if __name__ == '__main__':
    success = delete_all_pinned_locations()
    sys.exit(0 if success else 1)
