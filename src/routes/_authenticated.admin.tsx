import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, GlassCard } from "@/components/SectionHeading";
import {
  checkIsAdmin, adminListLeads, adminUpdateLead, adminDeleteLead,
  adminUpdateSettings, adminGetSettings, adminUpdateLegal, adminUpsertService,
  adminUpsertCase, adminDeleteCase, adminUpsertFaq, adminDeleteFaq,
  adminListConversations, adminGetConversation, adminUpdateConversation,
  adminDeleteConversation, adminCreateLeadFromConversation,
} from "@/lib/admin.functions";
import { getServices, getCases, getFaq, getLegalPage } from "@/lib/site.functions";
import { supabase } from "@/integrations/supabase/client";
import { LogOut, Trash2, Save, MessageSquare, ArrowLeft } from "lucide-react";

export const Route = createFileRoute("/_authenticated/admin")({
  head: () => ({ meta: [{ title: "Админка — AI My Time" }, { name: "robots", content: "noindex" }] }),
  component: AdminPage,
});

const TABS = ["Дашборд","Заявки","Диалоги","Услуги","Кейсы","FAQ","Контакты","Бот","Аналитика","Юр.страницы","SEO"] as const;
type Tab = typeof TABS[number];

function AdminPage() {
  const check = useServerFn(checkIsAdmin);
  const { data: gate, isLoading } = useQuery({ queryKey: ["isAdmin"], queryFn: () => check() });
  const [tab, setTab] = useState<Tab>("Дашборд");

  // Allow other tabs to open Dialogs tab with a specific conversation
  if (typeof window !== "undefined") {
    (window as unknown as { __adminOpenDialog?: (id: string) => void }).__adminOpenDialog = (id: string) => {
      sessionStorage.setItem("admin:openDialogId", id);
      setTab("Диалоги");
    };
  }

  if (isLoading) {
    return <SiteLayout><div className="p-12 text-center text-muted-foreground">Проверка доступа…</div></SiteLayout>;
  }
  if (!gate?.isAdmin) {
    return (
      <SiteLayout>
        <div className="mx-auto max-w-xl px-4 py-20 text-center">
          <h1 className="text-2xl font-semibold">Нет доступа</h1>
          <p className="mt-2 text-sm text-muted-foreground">Эта зона только для администраторов. Попросите назначить вам роль <code className="rounded bg-white/5 px-1.5 py-0.5">admin</code>.</p>
          <button onClick={async () => { await supabase.auth.signOut(); location.href = "/auth"; }} className="mt-6 rounded-full glass px-4 py-2 text-sm">Выйти</button>
        </div>
      </SiteLayout>
    );
  }

  return (
    <SiteLayout>
      <section className="mx-auto max-w-7xl px-4 pt-10 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div>
            <Eyebrow>Админка</Eyebrow>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">AI My Time · панель</h1>
          </div>
          <button onClick={async () => { await supabase.auth.signOut(); location.href = "/"; }} className="inline-flex items-center gap-2 rounded-full glass px-4 py-2 text-sm"><LogOut className="size-4" /> Выйти</button>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`rounded-full px-3.5 py-1.5 text-sm transition ${tab === t ? "bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)]" : "glass"}`}>
              {t}
            </button>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {tab === "Дашборд" && <DashboardTab />}
        {tab === "Заявки" && <LeadsTab />}
        {tab === "Диалоги" && <DialogsTab />}
        {tab === "Услуги" && <ServicesTab />}
        {tab === "Кейсы" && <CasesTab />}
        {tab === "FAQ" && <FaqTab />}
        {tab === "Контакты" && <SettingsTab kind="contacts" />}
        {tab === "Бот" && <SettingsTab kind="bot" />}
        {tab === "Аналитика" && <SettingsTab kind="analytics" />}
        {tab === "Юр.страницы" && <LegalTab />}
        {tab === "SEO" && <SettingsTab kind="seo" />}
      </section>
    </SiteLayout>
  );
}

function DashboardTab() {
  const list = useServerFn(adminListLeads);
  const { data } = useQuery({ queryKey: ["leads"], queryFn: () => list() });
  const leads = data ?? [];
  const now = new Date();
  const monthAgo = new Date(now.getTime() - 30 * 86400000);
  const monthCount = leads.filter((l) => new Date(l.created_at) > monthAgo).length;
  const byStatus = leads.reduce<Record<string, number>>((acc, l) => { acc[l.status] = (acc[l.status] || 0) + 1; return acc; }, {});

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <GlassCard><p className="text-xs uppercase tracking-wider text-muted-foreground">Новые заявки</p><p className="mt-3 text-3xl font-semibold">{byStatus["new"] || 0}</p></GlassCard>
      <GlassCard><p className="text-xs uppercase tracking-wider text-muted-foreground">За месяц</p><p className="mt-3 text-3xl font-semibold">{monthCount}</p></GlassCard>
      <GlassCard><p className="text-xs uppercase tracking-wider text-muted-foreground">Всего</p><p className="mt-3 text-3xl font-semibold">{leads.length}</p></GlassCard>
      <GlassCard className="md:col-span-3">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">По статусам</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {Object.entries(byStatus).map(([k, v]) => (
            <span key={k} className="rounded-full border border-border/60 bg-white/5 px-3 py-1 text-sm">{k}: <b>{v}</b></span>
          ))}
        </div>
      </GlassCard>
      <GlassCard className="md:col-span-3">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">Последние заявки</p>
        <ul className="mt-4 divide-y divide-border/40">
          {leads.slice(0, 5).map((l) => (
            <li key={l.id} className="py-3 text-sm">
              <p className="font-medium">{l.name} <span className="text-muted-foreground">· {new Date(l.created_at).toLocaleString("ru-RU")}</span></p>
              <p className="text-muted-foreground">{l.task || l.message}</p>
            </li>
          ))}
          {leads.length === 0 && <li className="py-3 text-sm text-muted-foreground">Пока нет заявок.</li>}
        </ul>
      </GlassCard>
    </div>
  );
}

const STATUSES = ["new","in_progress","contacted","waiting","scheduled","done","rejected","archive"];
const STATUS_LABEL: Record<string, string> = { new: "новая", in_progress: "в работе", contacted: "связались", waiting: "ждём ответа", scheduled: "консультация назначена", done: "выполнено", rejected: "отказ", archive: "архив" };

function LeadsTab() {
  const qc = useQueryClient();
  const list = useServerFn(adminListLeads);
  const update = useServerFn(adminUpdateLead);
  const del = useServerFn(adminDeleteLead);
  const { data } = useQuery({ queryKey: ["leads"], queryFn: () => list() });
  const [filter, setFilter] = useState<string>("all");
  const [q, setQ] = useState("");
  const rows = (data ?? []).filter((l) => (filter === "all" || l.status === filter) && (q === "" || JSON.stringify(l).toLowerCase().includes(q.toLowerCase())));

  return (
    <GlassCard>
      <div className="mb-4 flex flex-wrap gap-2">
        <select value={filter} onChange={(e) => setFilter(e.target.value)} className="rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm">
          <option value="all">Все статусы</option>
          {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
        </select>
        <input placeholder="Поиск…" value={q} onChange={(e) => setQ(e.target.value)} className="flex-1 min-w-[200px] rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead><tr className="text-muted-foreground"><th className="py-2 pr-3">Дата</th><th className="py-2 pr-3">Имя</th><th className="py-2 pr-3">Контакт</th><th className="py-2 pr-3">Задача</th><th className="py-2 pr-3">Статус</th><th></th></tr></thead>
          <tbody>
            {rows.map((l) => (
              <tr key={l.id} className="border-t border-border/40 align-top">
                <td className="py-3 pr-3 text-xs text-muted-foreground">{new Date(l.created_at).toLocaleString("ru-RU")}</td>
                <td className="py-3 pr-3">{l.name}</td>
                <td className="py-3 pr-3 text-xs">{l.phone_or_telegram}<br/>{l.email}</td>
                <td className="py-3 pr-3 text-xs">{l.task}<br/><span className="text-muted-foreground">{l.message}</span></td>
                <td className="py-3 pr-3">
                  <select value={l.status} onChange={async (e) => { await update({ data: { id: l.id, status: e.target.value } }); qc.invalidateQueries({ queryKey: ["leads"] }); }} className="rounded border border-border/60 bg-background/40 px-2 py-1 text-xs">
                    {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
                  </select>
                </td>
                <td className="py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {(l as { conversation_id?: string | null }).conversation_id ? (
                      <button title="Открыть диалог" onClick={() => { (window as unknown as { __adminOpenDialog?: (id: string) => void }).__adminOpenDialog?.((l as { conversation_id: string }).conversation_id); }} className="text-muted-foreground hover:opacity-80"><MessageSquare className="size-4" /></button>
                    ) : null}
                    <button onClick={async () => { if (confirm("Удалить?")) { await del({ data: { id: l.id } }); qc.invalidateQueries({ queryKey: ["leads"] }); } }} className="text-destructive hover:opacity-80"><Trash2 className="size-4" /></button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={6} className="py-6 text-center text-muted-foreground">Пусто</td></tr>}
          </tbody>
        </table>
      </div>
    </GlassCard>
  );
}

function ServicesTab() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["services"], queryFn: () => getServices() });
  const upsert = useServerFn(adminUpsertService);
  return (
    <div className="space-y-4">
      {(data ?? []).map((s) => (
        <GlassCard key={s.id}>
          <details>
            <summary className="cursor-pointer text-lg font-semibold">{s.title} <span className="text-xs text-muted-foreground">/{s.slug}</span></summary>
            <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={async (e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              await upsert({ data: {
                slug: s.slug,
                title: String(f.get("title")),
                short_description: String(f.get("short_description")),
                full_description: String(f.get("full_description")),
                audience: String(f.get("audience")),
                includes: String(f.get("includes")),
                result: String(f.get("result")),
                seo_title: String(f.get("seo_title")),
                seo_description: String(f.get("seo_description")),
                cta_text: String(f.get("cta_text")),
                is_active: f.get("is_active") === "on",
              }});
              qc.invalidateQueries({ queryKey: ["services"] });
              alert("Сохранено");
            }}>
              <AdminInput name="title" label="Название" defaultValue={s.title} />
              <AdminInput name="cta_text" label="Текст кнопки" defaultValue={s.cta_text || ""} />
              <AdminInput name="seo_title" label="SEO title" defaultValue={s.seo_title || ""} className="sm:col-span-2" />
              <AdminTextarea name="seo_description" label="SEO description" defaultValue={s.seo_description || ""} className="sm:col-span-2" />
              <AdminTextarea name="short_description" label="Краткое описание" defaultValue={s.short_description || ""} className="sm:col-span-2" />
              <AdminTextarea name="full_description" label="Полное описание" defaultValue={s.full_description || ""} className="sm:col-span-2" />
              <AdminTextarea name="audience" label="Кому подходит" defaultValue={s.audience || ""} />
              <AdminTextarea name="includes" label="Что входит" defaultValue={s.includes || ""} />
              <AdminTextarea name="result" label="Результат" defaultValue={s.result || ""} className="sm:col-span-2" />
              <label className="flex items-center gap-2 text-sm sm:col-span-2"><input type="checkbox" name="is_active" defaultChecked={s.is_active} /> Показывать на сайте</label>
              <button className="rounded-full bg-[image:var(--gradient-primary)] px-4 py-2 text-sm text-[color:var(--lime-foreground)] sm:col-span-2"><Save className="inline size-4" /> Сохранить</button>
            </form>
          </details>
        </GlassCard>
      ))}
    </div>
  );
}

function CasesTab() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["cases"], queryFn: () => getCases() });
  const upsert = useServerFn(adminUpsertCase);
  const del = useServerFn(adminDeleteCase);
  return (
    <div className="space-y-4">
      {(data ?? []).map((c) => (
        <GlassCard key={c.id}>
          <details>
            <summary className="cursor-pointer text-lg font-semibold">{c.title}</summary>
            <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={async (e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              await upsert({ data: {
                id: c.id,
                title: String(f.get("title")),
                category: String(f.get("category")),
                task: String(f.get("task")),
                solution: String(f.get("solution")),
                result: String(f.get("result")),
                is_active: f.get("is_active") === "on",
              }});
              qc.invalidateQueries({ queryKey: ["cases"] }); alert("Сохранено");
            }}>
              <AdminInput name="title" label="Название" defaultValue={c.title} className="sm:col-span-2" />
              <AdminInput name="category" label="Категория" defaultValue={c.category || ""} className="sm:col-span-2" />
              <AdminTextarea name="task" label="Задача" defaultValue={c.task || ""} />
              <AdminTextarea name="solution" label="Решение" defaultValue={c.solution || ""} />
              <AdminTextarea name="result" label="Результат" defaultValue={c.result || ""} className="sm:col-span-2" />
              <label className="flex items-center gap-2 text-sm sm:col-span-2"><input type="checkbox" name="is_active" defaultChecked={c.is_active} /> Показывать на сайте</label>
              <div className="flex gap-2 sm:col-span-2">
                <button className="rounded-full bg-[image:var(--gradient-primary)] px-4 py-2 text-sm text-[color:var(--lime-foreground)]">Сохранить</button>
                <button type="button" onClick={async () => { if (confirm("Удалить?")) { await del({ data: { id: c.id } }); qc.invalidateQueries({ queryKey: ["cases"] }); } }} className="rounded-full glass px-4 py-2 text-sm text-destructive">Удалить</button>
              </div>
            </form>
          </details>
        </GlassCard>
      ))}
    </div>
  );
}

function FaqTab() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["faq"], queryFn: () => getFaq() });
  const upsert = useServerFn(adminUpsertFaq);
  const del = useServerFn(adminDeleteFaq);
  return (
    <div className="space-y-3">
      {(data ?? []).map((q) => (
        <GlassCard key={q.id}>
          <form className="grid gap-3" onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            await upsert({ data: { id: q.id, question: String(f.get("question")), answer: String(f.get("answer")), is_active: f.get("is_active") === "on" }});
            qc.invalidateQueries({ queryKey: ["faq"] }); alert("Сохранено");
          }}>
            <AdminInput name="question" label="Вопрос" defaultValue={q.question} />
            <AdminTextarea name="answer" label="Ответ" defaultValue={q.answer} />
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="is_active" defaultChecked={q.is_active} /> Показывать</label>
            <div className="flex gap-2">
              <button className="rounded-full bg-[image:var(--gradient-primary)] px-4 py-2 text-sm text-[color:var(--lime-foreground)]">Сохранить</button>
              <button type="button" onClick={async () => { if (confirm("Удалить?")) { await del({ data: { id: q.id } }); qc.invalidateQueries({ queryKey: ["faq"] }); } }} className="rounded-full glass px-4 py-2 text-sm text-destructive">Удалить</button>
            </div>
          </form>
        </GlassCard>
      ))}
    </div>
  );
}

function SettingsTab({ kind }: { kind: "contacts" | "bot" | "analytics" | "seo" }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["admin_site_settings"], queryFn: () => adminGetSettings() });
  const update = useServerFn(adminUpdateSettings);
  if (!data) return null;

  type Field = [keyof NonNullable<typeof data>, string, "text" | "checkbox"];
  const fields: Record<string, Field[]> = {
    contacts: [["telegram","Telegram URL","text"],["email","Email","text"],["phone","Телефон","text"]],
    bot: [["bot_link","Ссылка на бота","text"],["bot_widget_text","Текст BotWidget","text"],["main_cta_text","Основной CTA","text"],["bot_widget_enabled","Включить BotWidget","checkbox"]],
    analytics: [["yandex_metrika_id","ID Яндекс.Метрики","text"],["google_analytics_id","ID Google Analytics","text"],["analytics_enabled","Включить аналитику","checkbox"]],
    seo: [["site_title","Название сайта","text"],["site_description","Описание сайта","text"]],
  };

  return (
    <GlassCard>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const patch: Record<string, unknown> = {};
        for (const [k,, t] of fields[kind]) {
          patch[k] = t === "checkbox" ? f.get(k) === "on" : String(f.get(k) || "");
        }
        await update({ data: patch as never });
        qc.invalidateQueries({ queryKey: ["admin_site_settings"] });
        qc.invalidateQueries({ queryKey: ["site_settings"] });
        qc.invalidateQueries({ queryKey: ["analytics_config"] });
        alert("Сохранено");
      }}>
        {fields[kind].map(([k, label, t]) => (
          t === "checkbox"
            ? <label key={k} className="flex items-center gap-2 text-sm sm:col-span-2"><input type="checkbox" name={k} defaultChecked={!!data[k]} /> {label}</label>
            : <AdminInput key={k} name={k} label={label} defaultValue={String(data[k] ?? "")} className="sm:col-span-2" />
        ))}
        <button className="rounded-full bg-[image:var(--gradient-primary)] px-4 py-2 text-sm text-[color:var(--lime-foreground)] sm:col-span-2">Сохранить</button>
      </form>
    </GlassCard>
  );
}

function LegalTab() {
  return (
    <div className="space-y-4">
      <LegalEditor type="privacy" />
      <LegalEditor type="offer" />
    </div>
  );
}

function LegalEditor({ type }: { type: "privacy" | "offer" }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["legal", type], queryFn: () => getLegalPage({ data: { type } }) });
  const update = useServerFn(adminUpdateLegal);
  if (!data) return null;
  return (
    <GlassCard>
      <form className="grid gap-3" onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        await update({ data: { type, title: String(f.get("title")), content: String(f.get("content")) } });
        qc.invalidateQueries({ queryKey: ["legal", type] }); alert("Сохранено");
      }}>
        <AdminInput name="title" label={type === "privacy" ? "Политика конфиденциальности" : "Договор оферты"} defaultValue={data.title} />
        <div>
          <label className="text-sm text-muted-foreground">Текст</label>
          <textarea name="content" rows={16} defaultValue={data.content} className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 font-mono text-xs" />
        </div>
        <button className="rounded-full bg-[image:var(--gradient-primary)] px-4 py-2 text-sm text-[color:var(--lime-foreground)] self-start">Сохранить</button>
        <p className="text-xs text-muted-foreground">Адаптируйте под реальные реквизиты и условия работы.</p>
      </form>
    </GlassCard>
  );
}

function AdminInput({ name, label, defaultValue, className }: { name: string; label: string; defaultValue?: string; className?: string }) {
  return (
    <div className={className}>
      <label className="text-xs uppercase tracking-wider text-muted-foreground">{label}</label>
      <input name={name} defaultValue={defaultValue} className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm" />
    </div>
  );
}
function AdminTextarea({ name, label, defaultValue, className }: { name: string; label: string; defaultValue?: string; className?: string }) {
  return (
    <div className={className}>
      <label className="text-xs uppercase tracking-wider text-muted-foreground">{label}</label>
      <textarea name={name} defaultValue={defaultValue} rows={3} className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm" />
    </div>
  );
}