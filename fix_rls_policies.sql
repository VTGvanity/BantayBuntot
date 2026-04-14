-- Fix RLS Policies for BantayBuntot
-- Run this in your Supabase SQL Editor to fix the infinite recursion issue

-- Drop existing problematic policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.users;
DROP POLICY IF EXISTS "Users can update own profile" ON public.users;
DROP POLICY IF EXISTS "Rescuers can view all users" ON public.users;

-- Create corrected RLS Policies for Users Table
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Rescuers can view all users" ON public.users
    FOR SELECT USING (
        auth.uid() IN (
            SELECT id FROM public.users WHERE user_type = 'rescuer'
        )
    );

-- Drop existing problematic policies for animal_reports
DROP POLICY IF EXISTS "Users can view own reports" ON public.animal_reports;
DROP POLICY IF EXISTS "Rescuers can view all reports" ON public.animal_reports;
DROP POLICY IF EXISTS "Users can create reports" ON public.animal_reports;
DROP POLICY IF EXISTS "Users can update own reports" ON public.animal_reports;
DROP POLICY IF EXISTS "Rescuers can update all reports" ON public.animal_reports;

-- Create corrected RLS Policies for Animal Reports
CREATE POLICY "Users can view own reports" ON public.animal_reports
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Rescuers can view all reports" ON public.animal_reports
    FOR SELECT USING (
        auth.uid() IN (
            SELECT id FROM public.users WHERE user_type = 'rescuer'
        )
    );

CREATE POLICY "Users can create reports" ON public.animal_reports
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own reports" ON public.animal_reports
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Rescuers can update all reports" ON public.animal_reports
    FOR UPDATE USING (
        auth.uid() IN (
            SELECT id FROM public.users WHERE user_type = 'rescuer'
        )
    );

-- Drop existing problematic policies for pinned_locations
DROP POLICY IF EXISTS "Users can view own pinned locations" ON public.pinned_locations;
DROP POLICY IF EXISTS "Rescuers can view all pinned locations" ON public.pinned_locations;
DROP POLICY IF EXISTS "Users can create pinned locations" ON public.pinned_locations;
DROP POLICY IF EXISTS "Users can update own pinned locations" ON public.pinned_locations;
DROP POLICY IF EXISTS "Users can delete own pinned locations" ON public.pinned_locations;

-- Create corrected RLS Policies for Pinned Locations
CREATE POLICY "Users can view own pinned locations" ON public.pinned_locations
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Rescuers can view all pinned locations" ON public.pinned_locations
    FOR SELECT USING (
        auth.uid() IN (
            SELECT id FROM public.users WHERE user_type = 'rescuer'
        )
    );

CREATE POLICY "Users can create pinned locations" ON public.pinned_locations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own pinned locations" ON public.pinned_locations
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own pinned locations" ON public.pinned_locations
    FOR DELETE USING (auth.uid() = user_id);

-- Drop existing problematic policies for report_comments
DROP POLICY IF EXISTS "Users can view comments on accessible reports" ON public.report_comments;
DROP POLICY IF EXISTS "Users can create comments on accessible reports" ON public.report_comments;

-- Create corrected RLS Policies for Report Comments
CREATE POLICY "Users can view comments on accessible reports" ON public.report_comments
    FOR SELECT USING (
        auth.uid() = user_id OR
        auth.uid() IN (
            SELECT user_id FROM public.animal_reports WHERE id = report_id
        ) OR
        auth.uid() IN (
            SELECT id FROM public.users WHERE user_type = 'rescuer'
        )
    );

CREATE POLICY "Users can create comments on accessible reports" ON public.report_comments
    FOR INSERT WITH CHECK (
        auth.uid() = user_id OR
        auth.uid() IN (
            SELECT user_id FROM public.animal_reports WHERE id = report_id
        ) OR
        auth.uid() IN (
            SELECT id FROM public.users WHERE user_type = 'rescuer'
        )
    );

-- Drop existing problematic policies for report_status_history
DROP POLICY IF EXISTS "Users can view status history of accessible reports" ON public.report_status_history;

-- Create corrected RLS Policies for Report Status History
CREATE POLICY "Users can view status history of accessible reports" ON public.report_status_history
    FOR SELECT USING (
        auth.uid() IN (
            SELECT user_id FROM public.animal_reports WHERE id = report_id
        ) OR
        auth.uid() IN (
            SELECT id FROM public.users WHERE user_type = 'rescuer'
        )
    );

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO service_role;
