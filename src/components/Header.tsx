import { Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, Menu, Sparkles, X } from "lucide-react";
import { CTAButton } from "./CTAButton";
import { solutions } from "@/data/solutions";

const navLinks = [
  { href: "/#amocrm", label: "amoCRM" },
  { href: "/#articles", label: "Статьи" },
  { to: "/about", label: "О проекте" },
  { to: "/contacts", label: "Контакты" },
] as const;

export function Header() {
  const [open, setOpen] = useState(false);
  const [solutionsOpen, setSolutionsOpen] = useState(false);
  const solutionsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!solutionsOpen) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!solutionsRef.current?.contains(event.target as Node)) {
        setSolutionsOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [solutionsOpen]);

  const closeAll = () => {
    setOpen(false);
    setSolutionsOpen(false);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-border/40 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-2 px-4 py-2 md:px-3 md:gap-2 lg:gap-4 lg:px-8">
        <Link to="/" className="group flex items-center gap-2.5" onClick={closeAll}>
          <span className="grid size-9 place-items-center rounded-xl bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)]">
            <Sparkles className="size-4" />
          </span>
          <span className="text-sm font-semibold tracking-tight">AI My Time</span>
        </Link>

        <nav className="hidden items-center gap-0.5 md:flex lg:gap-1">
          <div className="relative" ref={solutionsRef}>
            <button
              type="button"
              aria-expanded={solutionsOpen}
              aria-haspopup="menu"
              onClick={() => setSolutionsOpen((v) => !v)}
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground md:px-2 lg:px-3.5"
            >
              Решения
              <ChevronDown
                className={`size-3.5 transition-transform ${solutionsOpen ? "rotate-180" : ""}`}
              />
            </button>
            {solutionsOpen && (
              <div
                role="menu"
                className="absolute left-0 top-full z-50 mt-2 min-w-[18rem] rounded-2xl border border-border/50 bg-background/95 p-2 shadow-[var(--shadow-glow)] backdrop-blur-xl"
              >
                {solutions.map((item) => (
                  <Link
                    key={item.slug}
                    to="/solutions/$slug"
                    params={{ slug: item.slug }}
                    role="menuitem"
                    onClick={closeAll}
                    className="block rounded-xl px-3 py-2 text-sm text-foreground/90 transition-colors hover:bg-white/5 hover:text-foreground"
                  >
                    {item.navLabel}
                  </Link>
                ))}
                <div className="my-1.5 h-px bg-border/40" />
                <Link
                  to="/"
                  hash="scenarios"
                  role="menuitem"
                  onClick={closeAll}
                  className="block rounded-xl px-3 py-2 text-sm font-medium text-[color:var(--lime)] transition-colors hover:bg-white/5"
                >
                  Все решения →
                </Link>
              </div>
            )}
          </div>

          {navLinks.map((item) =>
            "href" in item ? (
              <a
                key={item.href}
                href={item.href}
                className="rounded-full px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground md:px-2 lg:px-3.5"
              >
                {item.label}
              </a>
            ) : (
              <Link
                key={item.to}
                to={item.to}
                activeProps={{ className: "text-foreground bg-white/5" }}
                inactiveProps={{ className: "text-muted-foreground" }}
                className="rounded-full px-2.5 py-1.5 text-sm transition-colors hover:bg-white/5 hover:text-foreground md:px-2 lg:px-3.5"
              >
                {item.label}
              </Link>
            ),
          )}
        </nav>

        <div className="hidden items-center md:flex">
          <CTAButton event="click_bot_header" size="md">
            Пройти диагностику
          </CTAButton>
        </div>

        <button
          className="text-foreground md:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label="Меню"
        >
          {open ? <X className="size-6" /> : <Menu className="size-6" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-border/40 bg-background/95 px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-1">
            <p className="px-3 pt-1 text-[11px] uppercase tracking-wider text-muted-foreground">
              Решения
            </p>
            {solutions.map((item) => (
              <Link
                key={item.slug}
                to="/solutions/$slug"
                params={{ slug: item.slug }}
                onClick={closeAll}
                className="rounded-lg px-3 py-2.5 text-base text-foreground/90 hover:bg-white/5"
              >
                {item.navLabel}
              </Link>
            ))}
            <Link
              to="/"
              hash="scenarios"
              onClick={closeAll}
              className="rounded-lg px-3 py-2.5 text-base font-medium text-[color:var(--lime)] hover:bg-white/5"
            >
              Все решения →
            </Link>
            <div className="my-2 h-px bg-border/40" />
            {navLinks.map((item) =>
              "href" in item ? (
                <a
                  key={item.href}
                  href={item.href}
                  onClick={closeAll}
                  className="rounded-lg px-3 py-2.5 text-base text-foreground/90 hover:bg-white/5"
                >
                  {item.label}
                </a>
              ) : (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={closeAll}
                  className="rounded-lg px-3 py-2.5 text-base text-foreground/90 hover:bg-white/5"
                >
                  {item.label}
                </Link>
              ),
            )}
            <div className="mt-3">
              <CTAButton event="click_bot_header" size="lg" className="w-full">
                Пройти диагностику
              </CTAButton>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
