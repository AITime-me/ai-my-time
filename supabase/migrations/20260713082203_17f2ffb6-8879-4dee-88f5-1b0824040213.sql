ALTER TABLE public.cases
  ADD COLUMN IF NOT EXISTS status text,
  ADD COLUMN IF NOT EXISTS ecosystem_role text;