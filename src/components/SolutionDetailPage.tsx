import { Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";

import { SOLUTION_IMAGE_SIZE, type SolutionScenario } from "@/data/solutions";
import { SiteLayout } from "@/components/SiteLayout";
import { CTAButton } from "@/components/CTAButton";
import { Reveal } from "@/components/Reveal";
import { Eyebrow, H2, Lead } from "@/components/SectionHeading";

export function SolutionDetailPage({ solution }: { solution: SolutionScenario }) {
  return (
    <SiteLayout>
      <section className="mx-auto max-w-7xl px-4 pt-14 sm:px-6 lg:px-8">
        <Link
          to="/"
          hash="scenarios"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> К сценариям на главной
        </Link>
        <Eyebrow className="mt-6">{solution.type}</Eyebrow>
        <h1 className="mt-5 max-w-4xl text-4xl font-semibold tracking-tight sm:text-5xl">
          {solution.h1}
        </h1>
        <Lead className="max-w-3xl">{solution.intro}</Lead>
      </section>

      <section
        aria-label="Как устроен процесс по шагам"
        className="mx-auto w-full max-w-[90rem] px-2 py-12 sm:px-6 lg:px-8"
      >
        <ol className="space-y-10 sm:space-y-14">
          {solution.steps.map((step, index) => (
            <li key={step.src}>
              <Reveal>
                <figure>
                  <figcaption className="mx-auto mb-4 max-w-3xl px-2 sm:px-0">
                    <p className="font-mono text-xs uppercase tracking-wider text-[color:var(--lime)]">
                      Этап {index + 1} из {solution.steps.length}
                    </p>
                    <p className="mt-2 text-base text-foreground/90 sm:text-lg">{step.caption}</p>
                  </figcaption>
                  <div className="overflow-hidden rounded-2xl border border-border/40 bg-white shadow-[var(--shadow-soft)]">
                    <img
                      src={step.src}
                      alt={step.alt}
                      width={SOLUTION_IMAGE_SIZE.width}
                      height={SOLUTION_IMAGE_SIZE.height}
                      className="block h-auto w-full max-w-full"
                      loading={index === 0 ? "eager" : "lazy"}
                      decoding="async"
                    />
                  </div>
                </figure>
              </Reveal>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-8 sm:px-6 lg:px-8">
        <Reveal>
          <div className="glass overflow-hidden rounded-3xl p-8 sm:p-12">
            <Eyebrow>Результат</Eyebrow>
            <H2 className="mt-4 max-w-3xl">Что меняется для бизнеса</H2>
            <ul className="mt-8 grid gap-4 sm:grid-cols-2">
              {solution.outcomes.map((item) => (
                <li
                  key={item}
                  className="rounded-2xl border border-border/50 bg-background/30 p-5 text-base text-foreground/90"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
        <div className="glass relative overflow-hidden rounded-3xl p-8 text-center sm:p-14">
          <div className="pointer-events-none absolute -top-32 left-1/2 size-80 -translate-x-1/2 rounded-full bg-[color:var(--lime)]/20 blur-3xl" />
          <Eyebrow>Следующий шаг</Eyebrow>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
            Узнаёте свою ситуацию?
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
            Разберём, как похожий процесс устроен у вас, и определим, какой следующий шаг имеет смысл
            для вашего бизнеса.
          </p>
          <div className="mt-8 flex flex-col items-center gap-3">
            <CTAButton event="click_bot_solutions" size="lg">
              Пройти диагностику бизнеса
            </CTAButton>
          </div>
        </div>
      </section>
    </SiteLayout>
  );
}
