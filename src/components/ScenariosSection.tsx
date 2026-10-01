import { Link } from "@tanstack/react-router";

import { solutions } from "@/data/solutions";
import { Reveal } from "@/components/Reveal";
import { Eyebrow, GlassCard, H2, Lead } from "@/components/SectionHeading";

export function ScenariosSection() {
  return (
    <section
      id="scenarios"
      aria-labelledby="scenarios-heading"
      className="mx-auto max-w-7xl scroll-mt-24 px-4 py-16 sm:px-6 lg:px-8"
    >
      <Reveal>
        <Eyebrow>Сценарии</Eyebrow>
        <H2 id="scenarios-heading" className="mt-4 max-w-3xl">
          Как может работать система в вашем бизнесе
        </H2>
        <Lead className="max-w-3xl">
          Типовые сценарии — от первого обращения клиента до записи, заказа, передачи сотруднику,
          работы в CRM и внутренних AI-инструментов. Откройте любой сценарий, чтобы увидеть процесс
          по шагам.
        </Lead>
      </Reveal>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {solutions.map((item, index) => (
          <Reveal key={item.slug} delay={index * 0.04} className="h-full">
            <Link
              to="/solutions/$slug"
              params={{ slug: item.slug }}
              className="block h-full rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--lime)]/50"
            >
              <GlassCard className="flex h-full flex-col">
                <p className="text-[11px] font-medium uppercase tracking-wider text-[color:var(--lime)]">
                  Запрос бизнеса
                </p>
                <blockquote className="mt-3 text-sm leading-relaxed text-foreground/90">
                  «{item.quote}»
                </blockquote>
                <h3 className="mt-5 text-lg font-semibold leading-snug">{item.title}</h3>
                <p className="mt-3 flex-1 text-sm text-muted-foreground">{item.cardDescription}</p>
                <span className="mt-5 text-sm font-medium text-[color:var(--lime)]">
                  Посмотреть, как это работает →
                </span>
              </GlassCard>
            </Link>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
