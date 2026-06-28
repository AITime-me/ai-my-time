import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, GlassCard, Lead } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { trackEvent } from "@/lib/analytics";
import { useSiteSettings } from "@/components/SiteSettingsProvider";
import { Send, Mail, Phone, Sparkles } from "lucide-react";

export const Route = createFileRoute("/contacts")({
  head: () => ({
    meta: [
      { title: "Контакты — Светлана Кузнецова | AI My Time" },
      { name: "description", content: "Связаться со Светланой Кузнецовой и обсудить сайт, AI-помощника, бота, автоматизацию или digital-разбор бизнеса." },
      { property: "og:title", content: "Контакты — AI My Time" },
      { property: "og:description", content: "Обсудить задачу: сайт, AI-помощник, бот, автоматизация, разбор" },
      { property: "og:url", content: "/contacts" },
    ],
    links: [{ rel: "canonical", href: "/contacts" }],
  }),
  component: ContactsPage,
});

function ContactsPage() {
  const s = useSiteSettings();

  return (
    <SiteLayout>
      <section className="mx-auto max-w-7xl px-4 pt-14 sm:px-6 lg:px-8">
        <Eyebrow>Контакты</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">Обсудить задачу</h1>
        <Lead className="max-w-3xl">
          Расскажите, где сейчас в бизнесе больше всего ручной работы. Я посмотрю, что можно упростить, передать AI или собрать в понятный digital-механизм.
        </Lead>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-5 lg:px-8">
        <div className="space-y-4 lg:col-span-2">
          <GlassCard>
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Основной способ</p>
            <p className="mt-3 text-base">
              Ответьте на пару вопросов AI-помощнику — так проще понять задачу и выбрать подходящее решение.
            </p>
            <div className="mt-5 flex flex-col gap-2">
              <CTAButton event="click_bot_hero" size="lg" className="self-start">
                Ответить на пару вопросов
              </CTAButton>
            </div>
          </GlassCard>
          <GlassCard>
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Прямые контакты</p>
            <ul className="mt-4 space-y-3 text-sm">
              {s.telegram && (
                <li>
                  <a
                    href={s.telegram}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => trackEvent("click_telegram")}
                    className="inline-flex items-center gap-2 hover:text-[color:var(--lime)]"
                  >
                    <Send className="size-4" /> Telegram
                  </a>
                </li>
              )}
              {s.email && (
                <li>
                  <a
                    href={`mailto:${s.email}`}
                    onClick={() => trackEvent("click_email")}
                    className="inline-flex items-center gap-2 hover:text-[color:var(--lime)]"
                  >
                    <Mail className="size-4" /> {s.email}
                  </a>
                </li>
              )}
              {s.phone && (
                <li>
                  <a href={`tel:${s.phone}`} className="inline-flex items-center gap-2 hover:text-[color:var(--lime)]">
                    <Phone className="size-4" /> {s.phone}
                  </a>
                </li>
              )}
              {!s.telegram && !s.email && !s.phone && (
                <li className="text-muted-foreground">Контакты появятся скоро. Пока пишите через AI-помощника.</li>
              )}
            </ul>
          </GlassCard>
        </div>

        <div className="lg:col-span-3">
          <GlassCard className="flex flex-col gap-5 sm:p-8">
            <div className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)]">
                <Sparkles className="size-5" />
              </span>
              <div>
                <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
                  Расскажите о задаче AI-помощнику
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
                  AI-помощник задаст несколько уточняющих вопросов, поможет сформулировать запрос и передаст
                  информацию для дальнейшей работы.
                </p>
              </div>
            </div>
            <CTAButton
              event="click_bot_contacts"
              label="Задать вопрос AI-помощнику"
              size="lg"
              legalAlign="left"
              className="self-start"
              legalClassName="max-w-xl"
            />
          </GlassCard>
        </div>
      </section>
    </SiteLayout>
  );
}
