import { Link } from "@tanstack/react-router";
import { ArrowDown, ArrowRight } from "lucide-react";

import type { DemandRadarContent, SolutionSlug } from "@/data/solutions";
import { Reveal } from "@/components/Reveal";
import { Eyebrow, GlassCard, H2 } from "@/components/SectionHeading";

export function DemandRadarSections({ content }: { content: DemandRadarContent }) {
  return (
    <>
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Процесс</Eyebrow>
          <H2 className="mt-4 max-w-3xl">{content.processTitle}</H2>
          <ol className="mt-10 flex flex-col items-stretch gap-0 md:flex-row md:flex-wrap md:items-center md:gap-x-2 md:gap-y-3">
            {content.processSteps.map((step, index) => (
              <li key={step} className="flex flex-col items-center md:flex-row md:items-center">
                <div className="w-full rounded-2xl border border-border/50 bg-background/30 px-4 py-4 text-center md:w-auto md:min-w-[10rem] md:max-w-[13rem]">
                  <span className="font-mono text-xs text-[color:var(--lime)]">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <p className="mt-2 text-sm font-medium leading-snug text-foreground/90">{step}</p>
                </div>
                {index < content.processSteps.length - 1 && (
                  <>
                    <ArrowDown
                      className="my-2 size-4 text-[color:var(--lime)] md:hidden"
                      aria-hidden
                    />
                    <ArrowRight
                      className="mx-2 hidden size-4 shrink-0 text-[color:var(--lime)] md:block"
                      aria-hidden
                    />
                  </>
                )}
              </li>
            ))}
          </ol>
        </Reveal>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Три шага</Eyebrow>
          <H2 className="mt-4 max-w-3xl">{content.triadTitle}</H2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {content.triadCards.map((card) => (
              <GlassCard key={card.title}>
                <h3 className="text-lg font-semibold">{card.title}</h3>
                <p className="mt-3 text-sm text-muted-foreground">{card.text}</p>
              </GlassCard>
            ))}
          </div>
        </Reveal>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Reveal>
          <div className="glass overflow-hidden rounded-3xl p-8 sm:p-12">
            <Eyebrow>Возможности</Eyebrow>
            <H2 className="mt-4 max-w-3xl">{content.searchTitle}</H2>
            <p className="mt-4 max-w-3xl text-base text-muted-foreground sm:text-lg">
              {content.searchIntro}
            </p>
            <ul className="mt-8 grid gap-3 sm:grid-cols-2">
              {content.searchExamples.map((item) => (
                <li
                  key={item}
                  className="rounded-2xl border border-border/50 bg-background/30 px-5 py-4 text-sm text-foreground/90"
                >
                  {item}
                </li>
              ))}
            </ul>
            <p className="mt-8 max-w-3xl text-base font-medium text-foreground/90">{content.searchNote}</p>
          </div>
        </Reveal>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Reveal>
          <div className="glass overflow-hidden rounded-3xl border border-[color:var(--lime)]/25 p-8 sm:p-12">
            <Eyebrow>Связка продуктов</Eyebrow>
            <H2 className="mt-4 max-w-3xl">{content.pairingTitle}</H2>
            <div className="mt-4 max-w-3xl space-y-3 text-base text-muted-foreground sm:text-lg">
              {content.pairingIntro.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </div>
            <p className="mt-6 text-base font-medium text-foreground/90">AI-агент может:</p>
            <ul className="mt-4 grid gap-2 sm:grid-cols-2">
              {content.pairingBullets.map((item) => (
                <li key={item} className="flex gap-2 text-sm text-muted-foreground">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-[color:var(--lime)]" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <div className="mt-8">
              <Link
                to="/solutions/$slug"
                params={{ slug: content.pairingLinkSlug as SolutionSlug }}
                className="inline-flex items-center gap-2 text-sm font-medium text-[color:var(--lime)] hover:underline"
              >
                {content.pairingLinkLabel}
              </Link>
            </div>
          </div>
        </Reveal>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Диалог</Eyebrow>
          <H2 className="mt-4 max-w-3xl">{content.dialogueTitle}</H2>
          <p className="mt-4 max-w-3xl text-base text-muted-foreground sm:text-lg">
            {content.dialogueIntro}
          </p>
          <p className="mt-4 max-w-3xl text-base text-foreground/90">{content.dialoguePrep}</p>
          <div className="mt-8 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
            {content.dialogueChain.map((step, index) => (
              <div key={step} className="flex items-center gap-2">
                <span className="rounded-full border border-[color:var(--lime)]/30 bg-[color:var(--lime)]/10 px-3 py-1.5 text-sm font-medium text-foreground/90">
                  {step}
                </span>
                {index < content.dialogueChain.length - 1 && (
                  <ArrowRight className="hidden size-4 text-[color:var(--lime)] sm:block" aria-hidden />
                )}
              </div>
            ))}
          </div>
          <div className="mt-8 max-w-3xl space-y-3 text-base text-muted-foreground">
            {content.dialogueFollowUp.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>
          <p className="mt-8 max-w-3xl rounded-2xl border border-border/50 bg-background/30 px-5 py-4 text-base font-medium text-foreground/90">
            {content.dialogueThesis}
          </p>
        </Reveal>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Reveal>
          <div className="rounded-3xl border border-border/50 bg-background/25 p-8 sm:p-10">
            <Eyebrow>{content.boundaryTitle}</Eyebrow>
            <p className="mt-4 max-w-3xl text-base text-muted-foreground sm:text-lg">
              {content.boundaryText}
            </p>
          </div>
        </Reveal>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Reveal>
          <div className="glass relative overflow-hidden rounded-3xl p-8 text-center sm:p-12">
            <div className="pointer-events-none absolute -top-24 left-1/2 size-64 -translate-x-1/2 rounded-full bg-[color:var(--lime)]/15 blur-3xl" />
            <Eyebrow>{content.formulaEyebrow}</Eyebrow>
            <H2 className="mt-4">{content.formulaTitle}</H2>
            <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">{content.formulaText}</p>
            <div className="mx-auto mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row sm:justify-center">
              {content.formulaLines.map((line) => (
                <p
                  key={line}
                  className="rounded-2xl border border-border/50 bg-background/40 px-4 py-3 text-sm font-medium text-foreground/90"
                >
                  {line}
                </p>
              ))}
            </div>
          </div>
        </Reveal>
      </section>
    </>
  );
}
