import asyncio
import base64
from supabase_client import supabase_manager

async def test_upload():
    print("Testing upload...")
    base64_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    img_bytes = base64.b64decode(base64_img)
    
    filename = "wowie/test_script.png"
    client = supabase_manager.get_client(use_service_role=True)
    
    try:
        response = client.storage.from_("animal-images").upload(
            filename,
            img_bytes,
            file_options={
                'content-type': 'image/png',
                'upsert': 'true'
            }
        )
        print("Response status code:", getattr(response, 'status_code', None))
        print("Response object:", response)
        
        try:
            print("Response JSON:", response.json())
        except:
            print("Response text:", getattr(response, 'text', 'No text'))
    except Exception as e:
        print("Exception:", str(e))

if __name__ == "__main__":
    asyncio.run(test_upload())
