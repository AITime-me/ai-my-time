import { createFileRoute, Link } from "@tanstack/react-router";

import { SiteLayout } from "@/components/SiteLayout";
import { CTAButton } from "@/components/CTAButton";
import { Reveal } from "@/components/Reveal";
import { Eyebrow, H2, Lead, GlassCard } from "@/components/SectionHeading";
import { HeroSchema } from "@/components/HeroSchema";

import {
  Users,
  Clock,
  Boxes,
  BarChart3,
  Globe,
  Bot,
  Headphones,
  Workflow,
  Database,
  Search,
  MessageSquareWarning,
  Inbox,
  Shuffle,
  CircleHelp,
  Gauge,
  ClipboardList,
  ChevronDown,
} from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AI My Time — сайты и AI для бизнеса" },
      {
        name: "description",
        content:
          "AI My Time: экспертная технологическая студия. Сайты, AI-помощники, боты и автоматизация для малого бизнеса, которому не хватает людей, времени и порядка.",
      },
      { property: "og:title", content: "AI My Time — сайты и AI для бизнеса" },
      {
        property: "og:description",
        content: "Сайты, AI-помощники, боты и автоматизация для малого бизнеса",
      },
      { property: "og:url", content: "/" },
    ],
    links: [{ rel: "canonical", href: "/" }],
  }),
  component: HomePage,
});

const pains = [
  {
    icon: Users,
    title: "Не хватает людей",
    text: "Хороший сотрудник не может быть везде и всегда.",
  },
  {
    icon: Clock,
    title: "Не хватает времени",
    text: "Повторяющиеся вопросы и ручные действия съедают день.",
  },
  {
    icon: Boxes,
    title: "Не хватает порядка",
    text: "Данные живут в разных местах, а собственник собирает картину по кусочкам.",
  },
  {
    icon: BarChart3,
    title: "Не хватает аналитики",
    text: "Решения принимаются по ощущениям, а не по цифрам.",
  },
];

const steps = [
  {
    n: "01",
    title: "Разбираем процесс",
    text: "Где клиент приходит, где спрашивает, где теряется, где человек не успевает.",
  },
  {
    n: "02",
    title: "Находим узкое место",
    text: "Что сейчас висит на собственнике, администраторе или менеджере.",
  },
  {
    n: "03",
    title: "Собираем решение",
    text: "Сайт, помощник, бот, форма, таблица, CRM, уведомления или связка сервисов — как инструменты под задачу.",
  },
  {
    n: "04",
    title: "Проверяем и донастраиваем",
    text: "AI не должен фантазировать. Он работает по базе знаний, сценарию и правилам.",
  },
];

/** Типовые ситуации бизнеса (problem-based), не сегменты аудитории. */
const situations = [
  {
    icon: MessageSquareWarning,
    title: "Заявки теряются между каналами",
    text: "Клиенты пишут в разные места, а ответы и статусы не собираются в один поток.",
  },
  {
    icon: Inbox,
    title: "Один человек держит весь поток",
    text: "Собственник или администратор снова контролирует всё руками — вечером и в выходные.",
  },
  {
    icon: Shuffle,
    title: "Процесс держится на ручном режиме",
    text: "Повторяющиеся вопросы, запись, напоминания и передача данных съедают день.",
  },
  {
    icon: CircleHelp,
    title: "Клиент не понимает следующий шаг",
    text: "Сайт или переписка рассказывают о компании, но не ведут к заявке или записи.",
  },
  {
    icon: Gauge,
    title: "Нет картины по цифрам",
    text: "Решения принимаются по ощущениям: непонятно, откуда приходят клиенты и где они отваливаются.",
  },
  {
    icon: ClipboardList,
    title: "Данные разъехались по таблицам и чатам",
    text: "История обращений, статусы и договорённости живут в разных местах.",
  },
];

const solutions = [
  {
    icon: Globe,
    title: "Сайт как рабочая точка",
    text: "Не просто страница, а место, где клиент понимает предложение, задаёт вопрос и делает следующий шаг.",
  },
  {
    icon: Bot,
    title: "AI-консультант",
    text: "Отвечает на частые вопросы, уточняет запрос и помогает клиенту выбрать услугу или продукт.",
  },
  {
    icon: Headphones,
    title: "AI-администратор",
    text: "Принимает обращения, собирает данные, помогает с записью, напоминает и передаёт информацию человеку.",
  },
  {
    icon: Workflow,
    title: "Автоматизация процесса",
    text: "Берём повторяющуюся задачу и выводим её из ручного режима — без автоматизации ради автоматизации.",
  },
  {
    icon: Database,
    title: "CRM и внутренний порядок",
    text: "Место, где видны клиенты, заявки, статусы и история общения — как инструмент управления, а не «ещё одна таблица».",
  },
  {
    icon: Search,
    title: "Диагностика и карта внедрения",
    text: "Смотрим, где не хватает людей, времени и порядка, и составляем понятный первый шаг.",
  },
];

const examples = [
  {
    title: "Сайты для бизнеса с заявками и SEO",
    text: "Создание сайтов, которые приводят клиентов, а не просто представляют компанию. Структура под SEO-запросы, продуманная логика конверсии, формы заявок, аналитика и возможность интеграции AI-решений.",
  },
  {
    title: "AI-администратор для бизнеса",
    text: "AI-ассистент, который отвечает клиентам, обрабатывает входящие заявки, ведёт диалог и выполняет роль цифрового сотрудника 24/7.",
  },
  {
    title: "Чат-боты и AI-боты для бизнеса",
    text: "Разработка чат-ботов для сайтов, Telegram и мессенджеров. Автоматизация общения, сбор заявок, запись клиентов и первичная обработка обращений.",
  },
  {
    title: "Автоматизация бизнеса на n8n",
    text: "Настройка автоматизации между сервисами: заявки, CRM, таблицы, уведомления, почта и аналитика. Снижение ручной работы и объединение всех процессов в единую цифровую систему.",
  },
  {
    title: "Приложения и цифровые продукты для бизнеса",
    text: "Разработка внутренних инструментов: мини-CRM, дашборды, системы учёта заявок, клиентские панели и бизнес-приложения под конкретные задачи.",
  },
  {
    title: "AI-разбор и диагностика бизнеса",
    text: "Анализ бизнес-процессов: где теряются заявки, где не хватает автоматизации, какие процессы требуют улучшения и цифровизации.",
  },
  {
    title: "OpenClaw Bot",
    text: "Разработка мощного AI-ассистента для собственника бизнеса: работает локально, интегрируется с сервисами и мессенджерами, автоматизирует рутину, работает с почтой, календарём, задачами, сообщениями и мониторингом сайтов.",
  },
  {
    title: "Настройка аналитики и Яндекс.Метрики",
    text: "Подключение аналитики, отслеживание заявок, источников трафика и поведения пользователей. Помогает бизнесу понимать, откуда приходят клиенты и где теряются заявки.",
  },
];

const founderTags = [
  "предпринимательский опыт",
  "маркетинг",
  "SMM",
  "реклама",
  "визуал",
  "UX",
  "AI",
  "автоматизация",
  "веб-разработка",
];

/**
 * Архив контента, убранного с рендера главной на этом этапе.
 * Не удалять: может понадобиться для founder / final CTA / контекста инструментов.
 */
const homeContentArchive = {
  tools: [
    "ChatGPT",
    "OpenAI",
    "Lovable",
    "Cursor",
    "Cloud Code",
    "React",
    "Tailwind",
    "Supabase",
    "Telegram",
    "n8n",
    "Google Sheets",
    "CRM",
    "AI tools",
    "Яндекс.Метрика",
    "сайты",
    "боты",
    "автоматизации",
  ],
  toolsIntro:
    "Не инструменты ради инструментов — а связка, которая помогает бизнесу работать проще.",
  toolsOutro:
    "Но если честно, главный инструмент не стек. Главный инструмент — понять, где у бизнеса болит, и не лечить это красивой кнопкой.",
  manifestoPrimary:
    "Хороший сайт не просто висит в интернете. Он объясняет, ведёт, отвечает, собирает заявки и помогает бизнесу не жить на ручнике.",
  manifestoSecondary:
    "AI не должен притворяться человеком. Он должен быть полезным, быстрым и понятным помощником.",
  legacyAudienceSegments: [
    { title: "Локальный бизнес", text: "Салоны, студии, школы, сервисы, офлайн-точки." },
    {
      title: "Эксперты и самозанятые",
      text: "Когда нужно упаковать услуги, ответы, запись и путь до заявки.",
    },
    {
      title: "Онлайн-магазины и товарный бизнес",
      text: "Когда клиенту нужна консультация, подбор и быстрый ответ.",
    },
    {
      title: "Малый бизнес на потолке роста",
      text: "Когда есть команда, но процессы держатся на людях и ручном контроле.",
    },
    {
      title: "Стартапы и новые идеи",
      text: "Когда нужно быстро собрать понятную первую версию продукта и проверить спрос.",
    },
    {
      title: "Услуги и сервисы",
      text: "Когда вы продаёте не товар, а заботу, экспертизу и время.",
    },
  ],
} as const;

function HomePage() {
  return (
    <SiteLayout>
      <HeroSection />
      <ProblemSection />
      <HowSection />
      <SituationsSection />
      <SolutionsSection />
      <AmoCrmSection />
      <CasesSection />
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
            Экспертная технологическая студия для бизнеса, которому тесно в{" "}
            <span className="text-gradient">ручном управлении</span>
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
            {/* PLACEHOLDER: финальный hero lead */}
            AI My Time помогает малому бизнесу собрать понятный digital-механизм: сайты,
            AI-помощники, боты, CRM и автоматизация — как инструменты под задачу, а не как самоцель.
          </p>
          <p className="mt-4 max-w-2xl text-sm text-muted-foreground/80">
            {/* PLACEHOLDER: краткое позиционирование студии */}
            Технологии объясняются человеческим языком и ставятся на реальные процессы бизнеса.
          </p>
          <div className="mt-8 flex flex-col gap-3">
            <div className="flex flex-wrap gap-3">
              <CTAButton event="click_bot_hero" size="lg">
                Обсудить задачу
              </CTAButton>
              <Link
                to="/cases"
                className="inline-flex items-center justify-center gap-2 rounded-full px-6 py-3.5 text-base glass hover:border-[color:var(--lime)]/40"
              >
                Посмотреть решения
              </Link>
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
        <Eyebrow>Узнавание проблемы</Eyebrow>
        <H2 className="mt-4 max-w-3xl">
          Когда бизнес держится на одном человеке, это не система. Это героизм на тонком льду.
        </H2>
        <Lead>
          Клиенты пишут вечером. Администратор не всегда успевает. Собственник снова контролирует
          всё руками. Заявки, вопросы, записи и отчёты расползаются по чатам, таблицам и памяти
          сотрудников. AI My Time помогает собрать из этого понятный рабочий механизм.
        </Lead>
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
    </section>
  );
}

function HowSection() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>Как AI My Time разбирает процесс</Eyebrow>
        <H2 className="mt-4">Не начинаем с инструмента. Начинаем с задачи.</H2>
        <Lead>
          Принцип подхода: не автоматизируем ради автоматизации и не ставим технологию первой в
          очереди выбора. Сначала процесс и узкое место — потом решение.
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

      {/* MERGE: бывший блок «Not bot for bot» — принцип подхода */}
      <div className="mt-12">
        <Reveal>
          <Eyebrow>Не технология ради технологии</Eyebrow>
          <H2 className="mt-4 max-w-3xl">
            AI не заменяет хорошего сотрудника. Он убирает слой рутины до человека.
          </H2>
          <Lead>
            Сложные вопросы, эмоции, претензии и нестандартные ситуации остаются человеку. AI берёт
            повторяющееся: частые вопросы, первичный сбор данных, напоминания, заявки, простые
            консультации.
          </Lead>
        </Reveal>
        <div className="mt-10 grid gap-4 lg:grid-cols-2">
          <GlassCard className="border-destructive/30">
            <p className="text-xs uppercase tracking-wider text-destructive/80">Плохой бот</p>
            <p className="mt-3 text-base text-foreground/80">
              «Здравствуйте. Ваш запрос принят. Мы предоставляем качественные услуги.»
            </p>
          </GlassCard>
          <GlassCard className="border-[color:var(--lime)]/40">
            <p className="text-xs uppercase tracking-wider text-[color:var(--lime)]">
              Хороший AI-помощник
            </p>
            <p className="mt-3 text-base text-foreground/90">
              «Здравствуйте! Похоже, у вас есть задача, в которой хочется навести больше порядка или
              найти более удобное решение. Подскажите, что сейчас вызывает больше всего вопросов?»
            </p>
          </GlassCard>
        </div>
      </div>
    </section>
  );
}

function SituationsSection() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>Типовые ситуации</Eyebrow>
        <H2 className="mt-4">С какими задачами чаще всего приходят</H2>
        <Lead>
          {/* PLACEHOLDER: вводный текст блока ситуаций */}
          Не сегменты «кто вы», а ситуации, в которых бизнесу тесно без системы.
        </Lead>
      </Reveal>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {situations.map((s, i) => (
          <Reveal key={s.title} delay={i * 0.04}>
            <GlassCard>
              <s.icon className="size-6 text-[color:var(--lime)]" />
              <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{s.text}</p>
            </GlassCard>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function SolutionsSection() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>Решения</Eyebrow>
        <H2 className="mt-4">Что можно собрать под задачу бизнеса</H2>
        <Lead>
          {/* PLACEHOLDER: акцент «инструменты под задачу» */}
          CRM, AI, сайты, боты, интеграции и аналитика — инструменты решения, а не первый уровень
          выбора.
        </Lead>
      </Reveal>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {solutions.map((o, i) => (
          <Reveal key={o.title} delay={i * 0.04}>
            <GlassCard>
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-lg bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)]">
                  <o.icon className="size-5" />
                </span>
                <h3 className="text-lg font-semibold">{o.title}</h3>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">{o.text}</p>
            </GlassCard>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/** Структурный placeholder: финальный copy блока amoCRM — позже. */
function AmoCrmSection() {
  return (
    <section
      id="amocrm"
      aria-labelledby="amocrm-heading"
      className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8"
    >
      <Reveal>
        <div className="glass overflow-hidden rounded-3xl p-8 sm:p-12">
          <Eyebrow>amoCRM</Eyebrow>
          <H2 id="amocrm-heading" className="mt-4 max-w-3xl">
            {/* PLACEHOLDER title */}
            Блок amoCRM
          </H2>
          <Lead className="max-w-3xl">
            {/* PLACEHOLDER body */}
            Здесь будет отдельный блок про работу AI My Time с amoCRM как инструментом под
            бизнес-задачи. Финальный текст пока не задан.
          </Lead>
          <p className="mt-4 text-sm text-muted-foreground/70">
            Structural placeholder — content TBD.
          </p>
        </div>
      </Reveal>
    </section>
  );
}

function CasesSection() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>Реальные системы</Eyebrow>
        <H2 className="mt-4">Примеры решений, которые собирает AI My Time</H2>
        <Lead>
          {/* PLACEHOLDER: связка с /cases */}
          Ниже — направления систем. Подробные кейсы и экосистема — на странице проектов.
        </Lead>
      </Reveal>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {examples.map((e, i) => (
          <Reveal key={e.title} delay={i * 0.04}>
            <GlassCard>
              <h3 className="text-lg font-semibold">{e.title}</h3>
              <p className="mt-3 text-sm text-muted-foreground">{e.text}</p>
            </GlassCard>
          </Reveal>
        ))}
      </div>
      <div className="mt-8">
        <Link
          to="/cases"
          className="inline-flex items-center gap-2 text-sm text-[color:var(--lime)] hover:underline"
        >
          Все решения →
        </Link>
      </div>
    </section>
  );
}

function FounderSection() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <div className="glass overflow-hidden rounded-3xl p-8 sm:p-12">
          <Eyebrow>Основатель проекта</Eyebrow>
          <H2 className="mt-4 max-w-3xl">Светлана Кузнецова — основатель AI My Time</H2>
          <Lead className="max-w-3xl">
            {/* PLACEHOLDER: роль founder, не «оказывает услуги» */}
            Источник предпринимательской и профессиональной экспертизы проекта: путь клиента, задача
            бизнеса, слабые места процесса и ощущение от интерфейса.
          </Lead>
          <div className="mt-8 flex flex-wrap gap-2">
            {founderTags.map((t) => (
              <span
                key={t}
                className="rounded-full border border-border/60 bg-white/5 px-3.5 py-1.5 text-sm text-foreground/80"
              >
                {t}
              </span>
            ))}
          </div>
          <p className="mt-6 max-w-3xl text-base text-foreground/80">
            Именно поэтому решения AI My Time — не набор блоков. Сайт, помощник или автоматизация
            становятся рабочей точкой: объясняют, ведут, собирают заявки и помогают собственнику
            видеть картину.
          </p>
          <p className="mt-4 max-w-3xl text-sm text-muted-foreground">
            {/* PLACEHOLDER: связка студии и founder */}
            AI My Time — самостоятельный проект и экспертная технологическая студия. Светлана
            Кузнецова — её основатель.
          </p>
        </div>
      </Reveal>
    </section>
  );
}

/** Структурный placeholder: финальный copy диагностики — позже. */
function DiagnosticsSection() {
  return (
    <section
      id="diagnostics"
      aria-labelledby="diagnostics-heading"
      className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8"
    >
      <Reveal>
        <div className="glass overflow-hidden rounded-3xl p-8 sm:p-12">
          <Eyebrow>Диагностика</Eyebrow>
          <H2 id="diagnostics-heading" className="mt-4 max-w-3xl">
            {/* PLACEHOLDER title */}
            Блок диагностики
          </H2>
          <Lead className="max-w-3xl">
            {/* PLACEHOLDER body */}
            Здесь будет блок про разбор процесса и первый шаг внедрения. Финальный текст пока не
            задан.
          </Lead>
          <div className="mt-8 flex flex-wrap gap-3">
            <CTAButton event="click_bot_cases" size="lg" variant="secondary">
              {/* PLACEHOLDER CTA label */}
              Записаться на разбор
            </CTAButton>
          </div>
          <p className="mt-4 text-sm text-muted-foreground/70">
            Structural placeholder — content TBD.
          </p>
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
        <Eyebrow>Старт</Eyebrow>
        <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
          Хотите понять, что можно снять с ручного режима в вашем бизнесе?
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
          Начнём с короткого разбора. Посмотрим, где теряется время, где не хватает людей и какой
          первый digital-механизм можно собрать без цифрового ремонта на полгода.
        </p>
        <div className="mt-8 flex flex-col items-center gap-3">
          <div className="flex flex-wrap justify-center gap-3">
            <CTAButton event="click_bot_cases" size="lg">
              Обсудить задачу
            </CTAButton>
            <CTAButton event="click_bot_cases" size="lg" variant="secondary">
              Записаться на разбор
            </CTAButton>
          </div>
        </div>
      </div>
    </section>
  );
}

const faqItems = [
  {
    id: "1",
    question: "Нужен ли AI для бизнеса или это просто тренд?",
    answer:
      "AI — это инструмент автоматизации бизнеса. Он нужен там, где есть заявки, клиенты и рутинные процессы: ответы, консультации, запись и обработка обращений.",
  },
  {
    id: "2",
    question: "Что делает AI-администратор для бизнеса?",
    answer:
      "AI-администратор для бизнеса не только отвечает на сообщения. Он может вести клиентскую базу, обрабатывать входящие заявки, консультировать клиентов и работать как цифровой сотрудник 24/7.",
  },
  {
    id: "3",
    question: "Можно ли автоматизировать обработку заявок в бизнесе?",
    answer:
      "Да. Заявки с сайта, мессенджеров и рекламы можно объединить в одну систему, чтобы они не терялись и обрабатывались без ручного контроля.",
  },
  {
    id: "4",
    question: "Чем сайт-визитка отличается от сайта для бизнеса?",
    answer:
      "Сайт-визитка — это просто информационная страница, которая редко приводит клиентов. Сайт для бизнеса — это инструмент с SEO-структурой, заявками, маркетингом и возможностью подключить AI и аналитику.",
  },
  {
    id: "5",
    question: "Нужен ли бизнесу чат-бот?",
    answer:
      "Чат-бот нужен при наличии потока клиентов. Он помогает отвечать 24/7, собирать заявки и снижать потерю клиентов вне рабочего времени.",
  },
  {
    id: "6",
    question: "Что делать, если бизнес теряет заявки?",
    answer:
      "Это значит, что нет выстроенной обработки заявок или автоматизации. Решается через сайт, AI-администратора или CRM-логику, где все обращения собираются в один поток.",
  },
  {
    id: "7",
    question: "Можно ли заменить менеджера AI-решением?",
    answer:
      "Частично да. AI может заменить первичную обработку заявок, ответы и запись клиентов. В бизнесах, где менеджер в основном принимает и распределяет заявки, это особенно эффективно.",
  },
  {
    id: "8",
    question: "Что входит в создание сайта для бизнеса с AI?",
    answer:
      "Это не только визуальная часть и SEO-структура. Это также маркетинговая логика, конверсионный сценарий, формы заявок, аналитика и возможность подключения AI-ассистента.",
  },
  {
    id: "9",
    question: "Подходит ли автоматизация для малого бизнеса?",
    answer:
      "Да. Особенно для малого бизнеса, где важно не терять заявки, ускорять обработку клиентов и снижать ручную нагрузку на сотрудников.",
  },
  {
    id: "10",
    question: "Что даёт внедрение AI и автоматизации в бизнес?",
    answer:
      "Бизнес перестаёт терять заявки с сайта и из мессенджеров, а работа с ними становится стабильной и управляемой даже при росте клиентов или нехватке сотрудников.",
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

function FaqSection() {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <section className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>FAQ</Eyebrow>
        <H2 className="mt-4">Частые вопросы перед внедрением</H2>
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
                <div className="border-t border-border/40 px-5 py-4 text-sm text-muted-foreground">
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
