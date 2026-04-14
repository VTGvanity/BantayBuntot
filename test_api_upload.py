import requests
import base64
import json

def test_api_upload():
    # 1x1 transparent PNG
    base64_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    data_url = f"data:image/png;base64,{base64_img}"
    
    payload = {
        "image_data": data_url,
        "file_name": "api_test.png"
    }
    
    # We need to simulate a logged in user, or just see if it fails due to auth
    # Actually, the user is authenticated in the browser.
    # Let's see what happens without auth first.
    print("Testing API upload without auth...")
    response = requests.post("http://127.0.0.1:8000/api/upload-image/", json=payload)
    print("Status:", response.status_code)
    print("Response JSON:", response.json())

if __name__ == "__main__":
    test_api_upload()
