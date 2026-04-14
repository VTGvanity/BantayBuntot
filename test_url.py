import asyncio
from supabase_client import supabase_manager

async def test_url():
    client = supabase_manager.get_client(use_service_role=True)
    file_name = "wowie/test_script.png"
    public_url = client.storage.from_("animal-images").get_public_url(file_name)
    print("Type of public_url:", type(public_url))
    print("Value of public_url:", public_url)

if __name__ == "__main__":
    asyncio.run(test_url())
