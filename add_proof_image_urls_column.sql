-- Migration: Add proof_image_urls column to animal_reports table
-- This column stores an array of multiple proof of rescue image URLs

-- Add the column if it doesn't exist
ALTER TABLE public.animal_reports 
ADD COLUMN IF NOT EXISTS proof_image_urls TEXT[];

-- Add comment for documentation
COMMENT ON COLUMN public.animal_reports.proof_image_urls IS 'Array of multiple proof of rescue image URLs';
