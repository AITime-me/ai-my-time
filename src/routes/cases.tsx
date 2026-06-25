import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, Lead, GlassCard } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { Reveal } from "@/components/Reveal";
import { getCases } from "@/lib/site.functions";
import { trackEvent } from "@/lib/analytics";

export const Route = createFileRoute("/cases")({
  head: ({ loaderData }) => {
    const cases = Array.isArray(loaderData) ? loaderData : [];
    return {
      meta: [
        { title: "Примеры AI-решений для бизнеса | AI My Time" },
        { name: "description", content: "Примеры сайтов, AI-помощников, ботов, мини-CRM и автоматизаций для малого бизнеса от Светланы Кузнецовой." },
        { property: "og:title", content: "Примеры решений AI My Time" },
        { property: "og:description", content: "Сайты, AI-помощники, боты, мини-CRM, автоматизация" },
        { property: "og:url", content: "/cases" },
      ],
      links: [{ rel: "canonical", href: "/cases" }],
      scripts: [
        {
          type: "application/ld+json",
          children: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            name: "Примеры решений AI My Time",
            description: "Примеры сайтов, AI-помощников, ботов, мини-CRM и автоматизаций для малого бизнеса от Светланы Кузнецовой.",
            url: "/cases",
            hasPart: cases.map((c) => ({
              "@type": "CreativeWork",
              name: c.title,
              description: [c.task, c.solution, c.result].filter(Boolean).join(" "),
              about: c.category,
            })),
          }),
        },
      ],
    };
  },
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: ["cases"], queryFn: () => getCases() }),
  component: CasesPage,
});

function CasesPage() {
  const { data } = useSuspenseQuery({ queryKey: ["cases"], queryFn: () => getCases() });
  return (
    <SiteLayout>
      <section className="mx-auto max-w-7xl px-4 pt-14 sm:px-6 lg:px-8">
        <Eyebrow>Решения</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">Примеры решений</h1>
        <Lead className="max-w-3xl">
          Здесь — примеры решений, которые можно собрать. Без выдуманных цифр и фейковых отзывов. Реальные кейсы появятся после первых релизов.
        </Lead>
      </section>
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(data ?? []).map((c, i) => (
            <Reveal key={c.id} delay={i * 0.04}>
              <GlassCard
                className="flex h-full cursor-default flex-col"
              >
                {c.category && (
                  <span className="self-start rounded-full border border-border/60 bg-white/5 px-2.5 py-1 text-[11px] uppercase tracking-wider text-muted-foreground">
                    {c.category}
                  </span>
                )}
                <h3 className="mt-3 text-lg font-semibold">{c.title}</h3>
                {c.task && <p className="mt-3 text-sm"><span className="text-muted-foreground">Задача: </span>{c.task}</p>}
                {c.solution && <p className="mt-2 text-sm"><span className="text-muted-foreground">Решение: </span>{c.solution}</p>}
                {c.result && <p className="mt-2 text-sm"><span className="text-muted-foreground">Результат: </span>{c.result}</p>}
                <div className="mt-6 flex flex-col gap-2">
                  <CTAButton event="click_bot_cases" variant="secondary" arrow>
                    <span onClick={() => trackEvent("click_case_card", { id: c.id })}>Хочу похожее решение</span>
                  </CTAButton>
                </div>
              </GlassCard>
            </Reveal>
          ))}
        </div>
      </section>
    </SiteLayout>
  );
}