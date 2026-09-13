import { Link } from "@tanstack/react-router";
import { CTAButton } from "./CTAButton";
import { useSiteSettings } from "./SiteSettingsProvider";
import { trackEvent } from "@/lib/analytics";
import { Mail, Send } from "lucide-react";

const navLinks = [
  { href: "/#solutions", label: "Решения" },
  { href: "/#amocrm", label: "amoCRM" },
  { href: "/#articles", label: "Статьи" },
  { to: "/about", label: "О проекте" },
  { to: "/contacts", label: "Контакты" },
  { href: "/#diagnostics", label: "Диагностика" },
] as const;

/** Future SEO landings — labels only until routes exist (no broken links). */
const futureSeoLinks = [
  "ИИ для бизнеса",
  "Чат-боты и AI-консультанты",
  "Интеграции CRM и сервисов",
  "Сайты и цифровые сервисы",
] as const;

const legalLinks = [
  { to: "/privacy", label: "Политика конфиденциальности" },
  { to: "/offer", label: "Договор оферты" },
] as const;

export function Footer() {
  const s = useSiteSettings();
  const year = new Date().getFullYear();

  return (
    <footer className="mt-24 border-t border-border/40">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="glass rounded-3xl p-8 sm:p-10 lg:p-12">
          <div className="grid gap-10 lg:grid-cols-12 lg:gap-8">
            <div className="lg:col-span-5">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">AI MY TIME</p>
              <h3 className="mt-2 text-2xl font-semibold tracking-tight">AI My Time</h3>
              <p className="mt-3 max-w-sm text-base font-medium text-foreground/90">
                Проектирование и автоматизация бизнес-процессов
              </p>
              <p className="mt-3 max-w-sm text-sm text-muted-foreground">
                CRM, AI, автоматизация, интеграции, сайты и цифровые сервисы для бизнеса.
              </p>
              <div className="mt-6 flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-3">
                  <CTAButton event="click_bot_footer">Пройти диагностику</CTAButton>
                  {s.telegram && (
                    <a
                      href={s.telegram}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => trackEvent("click_telegram")}
                      className="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm glass hover:border-accent/40"
                    >
                      <Send className="size-4" /> Telegram
                    </a>
                  )}
                  {s.email && (
                    <a
                      href={`mailto:${s.email}`}
                      onClick={() => trackEvent("click_email")}
                      className="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm glass hover:border-accent/40"
                    >
                      <Mail className="size-4" /> {s.email}
                    </a>
                  )}
                </div>
              </div>
            </div>

            <div className="lg:col-span-4 lg:pl-6">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Навигация</p>
              <ul className="mt-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-1">
                {navLinks.map((link) => (
                  <li key={link.label}>
                    {"href" in link ? (
                      <a
                        href={link.href}
                        className="group inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                      >
                        <span className="h-px w-4 bg-border transition-all group-hover:w-6 group-hover:bg-accent" />
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        to={link.to}
                        className="group inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                      >
                        <span className="h-px w-4 bg-border transition-all group-hover:w-6 group-hover:bg-accent" />
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>

              <p className="mt-8 text-xs uppercase tracking-wider text-muted-foreground">
                Направления
              </p>
              <ul className="mt-4 space-y-2.5">
                {futureSeoLinks.map((label) => (
                  <li key={label}>
                    <span
                      className="text-sm text-muted-foreground/60"
                      title="Страница появится позже"
                    >
                      {label}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="lg:col-span-3">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Юридическое</p>
              <ul className="mt-4 space-y-2.5">
                {legalLinks.map((link) => (
                  <li key={link.to}>
                    <Link
                      to={link.to}
                      className="text-sm text-muted-foreground/70 transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-border/40">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-2 px-4 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:px-6 lg:px-8">
          <p>© {year} AI My Time. Все права защищены.</p>
          <p>Проектирование и автоматизация бизнес-процессов</p>
        </div>
      </div>
    </footer>
  );
}
