import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, GlassCard, Lead } from "@/components/SectionHeading";
import { trackEvent } from "@/lib/analytics";
import { useSiteSettings } from "@/components/SiteSettingsProvider";
import { BookOpen, Send, Sparkles } from "lucide-react";
import { CTAButton } from "@/components/CTAButton";
import { isRealBotUrl } from "@/lib/bot-url";
import { absoluteUrl } from "@/lib/site-url";

const SEO_TITLE = "Контакты AI My Time — диагностика и каналы проекта";
const SEO_DESCRIPTION =
  "Как связаться с проектом AI My Time: пройти диагностику бизнеса или читать материалы в Telegram и на других площадках.";

export const Route = createFileRoute("/contacts")({
  head: () => ({
    meta: [
      { title: SEO_TITLE },
      { name: "description", content: SEO_DESCRIPTION },
      { property: "og:title", content: SEO_TITLE },
      { property: "og:description", content: SEO_DESCRIPTION },
      { property: "og:url", content: absoluteUrl("/contacts") },
    ],
    links: [{ rel: "canonical", href: absoluteUrl("/contacts") }],
  }),
  component: ContactsPage,
});

type SocialLinks = {
  telegram_channel?: string;
  telegram?: string;
  vcru?: string;
  dzen?: string;
};

function readSocialLinks(value: unknown): SocialLinks {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  const raw = value as Record<string, unknown>;
  const pick = (key: keyof SocialLinks) =>
    typeof raw[key] === "string" && (raw[key] as string).trim()
      ? (raw[key] as string).trim()
      : undefined;
  return {
    telegram_channel: pick("telegram_channel"),
    telegram: pick("telegram"),
    vcru: pick("vcru"),
    dzen: pick("dzen"),
  };
}

function ContactsPage() {
  const s = useSiteSettings();
  const social = readSocialLinks(s.social_links);

  // Channel from social_links or project telegram setting.
  const channelUrl =
    social.telegram_channel ||
    social.telegram ||
    (isRealBotUrl(s.telegram) ? s.telegram.trim() : "");

  const platforms = [
    { label: "VC.ru", href: social.vcru },
    { label: "Дзен", href: social.dzen },
  ].filter((p): p is { label: string; href: string } => isRealBotUrl(p.href));

  const projectEmail = isRealBotUrl(s.email) ? s.email.trim() : "";
  const hasExtras = platforms.length > 0 || !!projectEmail;

  return (
    <SiteLayout>
      <section className="mx-auto max-w-7xl px-4 pt-14 sm:px-6 lg:px-8">
        <Eyebrow>Контакты</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">
          Как с нами связаться
        </h1>
        <Lead className="max-w-3xl">
          Если хотите разобраться в своей бизнес-задаче — начните с диагностики. Если хотите сначала
          посмотреть наш подход и материалы — читайте AI My Time в Telegram и на других площадках.
        </Lead>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:px-8">
        <GlassCard className="flex h-full flex-col gap-5 sm:p-8">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)]">
              <Sparkles className="size-5" />
            </span>
            <div>
              <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
                Диагностика бизнеса
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
                AI задаст несколько вопросов о текущем процессе, уточнит только необходимое и
                поможет определить, какой участок имеет смысл разбирать в первую очередь.
              </p>
            </div>
          </div>
          <CTAButton
            event="click_bot_contacts"
            size="lg"
            className="self-start"
            source="site_contacts"
          >
            Пройти диагностику
          </CTAButton>
        </GlassCard>

        <GlassCard className="flex h-full flex-col gap-5 sm:p-8">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-border/60 bg-white/5 text-[color:var(--lime)]">
              <Send className="size-5" />
            </span>
            <div>
              <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
                Telegram-канал AI My Time
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
                Разборы бизнес-процессов, CRM, AI, автоматизации, интеграций и цифровых решений для
                бизнеса.
              </p>
            </div>
          </div>
          {channelUrl ? (
            <a
              href={channelUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => trackEvent("click_telegram")}
              className="inline-flex self-start items-center justify-center gap-2 rounded-full px-6 py-3.5 text-base glass hover:border-[color:var(--lime)]/40"
            >
              <Send className="size-4" />
              Перейти в канал
            </a>
          ) : null}
        </GlassCard>
      </section>

      {hasExtras ? (
        <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6 lg:px-8">
          <GlassCard>
            <div className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-border/60 bg-white/5 text-[color:var(--lime)]">
                <BookOpen className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="text-xl font-semibold tracking-tight">Дополнительные площадки</h2>
                {platforms.length > 0 ? (
                  <ul className="mt-6 flex flex-wrap gap-3">
                    {platforms.map((p) => (
                      <li key={p.label}>
                        <a
                          href={p.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm glass hover:border-[color:var(--lime)]/40"
                        >
                          {p.label}
                        </a>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {projectEmail ? (
                  <p className="mt-6 text-sm text-muted-foreground">
                    Email:{" "}
                    <a
                      href={`mailto:${projectEmail}`}
                      onClick={() => trackEvent("click_email")}
                      className="text-foreground/90 hover:text-[color:var(--lime)]"
                    >
                      {projectEmail}
                    </a>
                  </p>
                ) : null}
              </div>
            </div>
          </GlassCard>
        </section>
      ) : (
        <div className="pb-20" />
      )}
    </SiteLayout>
  );
}
