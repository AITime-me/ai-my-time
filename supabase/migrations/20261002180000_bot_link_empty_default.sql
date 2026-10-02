-- Fail-closed: stop using "#" as a sentinel for unset bot_link.
-- App treats "#" as absent via isRealBotUrl(); this aligns DB defaults/data.

ALTER TABLE public.site_settings
  ALTER COLUMN bot_link SET DEFAULT '';

UPDATE public.site_settings
SET bot_link = ''
WHERE bot_link IS NULL
   OR btrim(bot_link) = ''
   OR btrim(bot_link) = '#';
