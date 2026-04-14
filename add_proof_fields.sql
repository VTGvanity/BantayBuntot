-- Add Proof of Rescue tracking to the animal_reports schema
ALTER TABLE public.animal_reports ADD COLUMN IF NOT EXISTS proof_image_url TEXT;
ALTER TABLE public.animal_reports ADD COLUMN IF NOT EXISTS rescued_address TEXT;
ALTER TABLE public.animal_reports ADD COLUMN IF NOT EXISTS rescued_latitude DECIMAL(10, 8);
ALTER TABLE public.animal_reports ADD COLUMN IF NOT EXISTS rescued_longitude DECIMAL(11, 8);
