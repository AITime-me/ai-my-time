import type { ReactNode } from "react";
import { Header } from "./Header";
import { Footer } from "./Footer";
import { BotWidget } from "./BotWidget";
import { CookieNotice } from "./CookieNotice";

export function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
      <CookieNotice />
      <BotWidget />
    </div>
  );
}