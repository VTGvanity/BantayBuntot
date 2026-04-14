import asyncio
from supabase_client import supabase_manager
from supabase_config import USERS_TABLE

async def find_rescuer():
    client = supabase_manager.get_client(use_service_role=True)
    response = client.table(USERS_TABLE).select('email, user_type').eq('user_type', 'rescuer').limit(5).execute()
    if response.data:
        print("Found rescuers:")
        for user in response.data:
            print(f"- {user['email']}")
    else:
        print("No rescuers found in public.users table.")

if __name__ == "__main__":
    asyncio.run(find_rescuer())
