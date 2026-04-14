-- Supabase Database Schema for BantayBuntot
-- Run this SQL in your Supabase project SQL Editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Users Table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    user_type TEXT NOT NULL CHECK (user_type IN ('user', 'rescuer')),
    phone TEXT UNIQUE CHECK (phone ~ '^[0-9]{10}$'),
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure phone is unique if table already exists
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_phone_check') THEN
        ALTER TABLE public.users ADD CONSTRAINT users_phone_check CHECK (phone ~ '^[0-9]{10}$');
    END IF;
END $$;

-- Animal Reports Table
CREATE TABLE IF NOT EXISTS public.animal_reports (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    animal_type TEXT NOT NULL CHECK (animal_type IN ('dog', 'cat', 'other')),
    animal_condition TEXT NOT NULL CHECK (animal_condition IN ('healthy', 'injured', 'sick', 'pregnant')),
    description TEXT NOT NULL,
    address TEXT NOT NULL,
    landmark TEXT,
    additional_location_info TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'waiting_for_user_approval', 'in_progress', 'completed', 'resolved', 'rescuer_declined')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    images TEXT[], -- Array of image URLs
    proof_image_url TEXT,
    rescued_address TEXT,
    rescued_latitude DECIMAL(10, 8),
    rescued_longitude DECIMAL(11, 8),
    assigned_rescuer_id UUID REFERENCES public.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pinned Locations Table
CREATE TABLE IF NOT EXISTS public.pinned_locations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Report Comments Table (for communication between users and rescuers)
CREATE TABLE IF NOT EXISTS public.report_comments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    report_id UUID REFERENCES public.animal_reports(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    comment TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Report Status History Table
CREATE TABLE IF NOT EXISTS public.report_status_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    report_id UUID REFERENCES public.animal_reports(id) ON DELETE CASCADE,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_by UUID REFERENCES public.users(id),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_users_user_type ON public.users(user_type);

CREATE INDEX IF NOT EXISTS idx_animal_reports_user_id ON public.animal_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_animal_reports_status ON public.animal_reports(status);
CREATE INDEX IF NOT EXISTS idx_animal_reports_animal_type ON public.animal_reports(animal_type);
CREATE INDEX IF NOT EXISTS idx_animal_reports_created_at ON public.animal_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_animal_reports_location ON public.animal_reports USING GIST (point(longitude, latitude));

CREATE INDEX IF NOT EXISTS idx_pinned_locations_user_id ON public.pinned_locations(user_id);
CREATE INDEX IF NOT EXISTS idx_pinned_locations_location ON public.pinned_locations USING GIST (point(longitude, latitude));
CREATE INDEX IF NOT EXISTS idx_pinned_locations_created_at ON public.pinned_locations(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_report_comments_report_id ON public.report_comments(report_id);
CREATE INDEX IF NOT EXISTS idx_report_comments_created_at ON public.report_comments(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_report_status_history_report_id ON public.report_status_history(report_id);
CREATE INDEX IF NOT EXISTS idx_report_status_history_created_at ON public.report_status_history(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.animal_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pinned_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_status_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies for Users Table
DROP POLICY IF EXISTS "Users can view own profile" ON public.users;
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.users;
CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Rescuers can view all users" ON public.users;
CREATE POLICY "Rescuers can view all users" ON public.users
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id = auth.uid() AND user_type = 'rescuer'
        )
    );

-- RLS Policies for Animal Reports
DROP POLICY IF EXISTS "Users can view own reports" ON public.animal_reports;
CREATE POLICY "Users can view own reports" ON public.animal_reports
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Rescuers can view all reports" ON public.animal_reports;
CREATE POLICY "Rescuers can view all reports" ON public.animal_reports
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id = auth.uid() AND user_type = 'rescuer'
        )
    );

DROP POLICY IF EXISTS "Users can create reports" ON public.animal_reports;
CREATE POLICY "Users can create reports" ON public.animal_reports
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own reports" ON public.animal_reports;
CREATE POLICY "Users can update own reports" ON public.animal_reports
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Rescuers can update all reports" ON public.animal_reports;
CREATE POLICY "Rescuers can update all reports" ON public.animal_reports
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id = auth.uid() AND user_type = 'rescuer'
        )
    );

-- RLS Policies for Pinned Locations
DROP POLICY IF EXISTS "Users can view own pinned locations" ON public.pinned_locations;
CREATE POLICY "Users can view own pinned locations" ON public.pinned_locations
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Rescuers can view all pinned locations" ON public.pinned_locations;
CREATE POLICY "Rescuers can view all pinned locations" ON public.pinned_locations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id = auth.uid() AND user_type = 'rescuer'
        )
    );

DROP POLICY IF EXISTS "Users can create pinned locations" ON public.pinned_locations;
CREATE POLICY "Users can create pinned locations" ON public.pinned_locations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own pinned locations" ON public.pinned_locations;
CREATE POLICY "Users can update own pinned locations" ON public.pinned_locations
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own pinned locations" ON public.pinned_locations;
CREATE POLICY "Users can delete own pinned locations" ON public.pinned_locations
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for Report Comments
DROP POLICY IF EXISTS "Users can view comments on accessible reports" ON public.report_comments;
CREATE POLICY "Users can view comments on accessible reports" ON public.report_comments
    FOR SELECT USING (
        auth.uid() = user_id OR
        EXISTS (
            SELECT 1 FROM public.animal_reports ar
            WHERE ar.id = report_id AND (
                ar.user_id = auth.uid() OR
                EXISTS (
                    SELECT 1 FROM public.users 
                    WHERE id = auth.uid() AND user_type = 'rescuer'
                )
            )
        )
    );

DROP POLICY IF EXISTS "Users can create comments on accessible reports" ON public.report_comments;
CREATE POLICY "Users can create comments on accessible reports" ON public.report_comments
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.animal_reports ar
            WHERE ar.id = report_id AND (
                ar.user_id = auth.uid() OR
                EXISTS (
                    SELECT 1 FROM public.users 
                    WHERE id = auth.uid() AND user_type = 'rescuer'
                )
            )
        )
    );

-- RLS Policies for Report Status History
DROP POLICY IF EXISTS "Users can view status history of accessible reports" ON public.report_status_history;
CREATE POLICY "Users can view status history of accessible reports" ON public.report_status_history
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.animal_reports ar
            WHERE ar.id = report_id AND (
                ar.user_id = auth.uid() OR
                EXISTS (
                    SELECT 1 FROM public.users 
                    WHERE id = auth.uid() AND user_type = 'rescuer'
                )
            )
        )
    );

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS handle_users_updated_at ON public.users;
CREATE TRIGGER handle_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS handle_animal_reports_updated_at ON public.animal_reports;
CREATE TRIGGER handle_animal_reports_updated_at
    BEFORE UPDATE ON public.animal_reports
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS handle_pinned_locations_updated_at ON public.pinned_locations;
CREATE TRIGGER handle_pinned_locations_updated_at
    BEFORE UPDATE ON public.pinned_locations
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Trigger to create user profile after signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, full_name, username, user_type, phone)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', 'User'),
        COALESCE(NEW.raw_user_meta_data->>'username', NEW.email),
        COALESCE(NEW.raw_user_meta_data->>'user_type', 'user'),
        NEW.raw_user_meta_data->>'phone'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Storage Bucket for Animal Images
INSERT INTO storage.buckets (id, name, public) 
VALUES ('animal-images', 'animal-images', true)
ON CONFLICT (id) DO NOTHING;

-- Storage Policies
DROP POLICY IF EXISTS "Users can upload images" ON storage.objects;
CREATE POLICY "Users can upload images" ON storage.objects
    FOR INSERT WITH CHECK (
        bucket_id = 'animal-images' AND
        auth.role() = 'authenticated'
    );

DROP POLICY IF EXISTS "Users can view own images" ON storage.objects;
CREATE POLICY "Users can view own images" ON storage.objects
    FOR SELECT USING (
        bucket_id = 'animal-images' AND
        (auth.role() = 'authenticated' OR auth.role() = 'anon')
    );

DROP POLICY IF EXISTS "Users can update own images" ON storage.objects;
CREATE POLICY "Users can update own images" ON storage.objects
    FOR UPDATE USING (
        bucket_id = 'animal-images' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

DROP POLICY IF EXISTS "Users can delete own images" ON storage.objects;
CREATE POLICY "Users can delete own images" ON storage.objects
    FOR DELETE USING (
        bucket_id = 'animal-images' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Create a view for rescuers to see all reports with user info
CREATE OR REPLACE VIEW rescuer_reports_view AS
SELECT 
    ar.*,
    u.full_name as reporter_name,
    u.email as reporter_email,
    u.phone as reporter_phone
FROM public.animal_reports ar
LEFT JOIN public.users u ON ar.user_id = u.id;

-- Grant access to the view
GRANT SELECT ON rescuer_reports_view TO authenticated;

-- Create a view for rescuers to see all pinned locations with user info
CREATE OR REPLACE VIEW rescuer_pinned_locations_view AS
SELECT 
    pl.*,
    u.full_name as user_name,
    u.email as user_email,
    u.phone as user_phone
FROM public.pinned_locations pl
LEFT JOIN public.users u ON pl.user_id = u.id
WHERE pl.is_active = true;

-- Grant access to the view
GRANT SELECT ON rescuer_pinned_locations_view TO authenticated;
