import requests
import os

url = "https://cqtonydelbjnokaezeym.supabase.co/rest/v1/users?user_type=eq.rescuer&select=email&limit=5"
headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNxdG9ueWRlbGJqbm9rYWV6ZXltIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzY5MTc1MywiZXhwIjoyMDg5MjY3NzUzfQ.znqS1P57AD5X8c5uLGqUwPs-RvW6YYxvZZEIAVlO8TM",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNxdG9ueWRlbGJqbm9rYWV6ZXltIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzY5MTc1MywiZXhwIjoyMDg5MjY3NzUzfQ.znqS1P57AD5X8c5uLGqUwPs-RvW6YYxvZZEIAVlO8TM"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    if data:
        print("Found rescuers:")
        for user in data:
            print(f"- {user['email']}")
    else:
        print("No rescuers found.")
except Exception as e:
    print(f"Error: {e}")
