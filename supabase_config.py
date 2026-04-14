import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://your-project-id.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'your-supabase-anon-key')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', 'your-supabase-service-role-key')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', f'postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres')

# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret')

# Table Names
USERS_TABLE = 'users'
ANIMAL_REPORTS_TABLE = 'animal_reports'
PINNED_LOCATIONS_TABLE = 'pinned_locations'
REPORT_COMMENTS_TABLE = 'report_comments'

# File Upload Configuration
STORAGE_BUCKET = 'animal-images'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# CORS Configuration
ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    # Add your production domain here
]

# Debug output - remove this in production
# print("Supabase configuration loaded:")
# print(f"URL: {SUPABASE_URL}")
# print(f"Key exists: {bool(SUPABASE_KEY and SUPABASE_KEY != 'your-supabase-anon-key')}")
# print(f"URL length: {len(SUPABASE_URL)}")
# print(f"Users table: {USERS_TABLE}")
# print(f"Animal reports table: {ANIMAL_REPORTS_TABLE}")
# print(f"Pinned locations table: {PINNED_LOCATIONS_TABLE}")
