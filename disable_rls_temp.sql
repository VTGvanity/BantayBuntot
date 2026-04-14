-- Temporary fix: Disable RLS on users table for testing
-- Run this in Supabase SQL Editor if the fix_rls_policies.sql doesn't work

ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;

-- You can re-enable it later with:
-- ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
