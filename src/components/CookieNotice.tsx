import { useEffect, useState } from "react";
import { Link, useLocation } from "@tanstack/react-router";

const STORAGE_KEY = "ai_my_time_cookie_notice_accepted";

function isPublicRoute(pathname: string): boolean {
  if (pathname === "/auth" || pathname.startsWith("/auth/")) return false;
  if (pathname === "/admin" || pathname.startsWith("/admin/")) return false;
  return true;
}

function hasAcceptedNotice(): boolean {
  try {
    return typeof window !== "undefined" && !!window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return false;
  }
}

function saveAcceptedNotice(): void {
  try {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, "1");
    }
  } catch {
    // localStorage may be unavailable (SSR, private mode, etc.)
  }
}

export function CookieNotice() {
  const { pathname } = useLocation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!isPublicRoute(pathname) || hasAcceptedNotice()) {
      setVisible(false);
      return;
    }
    setVisible(true);
  }, [pathname]);

  const handleAccept = () => {
    saveAcceptedNotice();
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-live="polite"
      aria-label="Уведомление об использовании cookie"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-40 px-4 pb-4 sm:px-6 sm:pb-6"
    >
      <div className="pointer-events-auto mx-auto flex max-w-4xl flex-col gap-3 rounded-2xl border border-[color:var(--lime)]/20 bg-[color:var(--graphite)]/95 p-4 shadow-[var(--shadow-glow)] backdrop-blur-md sm:flex-row sm:items-center sm:gap-4 sm:p-5">
        <p className="flex-1 text-xs leading-relaxed text-muted-foreground sm:text-sm">
          Мы используем cookie, чтобы сайт работал корректно, анализировать посещаемость и улучшать
          сервис. Продолжая пользоваться сайтом, вы соглашаетесь с использованием cookie в
          соответствии с{" "}
          <Link
            to="/privacy"
            className="text-[color:var(--lime)] underline underline-offset-2 decoration-[color:var(--lime)]/40 hover:decoration-[color:var(--lime)]"
          >
            Политикой обработки персональных данных
          </Link>
          .
        </p>
        <button
          type="button"
          onClick={handleAccept}
          className="shrink-0 rounded-full bg-[image:var(--gradient-primary)] px-5 py-2 text-sm font-medium text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)] transition-all hover:brightness-110 sm:px-6"
        >
          Понятно
        </button>
      </div>
    </div>
  );
}
