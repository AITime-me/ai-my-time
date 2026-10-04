/** Official AI My Time Telegram channel (public). Distinct from bot_link / AI consultant. */
export const OFFICIAL_TELEGRAM_CHANNEL = "https://t.me/AIautomationsales";

export type SiteSocialLinks = {
  telegram_channel?: string;
  telegram?: string;
  vcru?: string;
  dzen?: string;
  [key: string]: unknown;
};

export type SiteConfig = {
  bot_link: string;
  bot_widget_enabled: boolean;
  bot_widget_text: string;
  main_cta_text: string;
  telegram: string;
  email: string;
  phone: string;
  social_links: SiteSocialLinks;
  site_title: string;
  site_description: string;
  og_image: string;
};

function readEnv(name: string): string | undefined {
  try {
    const viteVal = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env?.[
      name
    ];
    if (typeof viteVal === "string" && viteVal.trim() !== "") return viteVal.trim();
  } catch {
    // import.meta.env may be unavailable in some SSR contexts
  }
  try {
    const procVal = typeof process !== "undefined" ? process.env?.[name] : undefined;
    if (typeof procVal === "string" && procVal.trim() !== "") return procVal.trim();
  } catch {
    // process may be unavailable in the browser
  }
  return undefined;
}

function resolveBotLink(): string {
  return readEnv("BOT_LINK") || readEnv("VITE_BOT_LINK") || "";
}

const defaults: SiteConfig = {
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

export function getSiteConfig(): SiteConfig {
  const bot_link = resolveBotLink() || defaults.bot_link;
  return {
    ...defaults,
    bot_link,
    social_links: { ...defaults.social_links },
  };
}
