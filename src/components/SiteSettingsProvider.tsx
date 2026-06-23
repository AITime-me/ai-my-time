import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSiteSettings } from "@/lib/site.functions";

type Settings = NonNullable<Awaited<ReturnType<typeof getSiteSettings>>>;

const defaults: Settings = {
  bot_link: "#",
  bot_widget_enabled: true,
  bot_widget_text: "Задать вопрос AI-помощнику",
  main_cta_text: "Обсудить задачу",
  yandex_metrika_id: "",
  google_analytics_id: "",
  analytics_enabled: false,
  telegram: "",
  email: "",
  phone: "",
  social_links: {},
  site_title: "Светлана Кузнецова — AI My Time",
  site_description: "Сайты, AI-помощники, боты и автоматизация для малого бизнеса",
  og_image: "",
};

const Ctx = createContext<Settings>(defaults);

export function SiteSettingsProvider({ children }: { children: ReactNode }) {
  const { data } = useQuery({
    queryKey: ["site_settings"],
    queryFn: () => getSiteSettings(),
    staleTime: 60_000,
  });
  const value = { ...defaults, ...(data ?? {}) } as Settings;
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useSiteSettings = () => useContext(Ctx);