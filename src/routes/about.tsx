import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, GlassCard, H2, Lead } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import aboutPhotoAsset from "@/assets/about-photo.png.asset.json";
import { absoluteUrl, SITE_URL } from "@/lib/site-url";

const SEO_TITLE = "О проекте AI My Time — проектирование и автоматизация бизнес-процессов";
const SEO_DESCRIPTION =
  "AI My Time проектирует и автоматизирует бизнес-процессы: CRM, AI, интеграции, сайты и цифровые сервисы. Светлана Кузнецова — основатель проекта.";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: SEO_TITLE },
      { name: "description", content: SEO_DESCRIPTION },
      { property: "og:title", content: SEO_TITLE },
      { property: "og:description", content: SEO_DESCRIPTION },
      { property: "og:url", content: absoluteUrl("/about") },
    ],
    links: [{ rel: "canonical", href: absoluteUrl("/about") }],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Organization",
          name: "AI My Time",
          url: SITE_URL,
          description: SEO_DESCRIPTION,
          founder: {
            "@type": "Person",
            name: "Светлана Кузнецова",
            jobTitle: "Основатель AI My Time",
          },
        }),
      },
    ],
  }),
  component: AboutPage,
});

const approachSteps = [
  {
    title: "Сначала разбираем, где в процессе возникает проблема",
    description:
      "Смотрим, где бизнес теряет обращения, время или контроль: в работе с клиентами, передаче данных, ответах, статусах или следующих шагах.",
  },
  {
    title: "Восстанавливаем реальный сценарий работы",
    description:
      "Разбираем, как устроена работа на практике: откуда приходит клиент, кто отвечает, куда попадают данные и где возникает разрыв.",
  },
  {
    title: "Отделяем работу человека и системы",
    description:
      "Переговоры и нестандартные решения остаются человеку. Повторяемые действия можно передать CRM, автоматизации, AI или связке сервисов.",
  },
  {
    title: "Собираем решение под конкретный процесс",
    description:
      "Иногда достаточно исправить один участок. Иногда нужен связанный контур: CRM, интеграции, сайт, бот, аналитика или специализированный цифровой сервис.",
  },
];

function AboutPage() {
  return (
    <SiteLayout>
      <section className="mx-auto max-w-7xl px-4 pb-10 pt-14 sm:px-6 sm:pb-12 lg:px-8 lg:pb-14">
        <Eyebrow>О проекте</Eyebrow>
        <h1 className="mt-5 max-w-4xl text-4xl font-semibold tracking-tight sm:text-5xl md:text-6xl">
          AI My Time — проектирование и автоматизация бизнес-процессов
        </h1>
        <Lead className="mt-5 max-w-3xl">
          Проект помогает бизнесу выстроить работу с клиентами и операциями так, чтобы процесс не
          держался на памяти, внимании и присутствии одного человека.
        </Lead>
        <div className="mt-6 max-w-3xl space-y-4 text-base text-foreground/85">
          <p>
            AI My Time не начинает с вопроса, какую технологию поставить. Сначала разбирается
            текущий процесс: откуда приходит обращение, что происходит дальше, где возникает
            продажа, повторный контакт и где появляются потери.
          </p>
          <p>
            Затем под задачу выбираются инструменты — CRM, автоматизация, интеграции, AI, сайт или
            специализированный цифровой сервис. Технология имеет смысл только тогда, когда делает
            процесс надёжнее и даёт больше управляемости.
          </p>
        </div>
        <div className="mt-8">
          <CTAButton event="click_bot_hero" size="lg" className="self-start">
            Пройти диагностику бизнеса
          </CTAButton>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-14 lg:px-8 lg:py-16">
        <Eyebrow>Подход</Eyebrow>
        <H2 className="mt-4 max-w-3xl">Как AI My Time подходит к задачам бизнеса</H2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 sm:gap-6 lg:grid-cols-4">
          {approachSteps.map((step, index) => (
            <GlassCard key={step.title}>
              <span className="text-xs uppercase tabular-nums tracking-normal text-[color:var(--lime)]">
                {`0${index + 1}`}
              </span>
              <h3 className="mt-3 text-base font-medium leading-snug">{step.title}</h3>
              <p className="mt-2 text-sm text-foreground/80">{step.description}</p>
            </GlassCard>
          ))}
        </div>
      </section>

      <section
        id="founder"
        aria-labelledby="founder-heading"
        className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-14 lg:px-8 lg:py-16"
      >
        <div className="glass overflow-hidden rounded-3xl p-6 sm:p-10 lg:p-12">
          <div className="grid gap-10 lg:grid-cols-12 lg:items-start">
            <div className="lg:col-span-7">
              <Eyebrow>Основатель</Eyebrow>
              <h2
                id="founder-heading"
                className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl"
              >
                Светлана Кузнецова — основатель AI My Time
              </h2>
              <div className="mt-6 space-y-4 text-base text-muted-foreground">
                <p>
                  В основе проекта — практический опыт управления бизнесом, маркетинга, работы с
                  клиентским путём и цифровыми инструментами.
                </p>
                <p>
                  Поэтому CRM, AI, сайт или автоматизация здесь не рассматриваются как отдельные
                  продукты сами по себе. Важно увидеть весь процесс: как бизнес получает клиента,
                  как с ним работает, где возникают потери и где решение должен принимать человек.
                </p>
                <p className="font-medium text-foreground/90">
                  Задача оценивается не только с точки зрения технической реализуемости, но и с
                  точки зрения того, как решение будет работать для бизнеса, сотрудников и клиентов.
                </p>
              </div>
              <ul className="mt-8 flex flex-wrap gap-2">
                {[
                  "предпринимательство",
                  "маркетинг",
                  "продвижение",
                  "UX",
                  "CRM",
                  "автоматизация",
                  "AI",
                  "веб-разработка",
                ].map((x) => (
                  <li
                    key={x}
                    className="rounded-full border border-border/60 bg-white/5 px-3.5 py-1.5 text-sm text-foreground/80"
                  >
                    {x}
                  </li>
                ))}
              </ul>
            </div>
            <div className="lg:col-span-5">
              <div className="relative aspect-[4/5] overflow-hidden rounded-3xl border border-border/40 bg-background/40">
                <img
                  src={aboutPhotoAsset.url}
                  alt="Светлана Кузнецова — основатель AI My Time"
                  className="h-full w-full object-cover"
                  loading="lazy"
                  decoding="async"
                />
              </div>
            </div>
          </div>
        </div>
      </section>
    </SiteLayout>
  );
}
