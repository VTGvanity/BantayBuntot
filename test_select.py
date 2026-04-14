import asyncio
from supabase_client import supabase_manager
import json

async def test_select():
    client = supabase_manager.get_client(use_service_role=True)
    result = client.table('animal_reports').select('id, image_url, images').limit(5).order('created_at', desc=True).execute()
    
    with open("select_out.json", "w") as f:
        json.dump(result.data, f, indent=2)

if __name__ == "__main__":
    asyncio.run(test_select())
