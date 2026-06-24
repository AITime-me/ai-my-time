import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, Lead, GlassCard } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { LegalNote } from "@/components/LegalNote";
import { Reveal } from "@/components/Reveal";
import { getServices } from "@/lib/site.functions";
import { ArrowRight } from "lucide-react";
import { trackEvent } from "@/lib/analytics";

export const Route = createFileRoute("/services/")({
  head: () => ({
    meta: [
      { title: "Услуги AI My Time — сайты, AI-помощники, боты и автоматизация" },
      { name: "description", content: "Сайты, AI-помощники, боты, мини-CRM и автоматизация для малого бизнеса. Помогаю убрать повторяющиеся задачи из ручного режима." },
      { property: "og:title", content: "Услуги AI My Time" },
      { property: "og:description", content: "Сайты, AI-помощники, боты, мини-CRM и автоматизация" },
      { property: "og:url", content: "/services" },
    ],
    links: [{ rel: "canonical", href: "/services" }],
  }),
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: ["services"], queryFn: () => getServices() }),
  component: ServicesIndex,
});

function ServicesIndex() {
  const { data } = useSuspenseQuery({ queryKey: ["services"], queryFn: () => getServices() });
  return (
    <SiteLayout>
      <section className="mx-auto max-w-7xl px-4 pt-14 sm:px-6 lg:px-8">
        <Eyebrow>Услуги</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">Digital-решения для малого бизнеса</h1>
        <Lead className="max-w-3xl">
          Я не начинаю с вопроса «какой инструмент вам поставить». Сначала смотрю, где бизнесу не хватает людей, времени и порядка. А потом подбираю решение: сайт, AI-помощника, бота, автоматизацию, мини-CRM или разбор.
        </Lead>
      </section>
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-4 lg:grid-cols-2">
          {(data ?? []).map((s, i) => (
            <Reveal key={s.id} delay={i * 0.04}>
              <GlassCard className="flex h-full flex-col">
                <h3 className="text-xl font-semibold">{s.title}</h3>
                <p className="mt-3 text-sm text-muted-foreground">{s.short_description}</p>
                {s.audience && (
                  <p className="mt-4 text-sm"><span className="text-muted-foreground">Кому подходит: </span>{s.audience}</p>
                )}
                {s.result && (
                  <p className="mt-2 text-sm"><span className="text-muted-foreground">Результат: </span>{s.result}</p>
                )}
                <div className="mt-6 flex flex-col gap-2">
                  <div className="flex flex-wrap items-center gap-3">
                  <Link
                    to="/services/$slug" params={{ slug: s.slug }}
                    onClick={() => trackEvent("click_service_card", { slug: s.slug })}
                    className="inline-flex items-center gap-1 text-sm text-[color:var(--lime)] hover:underline"
                  >
                    Подробнее <ArrowRight className="size-4" />
                  </Link>
                  <CTAButton event="click_bot_services">{s.cta_text || "Обсудить задачу"}</CTAButton>
                  </div>
                  <LegalNote />
                </div>
              </GlassCard>
            </Reveal>
          ))}
        </div>
      </section>
    </SiteLayout>
  );
}