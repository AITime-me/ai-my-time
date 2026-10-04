/** First-party consent helpers. No backend, no PII. */

export const COOKIE_CONSENT_KEY = "ai_my_time_cookie_consent_v1";
export const CONSULTANT_PD_CONSENT_KEY = "ai_my_time_consultant_pd_consent_v1";
export const COOKIE_CONSENT_EVENT = "ai-my-time:cookie-consent";
export const COOKIE_SETTINGS_EVENT = "ai-my-time:open-cookie-settings";

export type CookieConsentValue = "accepted" | "essential_only";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function getCookieConsent(): CookieConsentValue | null {
  if (!canUseStorage()) return null;
  try {
    const raw = window.localStorage.getItem(COOKIE_CONSENT_KEY);
    if (raw === "accepted" || raw === "essential_only") return raw;
    return null;
  } catch {
    return null;
  }
}

export function setCookieConsent(value: CookieConsentValue): void {
  if (!canUseStorage()) return;
  try {
    window.localStorage.setItem(COOKIE_CONSENT_KEY, value);
    window.dispatchEvent(new CustomEvent(COOKIE_CONSENT_EVENT, { detail: value }));
  } catch {
    // private mode / blocked storage
  }
}

export function hasAnalyticsConsent(): boolean {
  return getCookieConsent() === "accepted";
}

export function openCookieSettings(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(COOKIE_SETTINGS_EVENT));
}

export function getConsultantPdConsent(): boolean {
  if (!canUseStorage()) return false;
  try {
    return window.localStorage.getItem(CONSULTANT_PD_CONSENT_KEY) === "accepted";
  } catch {
    return false;
  }
}

export function setConsultantPdConsent(accepted: boolean): void {
  if (!canUseStorage()) return;
  try {
    if (accepted) {
      window.localStorage.setItem(CONSULTANT_PD_CONSENT_KEY, "accepted");
    } else {
      window.localStorage.removeItem(CONSULTANT_PD_CONSENT_KEY);
    }
  } catch {
    // private mode / blocked storage
  }
}
