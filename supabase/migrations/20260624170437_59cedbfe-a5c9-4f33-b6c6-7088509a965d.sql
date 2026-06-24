-- Restrict user_roles modifications to admins only
CREATE POLICY "Admins can insert roles" ON public.user_roles
  FOR INSERT TO authenticated
  WITH CHECK (has_role(auth.uid(), 'admin'::app_role));

CREATE POLICY "Admins can update roles" ON public.user_roles
  FOR UPDATE TO authenticated
  USING (has_role(auth.uid(), 'admin'::app_role))
  WITH CHECK (has_role(auth.uid(), 'admin'::app_role));

CREATE POLICY "Admins can delete roles" ON public.user_roles
  FOR DELETE TO authenticated
  USING (has_role(auth.uid(), 'admin'::app_role));

-- Replace overly permissive INSERT policy on leads with a validated one
DROP POLICY IF EXISTS "Anyone can submit a lead" ON public.leads;

CREATE POLICY "Anyone can submit a valid lead" ON public.leads
  FOR INSERT TO anon, authenticated
  WITH CHECK (
    name IS NOT NULL
    AND length(btrim(name)) BETWEEN 1 AND 200
    AND (phone_or_telegram IS NULL OR length(phone_or_telegram) <= 200)
    AND (email IS NULL OR length(email) <= 200)
    AND (business_area IS NULL OR length(business_area) <= 500)
    AND (task IS NULL OR length(task) <= 2000)
    AND (message IS NULL OR length(message) <= 5000)
    AND (source IS NULL OR length(source) <= 100)
    AND status = 'new'
    AND admin_comment IS NULL
  );