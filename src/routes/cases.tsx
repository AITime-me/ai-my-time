import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, Lead, GlassCard } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { Reveal } from "@/components/Reveal";
import { getCases } from "@/lib/site.functions";
import { ArrowRight } from "lucide-react";

type CaseItem = {
  id: string;
  title: string;
  category?: string | null;
  status?: string | null;
  task?: string | null;
  solution?: string | null;
  ecosystem_role?: string | null;
};

export const Route = createFileRoute("/cases")({
  head: ({ loaderData }) => {
    const cases = Array.isArray(loaderData) ? (loaderData as CaseItem[]) : [];
    return {
      meta: [
        { title: "Проекты для салонов красоты | AI My Time" },
        { name: "description", content: "Проекты для салонов красоты: сайт, AI-администратор, онлайн-запись и CRM, калькулятор экономики процедур, внутренний AI-ассистент владельца." },
        { property: "og:title", content: "Проекты для салонов красоты" },
        { property: "og:description", content: "Экосистема цифровых решений для салонов красоты: сайт, AI-администратор, онлайн-запись, CRM, аналитика." },
        { property: "og:url", content: "/cases" },
      ],
      links: [{ rel: "canonical", href: "/cases" }],
      scripts: [
        {
          type: "application/ld+json",
          children: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            name: "Проекты для салонов красоты",
            description: "Проекты для салонов красоты: сайт, AI-администратор, онлайн-запись, CRM, аналитика.",
            url: "/cases",
            hasPart: cases.map((c) => ({
              "@type": "CreativeWork",
              name: c.title,
              description: [c.task, c.solution, c.ecosystem_role].filter(Boolean).join(" "),
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

const ecosystemSteps = [
  "SEO, контент, реклама и акции",
  "Сайт студии",
  "AI-администратор",
  "Онлайн-запись и CRM",
  "Аналитика и AI-ассистент владельца",
];

function CasesPage() {
  const { data } = useSuspenseQuery({ queryKey: ["cases"], queryFn: () => getCases() });
  const items = (data ?? []) as unknown as CaseItem[];
  return (
    <SiteLayout>
      <section className="mx-auto max-w-7xl px-4 pt-14 sm:px-6 lg:px-8">
        <Eyebrow>Портфолио</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">Проекты для салонов красоты</h1>
        <Lead className="max-w-3xl">
          Я создаю цифровые решения для салонов красоты, в которых маркетинг, сайт, общение с клиенткой,
          онлайн-запись и управление процессами связаны в одну систему. Проекты находятся на разных стадиях:
          от архитектуры и MVP до внедрения. Здесь нет выдуманных результатов — только то, что уже
          создано или спроектировано.
        </Lead>
      </section>

      <section className="mx-auto max-w-7xl px-4 pt-10 sm:px-6 lg:px-8">
        <GlassCard className="hover:-translate-y-0 hover:border-border/60 hover:shadow-none">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Экосистема «Твоё время»</p>
          <ol className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-3 text-sm">
            {ecosystemSteps.map((step, i) => (
              <li key={step} className="flex items-center gap-2">
                <span className="rounded-full border border-border/60 bg-white/5 px-3 py-1.5 text-foreground/90">
                  {step}
                </span>
                {i < ecosystemSteps.length - 1 && (
                  <ArrowRight className="size-4 text-[color:var(--lime)]/80" />
                )}
              </li>
            ))}
          </ol>
        </GlassCard>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((c, i) => (
            <Reveal key={c.id} delay={i * 0.04}>
              <GlassCard
                className="flex h-full cursor-default flex-col"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {c.category && (
                    <span className="rounded-full border border-border/60 bg-white/5 px-2.5 py-1 text-[11px] uppercase tracking-wider text-muted-foreground">
                      {c.category}
                    </span>
                  )}
                  {c.status && (
                    <span className="rounded-full border border-[color:var(--lime)]/40 bg-[color:var(--lime)]/10 px-2.5 py-1 text-[11px] uppercase tracking-wider text-[color:var(--lime)]">
                      {c.status}
                    </span>
                  )}
                </div>
                <h3 className="mt-3 text-lg font-semibold">{c.title}</h3>
                {c.task && <p className="mt-3 text-sm"><span className="text-muted-foreground">Задача: </span>{c.task}</p>}
                {c.solution && <p className="mt-2 text-sm"><span className="text-muted-foreground">Что создаётся: </span>{c.solution}</p>}
                {c.ecosystem_role && <p className="mt-2 text-sm"><span className="text-muted-foreground">Роль в экосистеме: </span>{c.ecosystem_role}</p>}
                <div className="mt-6 flex flex-col gap-2">
                  <CTAButton event="click_bot_cases" variant="secondary" arrow label="Обсудить проект" />
                </div>
              </GlassCard>
            </Reveal>
          ))}
        </div>
      </section>
    </SiteLayout>
  );
}