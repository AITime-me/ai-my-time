import { Link } from "@tanstack/react-router";
import { CTAButton } from "./CTAButton";
import { useSiteSettings } from "./SiteSettingsProvider";
import { trackEvent } from "@/lib/analytics";
import { Send, Mail } from "lucide-react";

export function Footer() {
  const s = useSiteSettings();
  const year = new Date().getFullYear();
  return (
    <footer className="mt-24 border-t border-border/40 bg-background/60">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-4 lg:px-8">
        <div className="lg:col-span-2">
          <p className="text-sm uppercase tracking-wider text-muted-foreground">AI My Time</p>
          <h3 className="mt-2 text-xl font-semibold">Светлана Кузнецова</h3>
          <p className="mt-3 max-w-md text-sm text-muted-foreground">
            Сайты, AI-помощники, боты и автоматизация для малого бизнеса, которому не хватает людей, времени и порядка.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <CTAButton event="click_bot_footer" />
            {s.telegram && (
              <a
                href={s.telegram}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => trackEvent("click_telegram")}
                className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm glass hover:border-[color:var(--lime)]/40"
              >
                <Send className="size-4" /> Telegram
              </a>
            )}
            {s.email && (
              <a
                href={`mailto:${s.email}`}
                onClick={() => trackEvent("click_email")}
                className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm glass hover:border-[color:var(--lime)]/40"
              >
                <Mail className="size-4" /> {s.email}
              </a>
            )}
          </div>
        </div>

        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Навигация</p>
          <ul className="mt-3 space-y-2 text-sm">
            <li><Link to="/" className="hover:text-foreground text-muted-foreground">Главная</Link></li>
            <li><Link to="/services" className="hover:text-foreground text-muted-foreground">Услуги</Link></li>
            <li><Link to="/cases" className="hover:text-foreground text-muted-foreground">Решения</Link></li>
            <li><Link to="/about" className="hover:text-foreground text-muted-foreground">Обо мне</Link></li>
            <li><Link to="/contacts" className="hover:text-foreground text-muted-foreground">Контакты</Link></li>
          </ul>
        </div>

        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Юридическое</p>
          <ul className="mt-3 space-y-2 text-sm">
            <li><Link to="/privacy" className="hover:text-foreground text-muted-foreground">Политика конфиденциальности</Link></li>
            <li><Link to="/offer" className="hover:text-foreground text-muted-foreground">Договор оферты</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border/40">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-2 px-4 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:px-6 lg:px-8">
          <p>© {year} AI My Time / Светлана Кузнецова. Все права защищены.</p>
          <p>Выглядит как вау. Работает как система.</p>
        </div>
      </div>
    </footer>
  );
}