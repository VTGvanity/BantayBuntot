import asyncio
import json
from supabase_client import supabase_manager

async def test_insert():
    report_data = {
        'animal_type': 'dog',
        'animal_condition': 'healthy',
        'description': 'Test report to see if image_url is ignored',
        'address': 'Test address',
        'image_url': 'https://example.com/image.jpg',
        'status': 'pending',
        'priority': 'medium'
    }
    
    client = supabase_manager.get_client(use_service_role=True)
    users = client.table('users').select('id').limit(1).execute()
    if users.data:
        report_data['user_id'] = users.data[0]['id']
        
    try:
        result = client.table('animal_reports').insert(report_data).execute()
        with open("out.json", "w") as f:
            json.dump(result.data[0], f)
    except Exception as e:
        with open("out.json", "w") as f:
            f.write(str(e))

if __name__ == "__main__":
    asyncio.run(test_insert())
