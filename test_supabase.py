#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== Supabase Connection Test ===")
print(f"Python version: {sys.version}")
print()

# Test environment variables
print("1. Testing environment variables:")
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

print(f"SUPABASE_URL: {supabase_url}")
print(f"SUPABASE_KEY exists: {bool(supabase_key)}")
print(f"SUPABASE_KEY length: {len(supabase_key) if supabase_key else 0}")
print()

# Test basic network connectivity
print("2. Testing network connectivity:")
try:
    import requests
    response = requests.get(f"{supabase_url}/rest/v1/", timeout=10)
    print(f"HTTP Status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
except Exception as e:
    print(f"Network error: {e}")
print()

# Test Supabase client
print("3. Testing Supabase client:")
try:
    from supabase import create_client, Client
    print("Supabase library imported successfully")
    
    client = create_client(supabase_url, supabase_key)
    print("Supabase client created successfully")
    
    # Test a simple query
    try:
        response = client.table('users').select('count').execute()
        print(f"Query successful: {response}")
    except Exception as query_error:
        print(f"Query error: {query_error}")
        
except Exception as client_error:
    print(f"Client error: {client_error}")
    print(f"Error type: {type(client_error)}")
    import traceback
    traceback.print_exc()
print()

# Test DNS resolution
print("4. Testing DNS resolution:")
import socket
try:
    hostname = supabase_url.replace('https://', '').replace('http://', '').split('/')[0]
    ip_address = socket.gethostbyname(hostname)
    print(f"Hostname: {hostname}")
    print(f"IP Address: {ip_address}")
except Exception as dns_error:
    print(f"DNS error: {dns_error}")

print("\n=== Test Complete ===")
