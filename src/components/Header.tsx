import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { Menu, X, Sparkles } from "lucide-react";
import { CTAButton } from "./CTAButton";

const nav = [
  { to: "/services", label: "Услуги" },
  { to: "/cases", label: "Решения" },
  { to: "/about", label: "Обо мне" },
  { to: "/contacts", label: "Контакты" },
] as const;

export function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-border/40 backdrop-blur-xl bg-background/70">
      <div className="mx-auto flex min-h-16 max-w-7xl items-start justify-between gap-4 px-4 py-2 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5 group" onClick={() => setOpen(false)}>
          <span className="grid size-9 place-items-center rounded-xl bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)]">
            <Sparkles className="size-4" />
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-sm font-semibold">Светлана Кузнецова</span>
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">AI My Time</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {nav.map((n) => (
            <Link
              key={n.to}
              to={n.to}
              activeProps={{ className: "text-foreground bg-white/5" }}
              inactiveProps={{ className: "text-muted-foreground" }}
              className="rounded-full px-3.5 py-1.5 text-sm transition-colors hover:text-foreground hover:bg-white/5"
            >
              {n.label}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-start">
          <CTAButton event="click_bot_header" size="md" legalClassName="max-w-[520px]" />
        </div>

        <button className="md:hidden text-foreground" onClick={() => setOpen((v) => !v)} aria-label="Меню">
          {open ? <X className="size-6" /> : <Menu className="size-6" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-border/40 bg-background/95 px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-1">
            {nav.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2.5 text-base text-foreground/90 hover:bg-white/5"
              >
                {n.label}
              </Link>
            ))}
            <div className="mt-3 flex flex-col gap-2">
              <CTAButton event="click_bot_header" size="lg" className="w-full" wrapperClassName="w-full" />
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}