import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, Lead } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { Sparkles } from "lucide-react";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "Светлана Кузнецова — AI/digital-специалист, проект AI My Time" },
      { name: "description", content: "Светлана Кузнецова: предприниматель, маркетолог и AI/digital-специалист. Создаю сайты, AI-помощников и автоматизацию для малого бизнеса." },
      { property: "og:title", content: "Светлана Кузнецова — AI My Time" },
      { property: "og:description", content: "AI/digital-специалист, проект AI My Time" },
      { property: "og:url", content: "/about" },
    ],
    links: [{ rel: "canonical", href: "/about" }],
  }),
  component: AboutPage,
});

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
          <div className="mt-8 flex flex-wrap gap-3">
            <CTAButton event="click_bot_hero" size="lg">Обсудить задачу</CTAButton>
          </div>
        </div>
        <div className="lg:col-span-5">
          <div className="glass relative aspect-square overflow-hidden rounded-3xl p-8">
            <div className="absolute inset-0 bg-grid opacity-30" />
            <div className="absolute -top-20 -right-20 size-64 rounded-full bg-[color:var(--lime)]/30 blur-3xl" />
            <div className="relative flex h-full flex-col justify-between">
              <div className="flex items-center gap-2">
                <span className="grid size-10 place-items-center rounded-xl bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)]">
                  <Sparkles className="size-5" />
                </span>
                <span className="text-sm uppercase tracking-wider text-muted-foreground">AI My Time</span>
              </div>
              <div>
                <p className="text-3xl font-semibold tracking-tight text-gradient">Светлана Кузнецова</p>
                <p className="mt-2 text-sm text-muted-foreground">AI / digital специалист · маркетолог · предприниматель</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-3 lg:px-8">
        <div className="glass rounded-2xl p-6">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Опыт</p>
          <ul className="mt-4 space-y-2 text-sm">
            {["предпринимательство","маркетинг","SMM","таргетированная реклама","визуал","UX","AI","автоматизация","сайты и приложения"].map((x) => (
              <li key={x} className="flex items-start gap-2"><span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-[color:var(--lime)]" />{x}</li>
            ))}
          </ul>
        </div>
        <div className="glass rounded-2xl p-6">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">Подход</p>
          <ol className="mt-4 space-y-3 text-sm">
            <li><span className="text-[color:var(--lime)]">01. </span>Сначала задача.</li>
            <li><span className="text-[color:var(--lime)]">02. </span>Потом сценарий.</li>
            <li><span className="text-[color:var(--lime)]">03. </span>Потом инструмент.</li>
            <li><span className="text-[color:var(--lime)]">04. </span>Потом визуал.</li>
          </ol>
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