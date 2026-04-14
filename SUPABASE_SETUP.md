# Supabase Setup Guide for BantayBuntot

## 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project" 
3. Sign up/login with your GitHub account
4. Create a new organization (or use existing)
5. Create a new project:
   - **Project Name**: BantayBuntot
   - **Database Password**: Choose a strong password
   - **Region**: Choose the closest region to your users
   - **Wait for project to be created** (2-3 minutes)

## 2. Get Project Credentials

1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **API**
3. Copy the following:
   - **Project URL** (e.g., `https://your-project-id.supabase.co`)
   - **anon public** key (e.g., `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)
   - **service_role** key (found in the same section)

## 3. Set Up Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` file and replace with your credentials:
   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_KEY=your-supabase-service-role-key
   DATABASE_URL=postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres
   JWT_SECRET=your-jwt-secret
   ```

## 4. Set Up Database Schema

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the entire contents of `supabase_schema.sql`
4. Click **Run** to execute the schema

This will create:
- `users` table (extends auth.users)
- `animal_reports` table
- `pinned_locations` table
- `report_comments` table
- `report_status_history` table
- Row Level Security (RLS) policies
- Storage bucket for images
- Triggers and views

## 5. Configure Storage

1. Go to **Storage** in your Supabase dashboard
2. You should see an `animal-images` bucket created by the schema
3. Click on the bucket and ensure it's set to **public**

## 6. Install Dependencies

```bash
pip install -r requirements.txt
```

## 7. Update Django Settings

Add to your `BantayBuntot/settings.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Add to INSTALLED_APPS if not already there
INSTALLED_APPS = [
    # ... other apps
    'corsheaders',
]

# Add CORS middleware
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ... other middleware
]

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Authentication settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
```

## 8. Test the Setup

1. Run migrations:
   ```bash
   python manage.py migrate
   ```

2. Create superuser:
   ```bash
   python manage.py createsuperuser
   ```

3. Start development server:
   ```bash
   python manage.py runserver
   ```

4. Test registration:
   - Go to `http://localhost:8000/register/`
   - Create a new account
   - Check Supabase dashboard → Authentication → Users to see the new user

5. Test login:
   - Go to `http://localhost:8000/login/`
   - Login with your created account

## 9. Test Animal Reports

1. Login as a user
2. Go to dashboard
3. Click "Report Animal"
4. Fill out the form and submit
5. Check Supabase dashboard → Table Editor → animal_reports

## 10. Test Pinned Locations

1. Go to Map View in user dashboard
2. Click "Pin My Location"
3. Check Supabase dashboard → Table Editor → pinned_locations
4. Login as rescuer and check if pinned locations appear

## Troubleshooting

### Common Issues:

1. **"Invalid JWT" errors**
   - Check your `SUPABASE_KEY` in `.env`
   - Ensure you're using the `anon` key, not `service_role`

2. **"Permission denied" errors**
   - Check RLS policies in SQL Editor
   - Ensure user is properly authenticated

3. **CORS errors**
   - Add your domain to `CORS_ALLOWED_ORIGINS`
   - Check Supabase project settings → API → CORS

4. **Database connection errors**
   - Verify `DATABASE_URL` in `.env`
   - Check database password matches what you set in Supabase

### Debug Tips:

1. Check browser console for JavaScript errors
2. Check Django development server output
3. Check Supabase dashboard logs
4. Use browser network tab to see API requests

## Production Considerations

1. **Security**:
   - Use environment variables, never commit secrets
   - Enable additional RLS policies as needed
   - Use HTTPS in production

2. **Performance**:
   - Add database indexes for frequently queried fields
   - Consider Supabase Edge Functions for complex logic
   - Implement caching for frequently accessed data

3. **Scaling**:
   - Monitor Supabase usage limits
   - Consider upgrading to Pro plan for production
   - Implement proper error handling and retry logic

## Next Steps

Once basic setup is working, you can:

1. Add email verification for registration
2. Implement password reset functionality
3. Add file upload for animal photos
4. Create admin dashboard for managing reports
5. Add real-time notifications for rescuers
6. Implement geolocation-based report filtering
