export const DIAGNOSTIC_BOT_BASE_URL = "https://t.me/aimytime_business_bot";

export const DIAGNOSTIC_SOURCES = [
  "site_header",
  "site_contacts",
  "site_consultant",
  "site_consultant_radar",
] as const;

export type DiagnosticSource = (typeof DIAGNOSTIC_SOURCES)[number];

const DIAGNOSTIC_SOURCE_SET = new Set<string>(DIAGNOSTIC_SOURCES);

/**
 * Builds a Telegram deep link only for a known diagnostic source.
 * Runtime validation prevents untrusted values from becoming bot payloads.
 */
export function getDiagnosticUrl(source: unknown): string | null {
  if (typeof source !== "string" || !DIAGNOSTIC_SOURCE_SET.has(source)) return null;
  return `${DIAGNOSTIC_BOT_BASE_URL}?start=${source}`;
}
