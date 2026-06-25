import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import aboutPhotoAsset from "@/assets/about-photo.png.asset.json";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "Об авторе AI My Time — Светлана Кузнецова" },
      { name: "description", content: "Светлана Кузнецова: предприниматель, маркетолог и AI/digital-специалист. Создаю сайты, AI-помощников и автоматизацию для малого бизнеса." },
      { property: "og:title", content: "Об авторе AI My Time — Светлана Кузнецова" },
      { property: "og:description", content: "AI/digital-специалист, проект AI My Time" },
      { property: "og:url", content: "/about" },
    ],
    links: [{ rel: "canonical", href: "/about" }],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Person",
          name: "Светлана Кузнецова",
          jobTitle: "AI/digital-специалист, предприниматель и маркетолог",
          worksFor: {
            "@type": "Organization",
            name: "AI My Time",
          },
          description: "Предприниматель, маркетолог и AI/digital-специалист. Создаёт сайты, AI-помощников и автоматизацию для малого бизнеса.",
          url: "/about",
        }),
      },
    ],
  }),
  component: AboutPage,
});

const approachSteps = [
  {
    title: "Сначала разбираем, где в бизнесе возникает проблема",
    description: "Анализируем, где бизнес теряет клиентов, заявки, время или деньги: в обработке заявок, на сайте, в коммуникации или внутри процессов.",
  },
  {
    title: "Потом анализируем реальные сценарии работы бизнеса",
    description: "Разбираем, как устроена работа: как приходят клиенты, кто и как отвечает, где возникают задержки или хаос.",
  },
  {
    title: "Подбираем подходящее цифровое решение",
    description: "Определяем, что нужно: сайт, AI-администратор, чат-бот, автоматизация или приложение для бизнеса.",
  },
  {
    title: "Собираем решение в рабочий цифровой инструмент",
    description: "Реализация выбранного решения, которое закрывает конкретную задачу бизнеса и снижает потери заявок и ручную нагрузку.",
  },
];

function AboutPage() {
  return (
    <SiteLayout>
      <section className="mx-auto grid max-w-7xl gap-10 px-4 pb-16 pt-14 sm:px-6 lg:grid-cols-12 lg:px-8">
        <div className="lg:col-span-7">
          <Eyebrow>Обо мне</Eyebrow>
          <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl md:text-6xl">Светлана Кузнецова</h1>
          <p className="mt-5 text-lg text-muted-foreground">
            Я Светлана Кузнецова. Предприниматель, маркетолог и AI/digital-специалист.
          </p>
          <div className="mt-6 space-y-4 text-base text-foreground/85">
            <p>
              Я сама развиваю локальный бизнес и знаю, как выглядит операционка изнутри: заявки, клиенты, запись, сотрудники, текучка, ручной контроль и вечное «надо бы всё систематизировать».
            </p>
            <p>
              Поэтому в проекте AI My Time я не продаю «бота ради бота» и не обещаю, что AI спасёт всё нажатием одной кнопки.
            </p>
            <p>
              Я смотрю, где бизнесу не хватает людей, времени и порядка, а потом собираю решение: сайт, AI-помощника, бота, автоматизацию, мини-CRM или другой digital-инструмент под конкретную задачу.
            </p>
          </div>
          <div className="mt-8 flex flex-col gap-3">
            <CTAButton event="click_bot_hero" size="lg" className="self-start">Обсудить задачу</CTAButton>
          </div>
        </div>
        <div className="lg:col-span-5">
          <div className="glass relative aspect-[4/5] overflow-hidden rounded-3xl">
            <img
              src={aboutPhotoAsset.url}
              alt="Светлана Кузнецова — AI/digital-специалист"
              className="h-full w-full object-cover"
              loading="lazy"
              decoding="async"
            />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">Подход</p>
        <h2 className="mt-4 max-w-3xl text-3xl font-semibold tracking-tight sm:text-4xl">
          Как я подхожу к задачам бизнеса
        </h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {approachSteps.map((step, index) => (
            <div key={step.title} className="glass rounded-2xl p-6">
              <span className="text-xs uppercase tracking-wider text-[color:var(--lime)]">0{index + 1}</span>
              <h3 className="mt-3 text-base font-medium leading-snug">{step.title}</h3>
              <p className="mt-2 text-sm text-foreground/80">{step.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:px-8">
        <div className="glass rounded-2xl p-6">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Опыт</p>
          <ul className="mt-4 space-y-2 text-sm">
            {["предпринимательство","маркетинг","SMM","таргетированная реклама","визуал","UX","AI","автоматизация","сайты и приложения"].map((x) => (
              <li key={x} className="flex items-start gap-2"><span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-[color:var(--lime)]" />{x}</li>
            ))}
          </ul>
        </div>
        <div className="glass rounded-2xl p-6">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Почему я понимаю малый бизнес</p>
          <p className="mt-4 text-sm text-foreground/85">
            Потому что сама знаю, как выглядит бизнес, где всё держится на собственнике, администраторе, таблице и надежде, что все всё помнят.
          </p>
        </div>
      </section>
    </SiteLayout>
  );
}