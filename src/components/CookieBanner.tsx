import { useEffect, useId, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  COOKIE_SETTINGS_EVENT,
  getCookieConsent,
  setCookieConsent,
  type CookieConsentValue,
} from "@/lib/consent";

export function CookieBanner() {
  const titleId = useId();
  const [visible, setVisible] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
    setVisible(getCookieConsent() === null);

    const onOpenSettings = () => setVisible(true);
    window.addEventListener(COOKIE_SETTINGS_EVENT, onOpenSettings);
    return () => window.removeEventListener(COOKIE_SETTINGS_EVENT, onOpenSettings);
  }, []);

  const choose = (value: CookieConsentValue) => {
    setCookieConsent(value);
    setVisible(false);
  };

  if (!hydrated || !visible) return null;

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-labelledby={titleId}
      className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-start p-3 sm:bottom-4 sm:left-4 sm:right-auto sm:max-w-md sm:p-0"
    >
      <div className="pointer-events-auto glass w-full rounded-2xl border border-white/10 p-4 shadow-[var(--shadow-glow)] sm:p-5">
        <p id={titleId} className="text-sm font-medium text-foreground">
          Файлы cookie и аналитика
        </p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Мы используем необходимые технологии для работы сайта и, с вашего согласия, аналитику,
          чтобы понимать, как используется сайт.{" "}
          <Link
            to="/privacy"
            className="underline underline-offset-2 hover:text-foreground"
          >
            Политика обработки персональных данных
          </Link>
        </p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-stretch">
          <button
            type="button"
            onClick={() => choose("accepted")}
            className="inline-flex flex-1 items-center justify-center rounded-full border border-white/20 bg-white/5 px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:border-[color:var(--lime)]/40 hover:bg-white/10"
          >
            Принять
          </button>
          <button
            type="button"
            onClick={() => choose("essential_only")}
            className="inline-flex flex-1 items-center justify-center rounded-full border border-white/15 px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:border-white/30 hover:text-foreground"
          >
            Только необходимые
          </button>
        </div>
      </div>
    </div>
  );
}
