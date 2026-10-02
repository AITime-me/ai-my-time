const DEFAULT_SITE_URL = "https://aimytime.ru";

function resolveSiteUrl(): string {
  const fromEnv =
    (typeof process !== "undefined" && (process.env.SITE_URL || process.env.VITE_SITE_URL)) ||
    (typeof import.meta !== "undefined" &&
      (import.meta as ImportMeta & { env?: { VITE_SITE_URL?: string } }).env?.VITE_SITE_URL) ||
    "";
  const raw = String(fromEnv || DEFAULT_SITE_URL)
    .trim()
    .replace(/\/+$/, "");
  return raw || DEFAULT_SITE_URL;
}

/** Canonical production origin (no trailing slash). Env override: SITE_URL / VITE_SITE_URL. */
export const SITE_URL = resolveSiteUrl();

/** Shared public meta description for root/home SEO. */
export const SITE_DESCRIPTION =
  "AI My Time проектирует и автоматизирует бизнес-процессы: CRM, AI, интеграции, сайты и цифровые сервисы для работы с клиентами, продажами и аналитикой.";

/** Build an absolute URL for SEO/meta/sitemap. Already-absolute inputs are returned unchanged. */
export function absoluteUrl(pathOrUrl: string = "/"): string {
  const value = (pathOrUrl || "/").trim();
  if (/^https?:\/\//i.test(value)) return value;

  const path = value.startsWith("/") ? value : `/${value}`;
  if (path === "/") return `${SITE_URL}/`;

  return `${SITE_URL}${path.replace(/\/+$/, "")}`;
}
