import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, H2, Lead, GlassCard } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { Reveal } from "@/components/Reveal";
import { Check } from "lucide-react";

const TITLE = "Услуги AI My Time — сайты, боты и AI";
const DESCRIPTION = "Сайты для бизнеса с SEO, AI-администраторы, чат-боты, автоматизация на n8n, приложения для бизнеса, OpenClaw Bot и аналитика для малого бизнеса.";

export const Route = createFileRoute("/services/")({
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
      { property: "og:type", content: "website" },
      { property: "og:url", content: "/services" },
      { name: "twitter:title", content: TITLE },
      { name: "twitter:description", content: DESCRIPTION },
    ],
    links: [{ rel: "canonical", href: "/services" }],
    scripts: [
      {
        type: "application/ld+json",
        children: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "CollectionPage",
          name: "Услуги AI My Time",
          description: DESCRIPTION,
          url: "/services",
          hasPart: services.map((s) => ({
            "@type": "Service",
            name: s.title,
            description: s.description,
            provider: { "@type": "Organization", name: "AI My Time" },
          })),
        }),
      },
    ],
  }),
  component: ServicesIndex,
});

type Service = {
  title: string;
  description: string;
  includes: string[];
  cta: string;
  event: string;
};

const services: Service[] = [
  {
    title: "Сайты для бизнеса с заявками и SEO",
    description:
      "Создаю сайты, которые не просто красиво выглядят, а помогают бизнесу получать заявки. Структура строится с учётом SEO-запросов, маркетинговой логики, конверсии, форм заявок, аналитики и возможности подключить AI-помощника.",
    includes: [
      "структура сайта под семантическое ядро",
      "SEO-страницы и мета-теги",
      "продуманная маркетинговая цепочка",
      "формы заявок",
      "подключение аналитики",
      "подготовка к интеграции бота или AI-помощника",
    ],
    cta: "Хочу сайт для бизнеса",
    event: "click_bot_services_site",
  },
  {
    title: "AI-администратор для бизнеса",
    description:
      "AI-администратор отвечает клиентам, ведёт диалог, помогает с заявками, записью и первичной консультацией. Он может работать как цифровой сотрудник 24/7 и закрывать часть рутины, где бизнесу не хватает людей или времени.",
    includes: [
      "сценарии общения",
      "база знаний",
      "ответы на частые вопросы",
      "сбор заявок",
      "запись клиентов",
      "передача сложных вопросов человеку",
    ],
    cta: "Обсудить AI-администратора",
    event: "click_bot_services_admin",
  },
  {
    title: "Чат-боты и AI-боты для бизнеса",
    description:
      "Разрабатываю чат-ботов и AI-ботов для сайта, Telegram, мессенджеров и соцсетей. Они помогают отвечать клиентам, собирать заявки, вести запись, консультировать и не оставлять обращения без ответа.",
    includes: [
      "бот для сайта",
      "Telegram-бот",
      "бот для заявок",
      "AI-бот для консультаций",
      "сценарии диалога",
      "передача заявки менеджеру",
    ],
    cta: "Хочу бота для бизнеса",
    event: "click_bot_services_bots",
  },
  {
    title: "Автоматизация бизнеса на n8n",
    description:
      "Настраиваю автоматизацию процессов между сервисами: заявки, таблицы, CRM, уведомления, почта, боты, мессенджеры и аналитика. Это помогает убрать ручной перенос данных и сделать работу быстрее.",
    includes: [
      "автоматизация заявок",
      "связка сервисов",
      "уведомления",
      "интеграция с Google Sheets",
      "интеграция с CRM",
      "автоматизация почты и сообщений",
      "сценарии на n8n",
    ],
    cta: "Обсудить автоматизацию",
    event: "click_bot_services_n8n",
  },
  {
    title: "Приложения и цифровые продукты для бизнеса",
    description:
      "Создаю простые рабочие приложения под задачи бизнеса: мини-CRM, дашборды, панели заявок, учёт клиентов, внутренние инструменты и приложения для команды. Не «сложная система ради системы», а конкретный инструмент под рабочую задачу.",
    includes: [
      "мини-CRM",
      "учёт заявок",
      "клиентские базы",
      "панели администратора",
      "дашборды",
      "внутренние приложения",
      "инструменты для команды",
    ],
    cta: "Хочу приложение для бизнеса",
    event: "click_bot_services_apps",
  },
  {
    title: "AI-разбор и диагностика бизнеса",
    description:
      "Помогаю понять, где бизнес теряет заявки, время, клиентов или деньги. Разбираю путь клиента, обработку заявок, сайт, коммуникации, сотрудников и ручные процессы. После разбора понятно, что нужно делать первым: сайт, AI, автоматизацию или приложение.",
    includes: [
      "анализ текущего процесса",
      "точки потери заявок",
      "слабые места сайта",
      "сценарии общения с клиентами",
      "карта цифровых решений",
      "приоритетный план внедрения",
    ],
    cta: "Начать с разбора",
    event: "click_bot_services_audit",
  },
  {
    title: "OpenClaw Bot",
    description:
      "OpenClaw Bot — это мощный интеллектуальный AI-помощник собственника бизнеса, который работает локально и интегрируется с цифровыми сервисами, автоматизирует рутинные процессы, собирает и анализирует данные, а также выполняет реальные действия в цифровой среде бизнеса.",
    includes: [
      "интеграция с мессенджерами и сервисами",
      "автоматизация рутинных задач",
      "работа с почтой",
      "создание событий в календаре",
      "постановка задач",
      "ответы на сообщения",
      "мониторинг сайтов, чатов и источников информации",
      "сбор и анализ данных",
    ],
    cta: "Обсудить OpenClaw Bot",
    event: "click_bot_services_openclaw",
  },
  {
    title: "Настройка аналитики и Яндекс.Метрики",
    description:
      "Подключаю аналитику, чтобы бизнес видел, откуда приходят посетители, какие кнопки нажимают, где теряются заявки и какие каналы работают лучше. Это помогает принимать решения не «на ощущениях», а по данным.",
    includes: [
      "Яндекс.Метрика",
      "цели и события",
      "отслеживание кликов",
      "аналитика заявок",
      "источники трафика",
      "базовые отчёты",
      "подготовка к SEO-аналитике",
    ],
    cta: "Настроить аналитику",
    event: "click_bot_services_analytics",
  },
];

const choosers = [
  {
    title: "Если заявок мало",
    text: "Проверяем сайт, SEO, структуру, оффер и путь до заявки.",
  },
  {
    title: "Если заявок много, но их сложно вести",
    text: "Смотрим обработку, статусы, менеджеров, ботов и автоматизацию.",
  },
  {
    title: "Если не хватает сотрудников",
    text: "Подбираем AI-администратора, чат-бота или OpenClaw Bot под конкретный участок работы.",
  },
  {
    title: "Если всё разбросано по чатам и таблицам",
    text: "Собираем цифровой инструмент: мини-CRM, дашборд, приложение или связку сервисов.",
  },
];

function ServicesIndex() {
  return (
    <SiteLayout>
      {/* Hero */}
      <section className="mx-auto max-w-7xl px-4 pt-14 sm:px-6 lg:px-8">
        <Eyebrow>Услуги</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl md:text-6xl">
          Сайты, AI и автоматизация для бизнеса
        </h1>
        <Lead className="max-w-3xl">
          Я создаю digital-решения для малого бизнеса: сайты с заявками и SEO,
          AI-помощников, чат-ботов, автоматизацию на n8n, приложения и
          инструменты, которые помогают не терять заявки, быстрее работать с
          клиентами и снижать ручную нагрузку.
        </Lead>
        <p className="mt-6 max-w-3xl text-base text-muted-foreground">
          Не начинаю с вопроса «какой инструмент вам поставить». Сначала смотрю,
          где бизнес теряет заявки, клиентов, время или деньги. А потом подбираю
          решение: сайт, AI-администратор, чат-бот, автоматизацию, приложение
          или OpenClaw Bot.
        </p>
        <div className="mt-8 flex flex-col items-start gap-2">
          <CTAButton event="click_bot_services_hero" size="lg">
            Обсудить задачу
          </CTAButton>
        </div>
      </section>

      {/* Services cards */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Eyebrow>Что можно сделать</Eyebrow>
        <H2 className="mt-5">Список услуг</H2>
        <div className="mt-10 grid gap-5 lg:grid-cols-2">
          {services.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.04}>
              <GlassCard className="flex h-full flex-col">
                <h3 className="text-xl font-semibold sm:text-2xl">{s.title}</h3>
                <p className="mt-3 text-sm text-muted-foreground sm:text-base">
                  {s.description}
                </p>
                <div className="mt-5">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">
                    Что входит
                  </p>
                  <ul className="mt-3 space-y-2">
                    {s.includes.map((item) => (
                      <li key={item} className="flex items-start gap-2 text-sm">
                        <Check className="mt-0.5 size-4 shrink-0 text-[color:var(--lime)]" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="mt-6 flex flex-col gap-2">
                  <CTAButton event={s.event}>{s.cta}</CTAButton>
                </div>
              </GlassCard>
            </Reveal>
          ))}
        </div>
      </section>

      {/* How to choose */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Eyebrow>Как понять, что вам нужно</Eyebrow>
        <H2 className="mt-5">Не обязательно сразу знать, какое решение вам нужно</H2>
        <Lead className="max-w-3xl">
          Иногда бизнесу нужен не новый сайт, а нормальная обработка заявок.
          Иногда нужен AI-администратор. Иногда — автоматизация на n8n. А иногда
          достаточно разобрать текущий процесс и найти одно слабое место,
          которое мешает росту.
        </Lead>
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {choosers.map((c, i) => (
            <Reveal key={c.title} delay={i * 0.05}>
              <GlassCard className="h-full">
                <h3 className="text-lg font-semibold sm:text-xl">{c.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground sm:text-base">{c.text}</p>
              </GlassCard>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <GlassCard className="text-center">
          <H2>Хотите понять, что подойдёт вашему бизнесу?</H2>
          <Lead className="mx-auto">
            Опишите задачу в двух словах. Я посмотрю, что лучше выбрать: сайт,
            AI-помощника, автоматизацию, приложение или разбор.
          </Lead>
          <div className="mt-8 flex flex-col items-center gap-2">
            <CTAButton event="click_bot_services_final" size="lg">
              Обсудить задачу
            </CTAButton>
          </div>
        </GlassCard>
      </section>
    </SiteLayout>
  );
}