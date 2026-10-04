import type { ReactNode } from "react";
import { Header } from "./Header";
import { Footer } from "./Footer";
import { ConsultantWidget } from "./ConsultantWidget";
import { TargetCursor } from "./TargetCursor";

export function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <TargetCursor />
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
      <ConsultantWidget />
    </div>
  );
}
