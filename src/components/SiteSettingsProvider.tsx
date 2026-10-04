import { createContext, useContext, type ReactNode } from "react";
import {
  getSiteConfig,
  OFFICIAL_TELEGRAM_CHANNEL,
  type SiteConfig,
} from "@/config/site";

export { OFFICIAL_TELEGRAM_CHANNEL };
export type Settings = SiteConfig;

const Ctx = createContext<SiteConfig>(getSiteConfig());

export function SiteSettingsProvider({ children }: { children: ReactNode }) {
  return <Ctx.Provider value={getSiteConfig()}>{children}</Ctx.Provider>;
}

export const useSiteSettings = () => useContext(Ctx);
