import { createFileRoute, Link } from "@tanstack/react-router";

import { SiteLayout } from "@/components/SiteLayout";
import { CTAButton } from "@/components/CTAButton";
import { Reveal } from "@/components/Reveal";
import { Eyebrow, H2, Lead, GlassCard } from "@/components/SectionHeading";
import { HeroSchema } from "@/components/HeroSchema";

import {
  Database,
  MessagesSquare,
  Shuffle,
  Eye,
  Inbox,
  Workflow,
  Bot,
  Settings2,
  Cable,
  AppWindow,
  BarChart3,
  ChevronDown,
} from "lucide-react";
import { useState, type ReactNode } from "react";

const SEO_TITLE = "Автоматизация бизнес-процессов, CRM и AI для бизнеса | AI My Time";
const SEO_DESCRIPTION =
  "AI My Time проектирует и автоматизирует бизнес-процессы: CRM, AI-сотрудники, интеграции, сайты и цифровые сервисы для работы с клиентами, продажами и аналитикой.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: SEO_TITLE },
      { name: "description", content: SEO_DESCRIPTION },
      { property: "og:title", content: SEO_TITLE },
      { property: "og:description", content: SEO_DESCRIPTION },
      { property: "og:url", content: "/" },
    ],
    links: [{ rel: "canonical", href: "/" }],
  }),
  component: HomePage,
});

const pains = [
  {
    icon: Database,
    title: "«CRM есть, а легче не стало»",
    text: "Часть работы идёт в CRM, часть — в чатах, таблицах и заметках. Чтобы понять, что происходит с клиентом, всё равно приходится проверять вручную.",
  },
  {
    icon: MessagesSquare,
    title: "«Пока я с клиентом, мне пишут ещё»",
    text: "Обращения приходят одновременно из разных каналов. Скорость ответа зависит от того, кто сейчас свободен и где заметили сообщение.",
  },
  {
    icon: Shuffle,
    title: "«Систем много, а люди всё равно между ними бегают»",
    text: "Данные переносят вручную, статусы сверяют, а сотрудник фактически становится связующим звеном между сервисами.",
  },
  {
    icon: Eye,
    title: "«Хочу утром понимать, где моё внимание действительно нужно»",
    text: "Но вместо исключений собственнику приходится проверять обычную операционку: ответили ли, перезвонили ли, поставили ли задачу, что произошло со сделкой.",
  },
];

const steps = [
  {
    n: "01",
    title: "Восстанавливаем реальный путь процесса",
    text: "Не тот, который описан в регламенте, а тот, по которому работа идёт на самом деле: чаты, звонки, таблицы, CRM, ручные действия сотрудников, контроль собственника.",
  },
  {
    n: "02",
    title: "Находим разрывы и лишнюю ручную работу",
    text: "Где данные переносят вручную, следующий шаг нужно помнить, статус приходится уточнять, клиент ждёт или собственнику приходится вмешиваться.",
  },
  {
    n: "03",
    title: "Разделяем работу человека и системы",
    text: "Переговоры, нестандартные ситуации и решения остаются человеку. Повторяемые действия — зафиксировать, передать, напомнить, проверить, запустить следующий шаг — можно передать системе.",
  },
  {
    n: "04",
    title: "Собираем решение под конкретный процесс",
    text: "Это может быть CRM, автоматизация, интеграции, AI, сайт, бот, аналитика или специализированный цифровой сервис. Иногда нужен целый контур. Иногда достаточно исправить один участок, который постоянно создаёт потери.",
  },
];

const solutions: Array<{
  icon: typeof Inbox;
  title: string;
  text: string;
  /** Internal route — card becomes a link only when set and route exists. */
  to?: string;
  /** External/published URL — used only when set. */
  href?: string;
}> = [
  {
    icon: Inbox,
    title: "Собрать обращения и работу с клиентами в единый контур",
    text: "Когда заявки, история, статусы и следующие действия разбросаны между CRM, чатами и другими сервисами.",
  },
  {
    icon: Workflow,
    title: "Автоматизировать повторяющиеся действия",
    text: "Когда сотрудники вручную переносят данные, ставят задачи, отправляют типовые сообщения, проверяют статусы или готовят однотипные отчёты.",
  },
  {
    icon: Bot,
    title: "Подключить AI к бизнес-процессу",
    text: "Для консультаций, квалификации, сопровождения клиента, работы с информацией, регулярных операций и других задач, где AI может действовать по заданным правилам.",
  },
  {
    icon: Settings2,
    title: "Настроить и автоматизировать CRM",
    text: "Когда CRM уже есть или нужна бизнесу, но процессы внутри неё ещё не отражают реальную работу сотрудников и клиента.",
  },
  {
    icon: Cable,
    title: "Связать сервисы между собой",
    text: "Сайт, CRM, мессенджеры, телефония, формы, AI и другие системы — чтобы данные передавались автоматически, а человеку не приходилось быть «интеграцией» между ними.",
  },
  {
    icon: AppWindow,
    title: "Создать специализированный цифровой сервис",
    text: "Когда готовых инструментов недостаточно для конкретной функции бизнеса: личный кабинет, онлайн-сервис, внутренний интерфейс, аналитическая панель или другой инструмент под конкретную задачу.",
  },
  {
    icon: BarChart3,
    title: "Сделать процесс видимым для собственника",
    text: "Чтобы понимать не только, сколько заявок пришло, но и что произошло дальше: кто ответил, где остановилась сделка, что привело к продаже и где сейчас требуется внимание.",
  },
];

const articleCards: Array<{
  title: string;
  text: string;
  /** Published article URL/route — card is clickable only when set. */
  to?: string;
  href?: string;
}> = [
  {
    title: "CRM есть, а легче не стало",
    text: "Почему наличие CRM не гарантирует порядок в работе с клиентами и где обычно остаются разрывы.",
  },
  {
    title: "Заявка пришла. А что произошло с ней дальше?",
    text: "Разбор того, как теряется следующий шаг после первого обращения и что делает процесс управляемее.",
  },
  {
    title: "Что стоит автоматизировать, а что лучше оставить человеку",
    text: "Как отделить повторяемые действия от переговоров, решений и ситуаций, где нужен человек.",
  },
];

/** Makes a card clickable only when a real destination is provided — no placeholder URLs. */
function LinkableCard({
  to,
  href,
  className,
  children,
}: {
  to?: string;
  href?: string;
  className?: string;
  children: ReactNode;
}) {
  const card = <GlassCard className={className}>{children}</GlassCard>;
  if (to) {
    return (
      <Link
        to={to}
        className="block h-full rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--lime)]/50"
      >
        {card}
      </Link>
    );
  }
  if (href) {
    return (
      <a
        href={href}
        className="block h-full rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--lime)]/50"
      >
        {card}
      </a>
    );
  }
  return card;
}

const diagnosticSteps = [
  {
    n: "1",
    title: "Несколько вопросов о бизнесе",
    text: "Как приходят клиенты, как устроена работа с обращениями, продажами и текущими системами.",
  },
  {
    n: "2",
    title: "Уточнение ситуации",
    text: "AI задаёт дополнительные вопросы только там, где информации недостаточно для понимания процесса.",
  },
  {
    n: "3",
    title: "Первичный результат",
    text: "Вы получаете краткий разбор основной проблемы и понимаете, что имеет смысл обсуждать дальше.",
  },
];

const faqItems = [
  {
    id: "1",
    question: "Нужна ли растущему бизнесу CRM-система?",
    answer:
      "Когда растут обращения, каналы и команда, без единого контура работы с клиентами сложно сохранять скорость и контроль. CRM не создаёт спрос из воздуха, но помогает доводить больше обращений до продажи, возвращать клиентов и системно работать с повторными продажами — если отражает реальный процесс, а не существует отдельно от него.",
  },
  {
    id: "2",
    question: "Можно автоматизировать только один участок, а не весь бизнес сразу?",
    answer:
      "Да. Не всегда нужен большой проект. Иногда достаточно убрать один разрыв, который постоянно съедает время, деньги или контроль. Решение может затрагивать один участок или несколько связанных процессов — технологии выбираются под задачу.",
  },
  {
    id: "3",
    question: "Что можно передать AI-сотруднику?",
    answer:
      "AI-сотрудник может вести определённый участок процесса целиком: консультировать по базе знаний, задавать уточняющие вопросы, квалифицировать обращение, подбирать подходящие варианты, сопровождать клиента по заданному сценарию, напоминать о следующем действии, возвращаться к диалогу после паузы, фиксировать информацию и передавать данные в другие системы.\n\nОн может работать и внутри бизнеса: собирать и проверять информацию, готовить сводки и отчёты, отслеживать заданные события, выполнять регулярные операции и запускать следующие действия по правилам процесса.\n\nГраницы его работы задаются заранее: что он может делать самостоятельно, где требуется подтверждение и в какой момент задача или коммуникация должны перейти человеку.",
  },
  {
    id: "4",
    question: "Можно подключить AI и автоматизацию к уже существующим системам?",
    answer:
      "Да. Часто задача как раз в том, чтобы связать уже работающие сервисы — сайт, CRM, мессенджеры, формы, телефонию и другие системы — так, чтобы данные передавались автоматически, а человеку не приходилось быть «интеграцией» между ними.",
  },
  {
    id: "5",
    question: "Вы работаете только с продажами и CRM?",
    answer:
      "Нет. Продажи и CRM — частый контур, но не единственный. AI My Time проектирует и автоматизирует бизнес-процессы шире: AI-сотрудники, интеграции, сайты, цифровые сервисы, аналитика и специализированные инструменты под конкретную функцию бизнеса.",
  },
  {
    id: "6",
    question: "С чего начинается работа?",
    answer:
      "С разбора процесса, а не с выбора технологии. Сначала смотрим, как работа устроена сейчас, где возникают разрывы и лишняя ручная работа. Удобная точка старта — диагностика бизнеса: несколько вопросов о ситуации, уточнения там, где нужно, и первичный результат с понятным следующим шагом.",
  },
];

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqItems.map((q) => ({
    "@type": "Question",
    name: q.question,
    acceptedAnswer: { "@type": "Answer", text: q.answer },
  })),
};

function HomePage() {
  return (
    <SiteLayout>
      <HeroSection />
      <ProblemSection />
      <HowSection />
      <SolutionsSection />
      <AmoCrmSection />
      <ArticlesSection />
      <FounderSection />
      <DiagnosticsSection />
      <FaqSection />
      <FinalCtaSection />
    </SiteLayout>
  );
}

function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-grid opacity-30" />
      <div className="mx-auto grid max-w-7xl gap-10 px-4 pb-20 pt-14 sm:px-6 lg:grid-cols-12 lg:gap-12 lg:px-8 lg:pt-20">
        <div className="lg:col-span-7">
          <Eyebrow>AI My Time</Eyebrow>
          <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl md:text-6xl">
            Проектирование и <span className="text-gradient">автоматизация</span> бизнес-процессов
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
            AI My Time проектирует работу бизнеса с клиентами — от первого обращения до продажи,
            повторного контакта и аналитики.
          </p>
          <p className="mt-4 max-w-2xl text-base text-muted-foreground">
            Настраиваем CRM, связываем сайт, мессенджеры, AI и другие сервисы, автоматизируем
            повторяющиеся действия и оставляем человеку те участки, где действительно нужны его
            решения.
          </p>
          <div className="mt-8 flex flex-col gap-3">
            <div className="flex flex-wrap gap-3">
              <CTAButton event="click_bot_hero" size="lg">
                Пройти диагностику бизнеса
              </CTAButton>
              <a
                href="#how"
                className="inline-flex items-center justify-center gap-2 rounded-full px-6 py-3.5 text-base glass hover:border-[color:var(--lime)]/40"
              >
                Как мы работаем
              </a>
            </div>
          </div>
        </div>
        <div className="lg:col-span-5">
          <HeroSchema />
        </div>
      </div>
    </section>
  );
}

function ProblemSection() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>Проблема</Eyebrow>
        <H2 className="mt-4 max-w-3xl">
          Когда бизнес держится на одном человеке, это не система. Это героизм на тонком льду.
        </H2>
      </Reveal>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {pains.map((p, i) => (
          <Reveal key={p.title} delay={i * 0.05}>
            <GlassCard>
              <p.icon className="size-6 text-[color:var(--lime)]" />
              <h3 className="mt-4 text-lg font-semibold">{p.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{p.text}</p>
            </GlassCard>
          </Reveal>
        ))}
      </div>
      <Reveal>
        <div className="mt-10 max-w-3xl space-y-4 text-base text-muted-foreground sm:text-lg">
          <p>
            Ручная работа сама по себе не проблема. Проблема начинается там, где от памяти, внимания
            и присутствия конкретного человека зависит, сработает процесс или нет.
          </p>
          <p>
            Когда таких точек становится много, бизнес теряет не только время. Теряются обращения,
            следующие контакты, повторные продажи — а вместе с ними и нормальная управляемость.
          </p>
        </div>
      </Reveal>
    </section>
  );
}

function HowSection() {
  return (
    <section id="how" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>Как мы работаем</Eyebrow>
        <H2 className="mt-4 max-w-3xl">Сначала разбираем процесс. Потом выбираем технологию.</H2>
        <Lead className="max-w-3xl">
          Мы не начинаем с вопроса, какую CRM поставить, какого бота подключить или куда добавить
          AI. Сначала смотрим, как работа устроена сейчас: откуда приходит клиент, кто и когда
          отвечает, куда попадают данные, что должно произойти дальше, где возникает продажа и что
          происходит после неё.
        </Lead>
      </Reveal>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s, i) => (
          <Reveal key={s.n} delay={i * 0.05}>
            <GlassCard>
              <span className="font-mono text-sm text-[color:var(--lime)]">{s.n}</span>
              <h3 className="mt-3 text-lg font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{s.text}</p>
            </GlassCard>
          </Reveal>
        ))}
      </div>
      <Reveal>
        <div className="mt-12 glass overflow-hidden rounded-3xl p-8 sm:p-10">
          <p className="text-lg font-semibold tracking-tight sm:text-xl">
            Не бот ради бота. Не CRM ради CRM. Не AI ради AI.
          </p>
          <p className="mt-4 max-w-3xl text-base text-muted-foreground">
            Технология имеет смысл только тогда, когда делает процесс надёжнее, снимает лишнюю
            ручную работу или даёт бизнесу больше управляемости.
          </p>
        </div>
      </Reveal>
    </section>
  );
}

function SolutionsSection() {
  return (
    <section id="solutions" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>Решения</Eyebrow>
        <H2 className="mt-4 max-w-3xl">Что можно изменить в работе бизнеса</H2>
        <Lead className="max-w-3xl">
          Не всегда нужен большой проект. Иногда достаточно убрать один разрыв, который постоянно
          съедает время, деньги или контроль.
        </Lead>
      </Reveal>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {solutions.map((o, i) => (
          <Reveal key={o.title} delay={i * 0.04}>
            <LinkableCard to={o.to} href={o.href}>
              <div className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)]">
                  <o.icon className="size-5" />
                </span>
                <h3 className="text-lg font-semibold leading-snug">{o.title}</h3>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">{o.text}</p>
            </LinkableCard>
          </Reveal>
        ))}
      </div>
      <Reveal>
        <p className="mt-10 max-w-3xl text-base text-muted-foreground">
          Решение может затрагивать один участок или несколько связанных процессов. Технологии
          выбираются под задачу, а не наоборот.
        </p>
      </Reveal>
    </section>
  );
}

function AmoCrmSection() {
  return (
    <section
      id="amocrm"
      aria-labelledby="amocrm-heading"
      className="mx-auto max-w-7xl scroll-mt-24 px-4 py-16 sm:px-6 lg:px-8"
    >
      <Reveal>
        <div className="glass overflow-hidden rounded-3xl p-8 sm:p-12">
          <Eyebrow>amoCRM</Eyebrow>
          <H2 id="amocrm-heading" className="mt-4 max-w-3xl">
            Когда рынок становится сложнее, больше значения имеет то, что происходит после обращения
          </H2>
          <Lead className="max-w-3xl">
            На объём спроса бизнес может влиять не всегда. А вот то, какая часть обращений доходит
            до продажи, как ведётся клиент после первого контакта и возвращается ли он снова, — уже
            зона управления.
          </Lead>
          <p className="mt-6 max-w-3xl text-base font-medium text-foreground/90">
            CRM не создаёт спрос из воздуха. Но помогает бизнесу получать больше из того спроса и
            клиентской базы, которые уже есть: доводить больше обращений до продажи, возвращать
            клиентов и системно работать с повторными продажами.
          </p>
          <h3 className="mt-10 text-xl font-semibold tracking-tight sm:text-2xl">
            amoCRM — от точечной настройки до сложной автоматизации
          </h3>
          <p className="mt-4 max-w-3xl text-base text-muted-foreground">
            Поля, карточки, воронки, права, шаблоны, виджеты, автоматические действия, интеграции с
            сайтом, мессенджерами и другими сервисами, работа с клиентской базой и аналитикой.
          </p>
          <p className="mt-4 max-w-3xl text-base text-muted-foreground">
            Это не закрытый перечень возможностей. Задача может начинаться с одной настройки или
            затрагивать несколько связанных участков клиентского процесса.
          </p>
          <p className="mt-8 max-w-3xl text-base font-medium text-foreground/90">
            amoCRM должна поддерживать работу бизнеса, а не становиться ещё одной системой, которую
            сотрудники вынуждены обслуживать.
          </p>
        </div>
      </Reveal>
    </section>
  );
}

function ArticlesSection() {
  return (
    <section
      id="articles"
      aria-labelledby="articles-heading"
      className="mx-auto max-w-7xl scroll-mt-24 px-4 py-16 sm:px-6 lg:px-8"
    >
      <Reveal>
        <Eyebrow>Статьи и разборы AI My Time</Eyebrow>
        <H2 id="articles-heading" className="mt-4 max-w-3xl">
          Разбираем, как на самом деле работают бизнес-процессы
        </H2>
        <Lead className="max-w-3xl">
          Без абстрактных советов про цифровизацию. Показываем, где возникает проблема, почему она
          появляется и что в процессе можно изменить.
        </Lead>
      </Reveal>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {articleCards.map((a, i) => (
          <Reveal key={a.title} delay={i * 0.04}>
            <LinkableCard to={a.to} href={a.href} className="h-full">
              <h3 className="text-lg font-semibold">{a.title}</h3>
              <p className="mt-3 text-sm text-muted-foreground">{a.text}</p>
            </LinkableCard>
          </Reveal>
        ))}
      </div>
      <div className="mt-8">
        {/* Route for articles hub is not ready yet — avoid broken links */}
        <span
          className="inline-flex cursor-default items-center gap-2 text-sm text-muted-foreground/70"
          title="Раздел статей появится позже"
        >
          Все статьи →
        </span>
      </div>
    </section>
  );
}

function FounderSection() {
  return (
    <section
      id="founder"
      aria-labelledby="founder-heading"
      className="mx-auto max-w-7xl scroll-mt-24 px-4 py-16 sm:px-6 lg:px-8"
    >
      <Reveal>
        <div className="glass overflow-hidden rounded-3xl p-8 sm:p-12">
          <Eyebrow>О проекте</Eyebrow>
          <H2 id="founder-heading" className="mt-4 max-w-3xl">
            Бизнес-процессы — не только про технологии
          </H2>
          <p className="mt-4 text-lg font-medium text-foreground/90">
            Светлана Кузнецова — основатель AI My Time.
          </p>
          <div className="mt-6 max-w-3xl space-y-4 text-base text-muted-foreground">
            <p>
              В основе AI My Time — практический опыт управления бизнесом, маркетинга, работы с
              клиентским путём и цифровыми инструментами.
            </p>
            <p>
              Поэтому здесь не рассматривают CRM, AI, сайт или автоматизацию как отдельные продукты.
              Важно увидеть весь процесс целиком: как бизнес получает клиента, как с ним работает,
              где возникают потери, что можно передать системе и где решение должен принимать
              человек.
            </p>
            <p>
              Опыт в предпринимательстве, маркетинге и продвижении, UX, CRM, автоматизации, AI и
              веб-разработке позволяет смотреть на задачу не только со стороны технологии, а со
              стороны того, как она повлияет на работу бизнеса и результат.
            </p>
            <p className="font-medium text-foreground/90">
              Поэтому задача оценивается не только с точки зрения того, можно ли её технически
              реализовать, но и с точки зрения того, как решение будет работать для бизнеса,
              сотрудников и клиентов.
            </p>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

function DiagnosticsSection() {
  return (
    <section
      id="diagnostics"
      aria-labelledby="diagnostics-heading"
      className="mx-auto max-w-7xl scroll-mt-24 px-4 py-16 sm:px-6 lg:px-8"
    >
      <Reveal>
        <div className="glass overflow-hidden rounded-3xl p-8 sm:p-12">
          <Eyebrow>Диагностика</Eyebrow>
          <H2 id="diagnostics-heading" className="mt-4 max-w-3xl">
            Найти участок, который действительно стоит менять
          </H2>
          <Lead className="max-w-3xl">
            Диагностика AI My Time помогает разобраться, где в текущем процессе возникает разрыв и
            какую задачу имеет смысл решать в первую очередь.
          </Lead>
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {diagnosticSteps.map((s) => (
              <div key={s.n} className="rounded-2xl border border-border/50 bg-background/30 p-5">
                <span className="font-mono text-sm text-[color:var(--lime)]">{s.n}</span>
                <h3 className="mt-3 text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{s.text}</p>
              </div>
            ))}
          </div>
          <p className="mt-8 max-w-3xl text-base font-medium text-foreground/90">
            Это не длинная анкета и не бесконечная консультация с AI. Цель — быстро понять контекст
            и выйти на конкретную бизнес-задачу.
          </p>
          <div className="mt-8 flex flex-col items-start gap-2">
            <CTAButton event="click_bot_cases" size="lg">
              Пройти диагностику бизнеса
            </CTAButton>
            <p className="text-sm text-muted-foreground">Диагностика проходит в Telegram.</p>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

function FinalCtaSection() {
  return (
    <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
      <div className="glass relative overflow-hidden rounded-3xl p-8 text-center sm:p-14">
        <div className="pointer-events-none absolute -top-32 left-1/2 size-80 -translate-x-1/2 rounded-full bg-[color:var(--lime)]/20 blur-3xl" />
        <Eyebrow>Следующий шаг</Eyebrow>
        <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
          Не обязательно знать, какое решение вам нужно
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
          Достаточно понимать, что текущий процесс можно сделать лучше. Разберём ситуацию и
          определим, какой следующий шаг имеет смысл именно для вашего бизнеса.
        </p>
        <div className="mt-8 flex flex-col items-center gap-3">
          <div className="flex flex-wrap justify-center gap-3">
            <CTAButton event="click_bot_cases" size="lg">
              Пройти диагностику бизнеса
            </CTAButton>
            <CTAButton event="click_bot_cases" size="lg" variant="secondary">
              Обсудить задачу
            </CTAButton>
          </div>
        </div>
      </div>
    </section>
  );
}

function FaqSection() {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <section className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>FAQ</Eyebrow>
        <H2 className="mt-4">Частые вопросы</H2>
      </Reveal>
      <div className="mt-8 space-y-2">
        {faqItems.map((q) => {
          const isOpen = open === q.id;
          return (
            <div key={q.id} className="glass rounded-2xl">
              <button
                onClick={() => setOpen(isOpen ? null : q.id)}
                className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
              >
                <span className="text-base font-medium">{q.question}</span>
                <ChevronDown
                  className={`size-5 shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`}
                />
              </button>
              {isOpen && (
                <div className="space-y-3 border-t border-border/40 px-5 py-4 text-sm text-muted-foreground whitespace-pre-line">
                  {q.answer}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />
    </section>
  );
}
