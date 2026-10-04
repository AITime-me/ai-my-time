import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import {
  CONSULTANT_PD_CONSENT_KEY,
  COOKIE_CONSENT_KEY,
  getConsultantPdConsent,
  getCookieConsent,
  hasAnalyticsConsent,
  setConsultantPdConsent,
  setCookieConsent,
} from "../src/lib/consent";

const memory = new Map<string, string>();

function installStorage(): void {
  memory.clear();
  const localStorage = {
    getItem: (key: string) => memory.get(key) ?? null,
    setItem: (key: string, value: string) => {
      memory.set(key, String(value));
    },
    removeItem: (key: string) => {
      memory.delete(key);
    },
    clear: () => memory.clear(),
  };
  Object.defineProperty(globalThis, "localStorage", {
    value: localStorage,
    configurable: true,
  });
  Object.defineProperty(globalThis, "window", {
    value: {
      localStorage,
      dispatchEvent: () => true,
    },
    configurable: true,
  });
}

beforeEach(() => {
  installStorage();
});

afterEach(() => {
  memory.clear();
});

describe("cookie consent storage", () => {
  test("starts empty and does not grant analytics", () => {
    expect(getCookieConsent()).toBeNull();
    expect(hasAnalyticsConsent()).toBe(false);
  });

  test("accepted enables analytics consent", () => {
    setCookieConsent("accepted");
    expect(getCookieConsent()).toBe("accepted");
    expect(hasAnalyticsConsent()).toBe(true);
    expect(window.localStorage.getItem(COOKIE_CONSENT_KEY)).toBe("accepted");
  });

  test("essential_only keeps analytics off", () => {
    setCookieConsent("essential_only");
    expect(getCookieConsent()).toBe("essential_only");
    expect(hasAnalyticsConsent()).toBe(false);
  });

  test("ignores unknown stored values", () => {
    window.localStorage.setItem(COOKIE_CONSENT_KEY, "maybe");
    expect(getCookieConsent()).toBeNull();
    expect(hasAnalyticsConsent()).toBe(false);
  });
});

describe("consultant personal data consent", () => {
  test("defaults to false", () => {
    expect(getConsultantPdConsent()).toBe(false);
  });

  test("persists acceptance and can be cleared", () => {
    setConsultantPdConsent(true);
    expect(getConsultantPdConsent()).toBe(true);
    expect(window.localStorage.getItem(CONSULTANT_PD_CONSENT_KEY)).toBe("accepted");
    setConsultantPdConsent(false);
    expect(getConsultantPdConsent()).toBe(false);
    expect(window.localStorage.getItem(CONSULTANT_PD_CONSENT_KEY)).toBeNull();
  });
});
