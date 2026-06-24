import { createFileRoute } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, GlassCard, Lead } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { ConsentCheckbox } from "@/components/ConsentCheckbox";
import { useState } from "react";
import { z } from "zod";
import { useServerFn } from "@tanstack/react-start";
import { submitLead } from "@/lib/site.functions";
import { trackEvent } from "@/lib/analytics";
import { useSiteSettings } from "@/components/SiteSettingsProvider";
import { Send, Mail, Phone, CheckCircle2, ArrowRight, Sparkles } from "lucide-react";

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
  phone_or_telegram: z.string().trim().min(3, "Укажите телефон или Telegram").max(100),
  email: z.string().trim().max(100).optional().default(""),
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
  const [step, setStep] = useState<1 | 2>(1);
  const [consent, setConsent] = useState(false);
  const [form, setForm] = useState({
    name: "",
    phone_or_telegram: "",
    business_area: "",
    task: "",
  });

  function update<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
    if (errors[key]) setErrors((e) => { const n = { ...e }; delete n[key]; return n; });
  }

  function onContinue() {
    const errs: Record<string, string> = {};
    if (form.name.trim().length < 2) errs.name = "Укажите имя";
    if (form.phone_or_telegram.trim().length < 3) errs.phone_or_telegram = "Укажите телефон или Telegram";
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setStep(2);
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrors({});
    if (!consent) {
      setErrors({ consent: "Поставьте галочку, чтобы подтвердить согласие на обработку персональных данных." });
      return;
    }
    const raw = {
      name: form.name,
      phone_or_telegram: form.phone_or_telegram,
      email: "",
      business_area: form.business_area,
      task: form.task,
      message: "",
      consent: true as const,
    };
    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
      const errs: Record<string, string> = {};
      parsed.error.issues.forEach((i) => { errs[i.path.join(".")] = i.message; });
      setErrors(errs);
      if (errs.name || errs.phone_or_telegram) setStep(1);
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
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Короткая форма</p>
            {done ? (
              <div className="mt-6 flex flex-col items-start gap-3">
                <CheckCircle2 className="size-8 text-[color:var(--lime)]" />
                <p className="text-lg font-medium">Спасибо! Заявка отправлена.</p>
                <p className="text-sm text-muted-foreground">Я посмотрю задачу и вернусь с ответом.</p>
              </div>
            ) : (
              <form onSubmit={onSubmit} className="mt-4 grid gap-4">
                <div className="flex items-start gap-3 rounded-2xl border border-border/40 bg-background/30 p-3">
                  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)]">
                    <Sparkles className="size-4" />
                  </span>
                  <p className="text-sm text-muted-foreground">
                    {step === 1
                      ? "Здравствуйте! Напишите, как я могу к&nbsp; Вам обращаться и где удобно продолжить диалог?"
                      : "Отлично. Расскажите пару слов о бизнесе — подберу подходящее решение."}
                  </p>
                </div>

                <Field
                  name="name"
                  label="Имя"
                  required
                  value={form.name}
                  onChange={(v) => update("name", v)}
                  error={errors.name}
                  autoComplete="name"
                />
                <Field
                  name="phone_or_telegram"
                  label="Телефон или Telegram"
                  required
                  value={form.phone_or_telegram}
                  onChange={(v) => update("phone_or_telegram", v)}
                  error={errors.phone_or_telegram}
                  placeholder="+7… или @username"
                />

                {step === 2 && (
                  <div className="grid gap-4 duration-300 animate-in fade-in slide-in-from-top-2">
                    <Field
                      name="business_area"
                      label="Сфера бизнеса"
                      value={form.business_area}
                      onChange={(v) => update("business_area", v)}
                      placeholder="Например, медицина, услуги, e-commerce"
                    />
                    <div>
                      <label className="text-sm text-muted-foreground">Что хотите улучшить или обсудить</label>
                      <textarea
                        name="task"
                        rows={3}
                        value={form.task}
                        onChange={(e) => update("task", e.target.value)}
                        placeholder="Коротко: что болит или что хотите запустить"
                        className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm outline-none focus:border-[color:var(--lime)]/60"
                      />
                    </div>
                  </div>
                )}

                {errors.form && <p className="text-xs text-destructive">{errors.form}</p>}

                <div className="mt-2 flex flex-col gap-3">
                  {step === 2 && (
                    <ConsentCheckbox
                      checked={consent}
                      onChange={(v) => {
                        setConsent(v);
                        if (v && errors.consent) {
                          setErrors((e) => { const n = { ...e }; delete n.consent; return n; });
                        }
                      }}
                      error={errors.consent}
                    />
                  )}
                  {step === 1 ? (
                    <button
                      type="button"
                      onClick={onContinue}
                      className="inline-flex items-center justify-center gap-2 self-start rounded-full bg-[image:var(--gradient-primary)] px-6 py-3 text-sm font-medium text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)]"
                    >
                      Продолжить <ArrowRight className="size-4" />
                    </button>
                  ) : (
                    <button
                      type="submit"
                      disabled={loading}
                      className="inline-flex items-center justify-center gap-2 self-start rounded-full bg-[image:var(--gradient-primary)] px-6 py-3 text-sm font-medium text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)] disabled:opacity-60"
                    >
                      {loading ? "Отправляю…" : "Отправить заявку"}
                    </button>
                  )}
                </div>
              </form>
            )}
          </GlassCard>
        </div>
      </section>
    </SiteLayout>
  );
}

function Field({
  name, label, type = "text", required, error, value, onChange, placeholder, autoComplete,
}: {
  name: string; label: string; type?: string; required?: boolean; error?: string;
  value: string; onChange: (v: string) => void; placeholder?: string; autoComplete?: string;
}) {
  return (
    <div>
      <label className="text-sm text-muted-foreground">{label}{required && <span className="text-destructive"> *</span>}</label>
      <input
        name={name}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm outline-none focus:border-[color:var(--lime)]/60"
      />
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}