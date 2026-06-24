
-- Lock down site_settings: anon must not read the full table
DROP POLICY IF EXISTS "Public can read settings" ON public.site_settings;
REVOKE SELECT ON public.site_settings FROM anon;

-- Admins (authenticated) keep full read access
CREATE POLICY "Admins read settings"
  ON public.site_settings
  FOR SELECT
  TO authenticated
  USING (public.has_role(auth.uid(), 'admin'));

-- Public-safe accessor: only non-sensitive fields, runs as definer to bypass RLS
CREATE OR REPLACE FUNCTION public.get_public_site_settings()
RETURNS TABLE (
  bot_link text,
  bot_widget_enabled boolean,
  bot_widget_text text,
  main_cta_text text,
  telegram text,
  email text,
  phone text,
  social_links jsonb,
  site_title text,
  site_description text,
  og_image text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT bot_link, bot_widget_enabled, bot_widget_text, main_cta_text,
         telegram, email, phone, social_links,
         site_title, site_description, og_image
  FROM public.site_settings
  WHERE id = 1
$$;

GRANT EXECUTE ON FUNCTION public.get_public_site_settings() TO anon, authenticated;

-- Friendly view wrapping the safe function
CREATE OR REPLACE VIEW public.public_site_settings AS
  SELECT * FROM public.get_public_site_settings();

GRANT SELECT ON public.public_site_settings TO anon, authenticated;

-- Analytics IDs: only exposed when analytics_enabled = true
CREATE OR REPLACE FUNCTION public.get_public_analytics()
RETURNS TABLE (
  yandex_metrika_id text,
  google_analytics_id text,
  analytics_enabled boolean
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT yandex_metrika_id, google_analytics_id, analytics_enabled
  FROM public.site_settings
  WHERE id = 1 AND analytics_enabled = true
$$;

GRANT EXECUTE ON FUNCTION public.get_public_analytics() TO anon, authenticated;
