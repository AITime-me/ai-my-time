import { createFileRoute, Link } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, GlassCard, Lead } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { LegalNote } from "@/components/LegalNote";
import { useState } from "react";
import { z } from "zod";
import { useServerFn } from "@tanstack/react-start";
import { submitLead } from "@/lib/site.functions";
import { trackEvent } from "@/lib/analytics";
import { useSiteSettings } from "@/components/SiteSettingsProvider";
import { Send, Mail, Phone, CheckCircle2 } from "lucide-react";

export const Route = createFileRoute("/contacts")({
  head: () => ({
    meta: [
      { title: "Контакты — Светлана Кузнецова | AI My Time" },
      { name: "description", content: "Связаться со Светланой Кузнецовой и обсудить сайт, AI-помощника, бота, автоматизацию или digital-разбор бизнеса." },
      { property: "og:title", content: "Контакты — AI My Time" },
      { property: "og:description", content: "Обсудить задачу: сайт, AI-помощник, бот, автоматизация, разбор" },
      { property: "og:url", content: "/contacts" },
    ],
    links: [{ rel: "canonical", href: "/contacts" }],
  }),
  component: ContactsPage,
});

const schema = z.object({
  name: z.string().trim().min(2, "Укажите имя").max(100),
  phone_or_telegram: z.string().trim().max(100).optional().default(""),
  email: z.string().trim().email("Некорректный email").or(z.literal("")).optional().default(""),
  business_area: z.string().trim().max(200).optional().default(""),
  task: z.string().trim().max(200).optional().default(""),
  message: z.string().trim().max(2000).optional().default(""),
  consent: z.literal(true, { message: "Нужно согласие" }),
});

function ContactsPage() {
  const s = useSiteSettings();
  const submit = useServerFn(submitLead);
  const [done, setDone] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrors({});
    const fd = new FormData(e.currentTarget);
    const raw = {
      name: String(fd.get("name") || ""),
      phone_or_telegram: String(fd.get("phone_or_telegram") || ""),
      email: String(fd.get("email") || ""),
      business_area: String(fd.get("business_area") || ""),
      task: String(fd.get("task") || ""),
      message: String(fd.get("message") || ""),
      consent: fd.get("consent") === "on",
    };
    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
      const errs: Record<string, string> = {};
      parsed.error.issues.forEach((i) => { errs[i.path.join(".")] = i.message; });
      setErrors(errs);
      return;
    }
    setLoading(true);
    try {
      await submit({ data: parsed.data });
      trackEvent("submit_contact_form");
      setDone(true);
    } catch (err) {
      setErrors({ form: (err as Error).message || "Не удалось отправить" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <SiteLayout>
      <section className="mx-auto max-w-7xl px-4 pt-14 sm:px-6 lg:px-8">
        <Eyebrow>Контакты</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">Обсудить задачу</h1>
        <Lead className="max-w-3xl">
          Расскажите, где сейчас в бизнесе больше всего ручной работы. Я посмотрю, что можно упростить, передать AI или собрать в понятный digital-механизм.
        </Lead>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-5 lg:px-8">
        <div className="lg:col-span-2 space-y-4">
          <GlassCard>
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Основной способ</p>
            <p className="mt-3 text-base">Ответить на пару вопросов&nbsp; AI-помощнику — это быстрее&nbsp; и удобнее формы.</p>
            <div className="mt-5 flex flex-col gap-2">
              <CTAButton event="click_bot_hero" size="lg" className="self-start">Ответить на пару вопросов</CTAButton>
              <LegalNote />
            </div>
          </GlassCard>
          <GlassCard>
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Прямые контакты</p>
            <ul className="mt-4 space-y-3 text-sm">
              {s.telegram && (
                <li><a href={s.telegram} target="_blank" rel="noopener noreferrer" onClick={() => trackEvent("click_telegram")} className="inline-flex items-center gap-2 hover:text-[color:var(--lime)]"><Send className="size-4" /> Telegram</a></li>
              )}
              {s.email && (
                <li><a href={`mailto:${s.email}`} onClick={() => trackEvent("click_email")} className="inline-flex items-center gap-2 hover:text-[color:var(--lime)]"><Mail className="size-4" /> {s.email}</a></li>
              )}
              {s.phone && (
                <li><a href={`tel:${s.phone}`} className="inline-flex items-center gap-2 hover:text-[color:var(--lime)]"><Phone className="size-4" /> {s.phone}</a></li>
              )}
              {!s.telegram && !s.email && !s.phone && (
                <li className="text-muted-foreground">Контакты появятся скоро. Пока пишите через бота или форму.</li>
              )}
            </ul>
          </GlassCard>
        </div>

        <div className="lg:col-span-3">
          <GlassCard>
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Резервная форма</p>
            {done ? (
              <div className="mt-6 flex flex-col items-start gap-3">
                <CheckCircle2 className="size-8 text-[color:var(--lime)]" />
                <p className="text-lg font-medium">Спасибо! Заявка отправлена.</p>
                <p className="text-sm text-muted-foreground">Я посмотрю задачу и вернусь с ответом.</p>
              </div>
            ) : (
              <form onSubmit={onSubmit} className="mt-4 grid gap-4">
                <Field name="name" label="Имя" required error={errors.name} />
                <Field name="phone_or_telegram" label="Телефон или Telegram" />
                <Field name="email" label="Email" type="email" error={errors.email} />
                <Field name="business_area" label="Сфера бизнеса" />
                <Field name="task" label="Что хотите сделать" />
                <div>
                  <label className="text-sm text-muted-foreground">Комментарий</label>
                  <textarea name="message" rows={4} className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm outline-none focus:border-[color:var(--lime)]/60" />
                </div>
                <label className="flex items-start gap-2 text-sm text-muted-foreground">
                  <input type="checkbox" name="consent" className="mt-0.5 accent-[color:var(--lime)]" />
                  <span>Я согласен/согласна с <Link to="/privacy" className="underline">политикой конфиденциальности</Link>.</span>
                </label>
                {errors.consent && <p className="text-xs text-destructive">{errors.consent}</p>}
                {errors.form && <p className="text-xs text-destructive">{errors.form}</p>}
                <div className="mt-2 flex flex-col gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="inline-flex items-center justify-center gap-2 self-start rounded-full bg-[image:var(--gradient-primary)] px-6 py-3 text-sm font-medium text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)] disabled:opacity-60"
                  >
                    {loading ? "Отправляю…" : "Отправить заявку"}
                  </button>
                  <LegalNote />
                </div>
              </form>
            )}
          </GlassCard>
        </div>
      </section>
    </SiteLayout>
  );
}

function Field({ name, label, type = "text", required, error }: { name: string; label: string; type?: string; required?: boolean; error?: string }) {
  return (
    <div>
      <label className="text-sm text-muted-foreground">{label}{required && <span className="text-destructive"> *</span>}</label>
      <input
        name={name}
        type={type}
        required={required}
        className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm outline-none focus:border-[color:var(--lime)]/60"
      />
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}