import { useState, useEffect } from "react";
import { MessageCircle, X } from "lucide-react";
import { useSiteSettings } from "./SiteSettingsProvider";
import { trackEvent } from "@/lib/analytics";
import { motion, AnimatePresence } from "framer-motion";
import { BotLegalNote } from "./BotLegalNote";

export function BotWidget() {
  const s = useSiteSettings();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted || !s.bot_widget_enabled) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 sm:bottom-6 sm:right-6">
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.95 }}
            className="mb-3 w-[280px] glass rounded-2xl p-4 sm:w-[320px]"
          >
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium">AI-помощник AI My Time</p>
              <button onClick={() => setOpen(false)} aria-label="Закрыть" className="text-muted-foreground hover:text-foreground">
                <X className="size-4" />
              </button>
            </div>
            <p className="text-sm text-muted-foreground">
              Расскажу про сайты, AI-помощников и автоматизацию. Уточню задачу, передам Светлане.
            </p>
            <a
              href={s.bot_link || "#"}
              target={s.bot_link && s.bot_link !== "#" ? "_blank" : undefined}
              rel="noopener noreferrer"
              onClick={() => trackEvent("open_bot_widget")}
              className="mt-3 inline-flex w-full items-center justify-center rounded-full bg-[image:var(--gradient-primary)] px-4 py-2 text-sm font-medium text-[color:var(--lime-foreground)]"
            >
              Открыть помощника
            </a>
            <BotLegalNote align="left" />
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={() => {
          trackEvent("open_bot_widget");
          setOpen((v) => !v);
        }}
        className="flex items-center gap-2 rounded-full bg-[image:var(--gradient-primary)] px-4 py-3 text-sm font-medium text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)] transition-transform hover:scale-105"
        aria-label={s.bot_widget_text || "Задать вопрос AI-помощнику"}
      >
        <MessageCircle className="size-5" />
        <span className="hidden sm:inline">{s.bot_widget_text || "Задать вопрос AI-помощнику"}</span>
      </button>
    </div>
  );
}