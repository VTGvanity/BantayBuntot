-- Drop the existing constraint that restricts status values
ALTER TABLE public.animal_reports DROP CONSTRAINT IF EXISTS animal_reports_status_check;

-- Add the updated constraint including 'waiting_for_user_approval', 'rescuer_declined', and 'pending_completion'
ALTER TABLE public.animal_reports ADD CONSTRAINT animal_reports_status_check CHECK (status IN ('pending', 'waiting_for_user_approval', 'in_progress', 'pending_completion', 'completed', 'resolved', 'rescuer_declined'));
