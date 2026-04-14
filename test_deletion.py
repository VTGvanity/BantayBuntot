
import os
import asyncio
import sys

# Add the project root to sys.path to allow importing from the project
sys.path.append(os.getcwd())

# Mock Django setup if needed, but we can just use the supabase_manager directly for core verification
# and then use a mock-request script for the API view verification.

from supabase_client import supabase_manager
from supabase_config import ANIMAL_REPORTS_TABLE

async def test_admin_deletion():
    print("--- TESTING ADMIN DELETION LOGIC ---")
    
    # 1. Create a dummy report
    test_report = {
        'user_id': '5f538108-da1f-4450-af53-4ce9543382e0',
        'animal_type': 'test_animal',
        'animal_condition': 'test_condition',
        'description': 'This is a test report for deletion verification.',
        'latitude': 0,
        'longitude': 0,
        'address': 'Test Street',
        'status': 'pending',
        'reporter_name': 'Test Reporter'
    }
    
    print("Creating test report...")
    created_report = await supabase_manager.create_animal_report(test_report)
    if not created_report:
        print("FAILED: Could not create test report.")
        return
    
    report_id = created_report['id']
    print(f"Test report created with ID: {report_id}")
    
    # 2. Verify it exists
    client = supabase_manager.get_client(use_service_role=True)
    check = client.table(ANIMAL_REPORTS_TABLE).select('id').eq('id', report_id).execute()
    if not check.data:
        print("FAILED: Report not found after creation.")
        return
    print("Report existence verified.")
    
    # 3. Use the deletion logic (Admin path)
    print("Simulating admin deletion...")
    # In a real API call, it would be: result = asyncio.run(supabase_manager.delete_animal_report(report_id))
    # We'll call the manager's method directly as that's what the Admin path in api_views does.
    delete_result = await supabase_manager.delete_animal_report(report_id)
    
    if delete_result is not None:
        print("Deletion logic returned success.")
    else:
        print("FAILED: Deletion logic returned None.")
        return
        
    # 4. Final Verification
    check_deleted = client.table(ANIMAL_REPORTS_TABLE).select('id').eq('id', report_id).execute()
    if not check_deleted.data:
        print("SUCCESS: Report is gone from Supabase.")
    else:
        print("FAILED: Report still exists in Supabase.")

if __name__ == "__main__":
    asyncio.run(test_admin_deletion())
