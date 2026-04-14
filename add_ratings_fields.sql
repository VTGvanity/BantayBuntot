-- Add Rating fields to the animal_reports schema
ALTER TABLE public.animal_reports ADD COLUMN IF NOT EXISTS rescuer_to_user_rating INTEGER CHECK (rescuer_to_user_rating >= 1 AND rescuer_to_user_rating <= 5);
ALTER TABLE public.animal_reports ADD COLUMN IF NOT EXISTS rescuer_to_user_feedback TEXT;
ALTER TABLE public.animal_reports ADD COLUMN IF NOT EXISTS user_to_rescuer_rating INTEGER CHECK (user_to_rescuer_rating >= 1 AND user_to_rescuer_rating <= 5);
ALTER TABLE public.animal_reports ADD COLUMN IF NOT EXISTS user_to_rescuer_feedback TEXT;
