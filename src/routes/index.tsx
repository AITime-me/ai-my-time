import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { SiteLayout } from "@/components/SiteLayout";
import { CTAButton } from "@/components/CTAButton";
import { Reveal } from "@/components/Reveal";
import { Eyebrow, H2, Lead, GlassCard } from "@/components/SectionHeading";
import { HeroSchema } from "@/components/HeroSchema";
import { getFaq } from "@/lib/site.functions";
import {
  Users, Clock, Boxes, BarChart3, Globe, Bot, Headphones, Workflow, Database, Search,
  Building2, UserCircle, ShoppingBag, TrendingUp, Rocket, Layers, ChevronDown,
} from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Светлана Кузнецова — сайты и AI-помощники для малого бизнеса | AI My Time" },
      { name: "description", content: "Светлана Кузнецова, проект AI My Time: сайты, AI-помощники, боты и автоматизация для малого бизнеса, которому не хватает людей, времени и порядка." },
      { property: "og:title", content: "Светлана Кузнецова — AI My Time" },
      { property: "og:description", content: "Сайты, AI-помощники, боты и автоматизация для малого бизнеса" },
      { property: "og:url", content: "/" },
    ],
    links: [{ rel: "canonical", href: "/" }],
  }),
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: ["faq"], queryFn: () => getFaq() }),
  component: HomePage,
});

const pains = [
  { icon: Users, title: "Не хватает людей", text: "Хороший сотрудник не может быть везде и всегда." },
  { icon: Clock, title: "Не хватает времени", text: "Повторяющиеся вопросы и ручные действия съедают день." },
  { icon: Boxes, title: "Не хватает порядка", text: "Данные живут в разных местах, а собственник собирает картину по кусочкам." },
  { icon: BarChart3, title: "Не хватает аналитики", text: "Решения принимаются по ощущениям, а не по цифрам." },
];

const offers = [
  { icon: Globe, title: "Сайт с AI-помощником", text: "Не просто страница, а место, где клиент может понять предложение, задать вопрос и сделать следующий шаг." },
  { icon: Bot, title: "AI-консультант", text: "Отвечает на частые вопросы, уточняет запрос и помогает клиенту выбрать услугу или продукт." },
  { icon: Headphones, title: "AI-администратор", text: "Принимает обращения, собирает данные, помогает с записью, напоминает и передаёт информацию человеку." },
  { icon: Workflow, title: "Автоматизация процесса", text: "Берём повторяющуюся задачу и выводим её из ручного режима." },
  { icon: Database, title: "Мини-CRM или админка", text: "Место, где видны клиенты, заявки, статусы, доходы, расходы и история общения." },
  { icon: Search, title: "AI/digital-разбор", text: "Смотрим, где не хватает людей, времени и порядка, и составляем понятную карту внедрения." },
];

const steps = [
  { n: "01", title: "Разбираем процесс", text: "Где клиент приходит, где спрашивает, где теряется, где человек не успевает." },
  { n: "02", title: "Находим узкое место", text: "Что сейчас висит на собственнике, администраторе или менеджере." },
  { n: "03", title: "Собираем решение", text: "Сайт, помощник, бот, форма, таблица, CRM, уведомления или связка сервисов." },
  { n: "04", title: "Проверяем и донастраиваем", text: "AI не должен фантазировать. Он работает по базе знаний, сценарию и правилам." },
];

const audience = [
  { icon: Building2, title: "Локальный бизнес", text: "Салоны, студии, школы, сервисы, офлайн-точки." },
  { icon: UserCircle, title: "Эксперты и самозанятые", text: "Когда нужно упаковать услуги, ответы, запись и путь до заявки." },
  { icon: ShoppingBag, title: "Онлайн-магазины и товарный бизнес", text: "Когда клиенту нужна консультация, подбор и быстрый ответ." },
  { icon: TrendingUp, title: "Малый бизнес на потолке роста", text: "Когда есть команда, но процессы держатся на людях и ручном контроле." },
  { icon: Rocket, title: "Стартапы и новые идеи", text: "Когда нужно быстро собрать MVP, прототип или понятную первую версию." },
  { icon: Layers, title: "Услуги и сервисы", text: "Когда вы продаёте не товар, а заботу, экспертизу и время." },
];

const examples = [
  { title: "Сайт для студии услуг", task: "Показать услуги, ответить на частые вопросы, довести до записи.", stack: "Структура, тексты, форма заявки, AI-помощник, уведомления." },
  { title: "AI-администратор", task: "Разгрузить администратора от повторяющихся вопросов.", stack: "База знаний, сценарии, сбор данных, передача заявки человеку." },
  { title: "Мини-CRM", task: "Видеть заявки, клиентов, статусы и историю.", stack: "Админка, таблицы, фильтры, статусы, экспорт." },
  { title: "AI/digital-разбор", task: "Понять, с чего начать без цифровой паники.", stack: "Карта процессов, точки хаоса, список решений по приоритету." },
  { title: "Чек-лист или тест", task: "Вовлечь аудиторию и собрать ответы.", stack: "Вопросы, результат, форма контактов, сохранение ответов." },
  { title: "Аналитика для собственника", task: "Видеть, что происходит с заявками и клиентами.", stack: "Отчёты, ключевые показатели, повторяющиеся вопросы, точки улучшения." },
];

const tools = ["ChatGPT","Lovable","Cursor","React","Tailwind","Supabase","Telegram","n8n","Google Sheets","CRM","AI tools","Яндекс.Метрика","сайты","боты","автоматизации"];

function HomePage() {
  return (
    <SiteLayout>
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-30" />
        <div className="mx-auto grid max-w-7xl gap-10 px-4 pb-20 pt-14 sm:px-6 lg:grid-cols-12 lg:gap-12 lg:px-8 lg:pt-20">
          <div className="lg:col-span-7">
            <Eyebrow>Светлана Кузнецова · проект AI My Time</Eyebrow>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl md:text-6xl">
              Сайты и <span className="text-gradient">AI-помощники</span> для малого бизнеса, которому тесно в ручном управлении
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
              Я создаю сайты, AI-помощников, ботов и автоматизации для предпринимателей, которым не хватает людей, времени и порядка. Помогаю переложить повторяющиеся задачи из ручного режима в понятный digital-механизм.
            </p>
            <p className="mt-4 max-w-2xl text-sm text-muted-foreground/80">
              AI My Time — мой проект о технологиях, которые объясняются человеческим языком и работают на реальные процессы бизнеса.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <CTAButton event="click_bot_hero" size="lg">Обсудить задачу</CTAButton>
              <Link to="/cases" className="inline-flex items-center justify-center gap-2 rounded-full px-6 py-3.5 text-base glass hover:border-[color:var(--lime)]/40">
                Посмотреть решения
              </Link>
            </div>
          </div>
          <div className="lg:col-span-5">
            <HeroSchema />
          </div>
        </div>
      </section>

      {/* PAIN */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Главная боль</Eyebrow>
          <H2 className="mt-4 max-w-3xl">
            Когда бизнес держится на одном человеке, это не система. Это героизм на тонком льду.
          </H2>
          <Lead>
            Клиенты пишут вечером. Администратор не всегда успевает. Собственник снова контролирует всё руками. Заявки, вопросы, записи и отчёты расползаются по чатам, таблицам и памяти сотрудников. Я помогаю собрать из этого понятный рабочий механизм.
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

      {/* OFFERS */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Что я создаю</Eyebrow>
          <H2 className="mt-4">Что можно собрать для вашего бизнеса</H2>
        </Reveal>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {offers.map((o, i) => (
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

      {/* HOW */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Как это работает</Eyebrow>
          <H2 className="mt-4">Не начинаю с инструмента. Начинаю с задачи.</H2>
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
      </section>

      {/* NOT BOT FOR BOT */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Не «бот ради бота»</Eyebrow>
          <H2 className="mt-4 max-w-3xl">AI не заменяет хорошего сотрудника. Он убирает слой рутины до человека.</H2>
          <Lead>
            Сложные вопросы, эмоции, претензии и нестандартные ситуации остаются человеку. AI берёт повторяющееся: частые вопросы, первичный сбор данных, напоминания, заявки, простые консультации.
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
            <p className="text-xs uppercase tracking-wider text-[color:var(--lime)]">Хороший AI-помощник</p>
            <p className="mt-3 text-base text-foreground/90">
              «Здравствуйте! Похоже, у вас есть задача, в которой хочется навести больше порядка или найти более удобное решение. Подскажите, что сейчас вызывает больше всего вопросов?»
            </p>
          </GlassCard>
        </div>
      </section>

      {/* AUDIENCE */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Для кого</Eyebrow>
          <H2 className="mt-4">Кому это подойдёт</H2>
        </Reveal>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {audience.map((a, i) => (
            <Reveal key={a.title} delay={i * 0.04}>
              <GlassCard>
                <a.icon className="size-6 text-[color:var(--lime)]" />
                <h3 className="mt-4 text-lg font-semibold">{a.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{a.text}</p>
              </GlassCard>
            </Reveal>
          ))}
        </div>
      </section>

      {/* EXAMPLES */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Примеры решений</Eyebrow>
          <H2 className="mt-4">Какие решения можно собрать</H2>
        </Reveal>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {examples.map((e, i) => (
            <Reveal key={e.title} delay={i * 0.04}>
              <GlassCard>
                <h3 className="text-lg font-semibold">{e.title}</h3>
                <p className="mt-3 text-sm"><span className="text-muted-foreground">Задача: </span>{e.task}</p>
                <p className="mt-2 text-sm"><span className="text-muted-foreground">Что внутри: </span>{e.stack}</p>
              </GlassCard>
            </Reveal>
          ))}
        </div>
        <div className="mt-8">
          <Link to="/cases" className="inline-flex items-center gap-2 text-sm text-[color:var(--lime)] hover:underline">
            Все решения →
          </Link>
        </div>
      </section>

      {/* WHY ME */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Почему со мной</Eyebrow>
          <H2 className="mt-4 max-w-3xl">Почему ко мне идут не просто за сайтом</H2>
          <Lead className="max-w-3xl">
            Я смотрю на проект не как на набор блоков. Я смотрю на путь клиента, задачу бизнеса, слабые места процесса и ощущение от интерфейса.
          </Lead>
        </Reveal>
        <div className="mt-8 flex flex-wrap gap-2">
          {["предпринимательский опыт", "маркетинг", "SMM", "реклама", "визуал", "UX", "AI", "автоматизация", "веб-разработка"].map((t) => (
            <span key={t} className="rounded-full border border-border/60 bg-white/5 px-3.5 py-1.5 text-sm text-foreground/80">{t}</span>
          ))}
        </div>
        <p className="mt-6 max-w-3xl text-base text-foreground/80">
          Именно поэтому сайт не просто красиво висит в интернете. Он становится рабочей точкой: объясняет, ведёт, собирает заявки и помогает собственнику видеть картину.
        </p>
      </section>

      {/* AI MY TIME */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Reveal>
          <div className="glass overflow-hidden rounded-3xl p-8 sm:p-12">
            <Eyebrow>AI My Time</Eyebrow>
            <H2 className="mt-4 max-w-3xl">AI My Time — мой проект о технологиях без цифровой каши</H2>
            <Lead className="max-w-3xl">
              Это направление, в котором я собираю понятные digital-решения для малого бизнеса: сайты, AI-помощники, боты, автоматизация, мини-CRM, аналитика, приложения и рабочие инструменты.
            </Lead>
            <p className="mt-4 max-w-3xl text-base text-foreground/80">
              Главная идея — помочь бизнесу не держать всё на одном человеке, одной таблице и надежде, что клиент сам разберётся.
            </p>
          </div>
        </Reveal>
      </section>

      {/* TOOLS */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <Reveal>
          <Eyebrow>Инструменты</Eyebrow>
          <H2 className="mt-4">Инструменты</H2>
          <div className="mt-8 flex flex-wrap gap-2">
            {tools.map((t) => (
              <span key={t} className="rounded-full border border-border/60 bg-white/5 px-3.5 py-1.5 text-sm">{t}</span>
            ))}
          </div>
          <p className="mt-6 max-w-2xl text-sm text-muted-foreground">
            Но если честно, главный инструмент не стек. Главный инструмент — понять, где у бизнеса болит, и не лечить это красивой кнопкой.
          </p>
        </Reveal>
      </section>

      {/* FAQ */}
      <FaqSection />

      {/* MANIFESTO */}
      <section className="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 lg:px-8">
        <Reveal>
          <p className="text-2xl font-semibold tracking-tight sm:text-3xl md:text-4xl">
            Хороший сайт не просто висит в интернете. Он объясняет, ведёт, отвечает, собирает заявки и помогает бизнесу не жить на ручнике.
          </p>
          <p className="mt-6 text-muted-foreground">
            AI не должен притворяться человеком. Он должен быть полезным, быстрым и понятным помощником.
          </p>
        </Reveal>
      </section>

      {/* FINAL CTA */}
      <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8">
        <div className="glass overflow-hidden rounded-3xl p-8 sm:p-14 text-center relative">
          <div className="pointer-events-none absolute -top-32 left-1/2 size-80 -translate-x-1/2 rounded-full bg-[color:var(--lime)]/20 blur-3xl" />
          <Eyebrow>Старт</Eyebrow>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
            Хотите понять, что можно снять с ручного режима в вашем бизнесе?
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
            Начнём с короткого разбора. Посмотрим, где теряется время, где не хватает людей и какой первый digital-механизм можно собрать без цифрового ремонта на полгода.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <CTAButton event="click_bot_cases" size="lg">Обсудить задачу</CTAButton>
            <CTAButton event="click_bot_cases" size="lg" variant="secondary">Записаться на разбор</CTAButton>
          </div>
        </div>
      </section>
    </SiteLayout>
  );
}

function FaqSection() {
  const { data } = useSuspenseQuery({ queryKey: ["faq"], queryFn: () => getFaq() });
  const [open, setOpen] = useState<string | null>(null);
  const items = data ?? [];
  return (
    <section className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
      <Reveal>
        <Eyebrow>FAQ</Eyebrow>
        <H2 className="mt-4">Нормальные вопросы перед внедрением</H2>
      </Reveal>
      <div className="mt-8 space-y-2">
        {items.map((q) => {
          const isOpen = open === q.id;
          return (
            <div key={q.id} className="glass rounded-2xl">
              <button
                onClick={() => setOpen(isOpen ? null : q.id)}
                className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
              >
                <span className="text-base font-medium">{q.question}</span>
                <ChevronDown className={`size-5 shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`} />
              </button>
              {isOpen && (
                <div className="border-t border-border/40 px-5 py-4 text-sm text-muted-foreground">{q.answer}</div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// JSON-LD FAQPage for SEO
export const _faqJsonLd = "";