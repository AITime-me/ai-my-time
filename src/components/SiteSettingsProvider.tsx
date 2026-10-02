import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSiteSettings } from "@/lib/site.functions";

type Settings = NonNullable<Awaited<ReturnType<typeof getSiteSettings>>>;

/** Official AI My Time Telegram channel (public). Distinct from bot_link / AI consultant. */
export const OFFICIAL_TELEGRAM_CHANNEL = "https://t.me/AIautomationsales";

const defaults: Settings = {
  bot_link: "",
  bot_widget_enabled: true,
  bot_widget_text: "Задать вопрос AI-помощнику",
  main_cta_text: "Обсудить задачу",
  telegram: OFFICIAL_TELEGRAM_CHANNEL,
  email: "",
  phone: "",
  social_links: { telegram_channel: OFFICIAL_TELEGRAM_CHANNEL },
  site_title: "Автоматизация бизнес-процессов, CRM и AI для бизнеса | AI My Time",
  site_description:
    "AI My Time проектирует и автоматизирует бизнес-процессы: CRM, AI-сотрудники, интеграции, сайты и цифровые сервисы для работы с клиентами, продажами и аналитикой.",
  og_image: "",
};

function isFilledUrl(value: unknown): value is string {
  return typeof value === "string" && value.trim() !== "" && value.trim() !== "#";
}

function resolveSettings(data: Settings | null | undefined): Settings {
  const merged = { ...defaults, ...(data ?? {}) } as Settings;

  // DB seed leaves telegram as '' — keep official channel unless admin set a real URL.
  if (!isFilledUrl(merged.telegram)) {
    merged.telegram = OFFICIAL_TELEGRAM_CHANNEL;
  }

  const rawSocial =
    merged.social_links &&
    typeof merged.social_links === "object" &&
    !Array.isArray(merged.social_links)
      ? { ...(merged.social_links as Record<string, unknown>) }
      : {};
  if (!isFilledUrl(rawSocial.telegram_channel) && !isFilledUrl(rawSocial.telegram)) {
    rawSocial.telegram_channel = OFFICIAL_TELEGRAM_CHANNEL;
  }
  merged.social_links = rawSocial;

  return merged;
}

const Ctx = createContext<Settings>(defaults);

export function SiteSettingsProvider({ children }: { children: ReactNode }) {
  const { data } = useQuery({
    queryKey: ["site_settings"],
    queryFn: () => getSiteSettings(),
    staleTime: 60_000,
  });
  const value = resolveSettings(data);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useSiteSettings = () => useContext(Ctx);
