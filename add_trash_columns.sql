-- SQL Script to add trash bin support to animal_reports table
-- Run this in your Supabase SQL Editor

-- Add columns for soft deletion
ALTER TABLE public.animal_reports 
ADD COLUMN IF NOT EXISTS is_deleted_by_user BOOLEAN DEFAULT false;

ALTER TABLE public.animal_reports 
ADD COLUMN IF NOT EXISTS is_deleted_by_rescuer BOOLEAN DEFAULT false;

-- Index for performance when filtering for trash
CREATE INDEX IF NOT EXISTS idx_animal_reports_trash_user ON public.animal_reports(is_deleted_by_user);
CREATE INDEX IF NOT EXISTS idx_animal_reports_trash_rescuer ON public.animal_reports(is_deleted_by_rescuer);

COMMENT ON COLUMN public.animal_reports.is_deleted_by_user IS 'Whether the reporter has moved this completed rescue to their trash bin';
COMMENT ON COLUMN public.animal_reports.is_deleted_by_rescuer IS 'Whether the rescuer has moved this completed rescue to their trash bin';
