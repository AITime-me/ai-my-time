declare global {
  interface Window {
    ym?: (id: number, action: string, ...args: unknown[]) => void;
    gtag?: (...args: unknown[]) => void;
  }
}

export function trackEvent(name: string, params?: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  try {
    const ymId = (window as unknown as { __YM_ID__?: string }).__YM_ID__;
    if (window.ym && ymId) {
      window.ym(Number(ymId), "reachGoal", name, params);
    }
    if (window.gtag) {
      window.gtag("event", name, params || {});
    }
  } catch {
    /* no-op */
  }
}

export {};