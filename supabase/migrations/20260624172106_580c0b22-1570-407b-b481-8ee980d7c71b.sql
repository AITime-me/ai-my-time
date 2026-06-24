
REVOKE EXECUTE ON FUNCTION public.get_public_site_settings() FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.get_public_analytics() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_public_site_settings() TO service_role;
GRANT EXECUTE ON FUNCTION public.get_public_analytics() TO service_role;
