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
import { adminDiagnostics } from "@/lib/admin-diag.functions";
import { getServices, getCases, getFaq, getLegalPage } from "@/lib/site.functions";
import { supabase } from "@/integrations/supabase/client";
import { LogOut, Trash2, Save, MessageSquare, ArrowLeft } from "lucide-react";

export const Route = createFileRoute("/_authenticated/admin")({
  head: () => ({ meta: [{ title: "Админка — AI My Time" }, { name: "robots", content: "noindex" }] }),
  component: AdminPage,
});

const TABS = ["Дашборд","Заявки","Диалоги","Услуги","Кейсы","FAQ","Контакты","Бот","Аналитика","Юр.страницы","SEO","Диагностика"] as const;
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
        {tab === "Диагностика" && <DiagnosticsTab />}
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

// ============ Dialogs tab ============

const CONV_STATUSES = ["new","in_progress","lead_created","waiting","closed","spam"] as const;
const CONV_STATUS_LABEL: Record<string, string> = {
  new: "новый", in_progress: "в работе", lead_created: "заявка создана",
  waiting: "ждём ответа", closed: "закрыт", spam: "спам",
};
const SOURCE_LABEL: Record<string, string> = {
  site: "сайт", telegram: "Telegram", vk: "VK", max: "MAX", other: "другой",
};

function DialogsTab() {
  const list = useServerFn(adminListConversations);
  const { data } = useQuery({ queryKey: ["bot_conversations"], queryFn: () => list() });
  const [selectedId, setSelectedId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    const v = sessionStorage.getItem("admin:openDialogId");
    if (v) sessionStorage.removeItem("admin:openDialogId");
    return v;
  });
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [contactQ, setContactQ] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  if (selectedId) return <ConversationView id={selectedId} onBack={() => setSelectedId(null)} />;

  const all = data ?? [];
  const sources = Array.from(new Set(all.map((c) => c.source))).filter(Boolean);
  const filtered = all.filter((c) => {
    if (statusFilter !== "all" && c.status !== statusFilter) return false;
    if (sourceFilter !== "all" && c.source !== sourceFilter) return false;
    if (contactQ) {
      const cq = contactQ.toLowerCase();
      const hay = `${c.user_email || ""} ${c.user_messenger || ""}`.toLowerCase();
      if (!hay.includes(cq)) return false;
    }
    if (q) {
      const qq = q.toLowerCase();
      const hay = `${c.user_name || ""} ${c.user_email || ""} ${c.user_messenger || ""} ${c.last_user_message || ""}`.toLowerCase();
      if (!hay.includes(qq)) return false;
    }
    return true;
  });
  const total = filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, totalPages);
  const rows = filtered.slice((safePage - 1) * pageSize, safePage * pageSize);
  const resetPage = () => setPage(1);

  return (
    <GlassCard>
      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); resetPage(); }}
          className="rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm"
        >
          <option value="all">Все статусы</option>
          {CONV_STATUSES.map((s) => <option key={s} value={s}>{CONV_STATUS_LABEL[s]}</option>)}
        </select>
        <select
          value={sourceFilter}
          onChange={(e) => { setSourceFilter(e.target.value); resetPage(); }}
          className="rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm"
        >
          <option value="all">Все источники</option>
          {sources.map((s) => <option key={s} value={s}>{SOURCE_LABEL[s] || s}</option>)}
        </select>
        <input
          placeholder="Email или Telegram"
          value={contactQ}
          onChange={(e) => { setContactQ(e.target.value); resetPage(); }}
          className="rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm"
        />
        <input
          placeholder="Поиск по имени, контакту, сообщению"
          value={q}
          onChange={(e) => { setQ(e.target.value); resetPage(); }}
          className="rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm"
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-muted-foreground">
              <th className="py-2 pr-3">Пользователь</th>
              <th className="py-2 pr-3">Контакт</th>
              <th className="py-2 pr-3">Источник</th>
              <th className="py-2 pr-3">Первое</th>
              <th className="py-2 pr-3">Последнее</th>
              <th className="py-2 pr-3">Сообщение</th>
              <th className="py-2 pr-3">Статус</th>
              <th className="py-2 pr-3">Заявка</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} className="border-t border-border/40 align-top">
                <td className="py-3 pr-3">{c.user_name || <span className="text-muted-foreground">—</span>}</td>
                <td className="py-3 pr-3 text-xs">
                  {c.user_email && <div>{c.user_email}</div>}
                  {c.user_messenger && <div className="text-muted-foreground">{c.user_messenger}</div>}
                </td>
                <td className="py-3 pr-3 text-xs">{SOURCE_LABEL[c.source] || c.source}</td>
                <td className="py-3 pr-3 text-xs text-muted-foreground">{c.first_message_at ? new Date(c.first_message_at).toLocaleString("ru-RU") : "—"}</td>
                <td className="py-3 pr-3 text-xs text-muted-foreground">{c.last_message_at ? new Date(c.last_message_at).toLocaleString("ru-RU") : "—"}</td>
                <td className="py-3 pr-3 text-xs max-w-[220px] truncate" title={c.last_user_message || ""}>{c.last_user_message || <span className="text-muted-foreground">—</span>}</td>
                <td className="py-3 pr-3 text-xs">{CONV_STATUS_LABEL[c.status] || c.status}</td>
                <td className="py-3 pr-3 text-xs">{c.lead_id ? "✓" : <span className="text-muted-foreground">—</span>}</td>
                <td className="py-3 text-right">
                  <button onClick={() => setSelectedId(c.id)} className="rounded-full glass px-3 py-1 text-xs">Открыть диалог</button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={9} className="py-6 text-center text-muted-foreground">{all.length === 0 ? "Пока нет диалогов. Здесь появятся переписки пользователей с AI-помощником." : "По заданным фильтрам ничего не найдено."}</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
        <div>Найдено: <b className="text-foreground">{total}</b>{total !== all.length ? <> из {all.length}</> : null}</div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={safePage <= 1}
            className="rounded-full glass px-3 py-1 disabled:opacity-40"
          >Назад</button>
          <span>Стр. {safePage} / {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={safePage >= totalPages}
            className="rounded-full glass px-3 py-1 disabled:opacity-40"
          >Вперёд</button>
        </div>
      </div>
    </GlassCard>
  );
}

function ConversationView({ id, onBack }: { id: string; onBack: () => void }) {
  const qc = useQueryClient();
  const get = useServerFn(adminGetConversation);
  const update = useServerFn(adminUpdateConversation);
  const del = useServerFn(adminDeleteConversation);
  const createLead = useServerFn(adminCreateLeadFromConversation);
  const { data, isLoading } = useQuery({ queryKey: ["bot_conversation", id], queryFn: () => get({ data: { id } }) });
  const [showLeadForm, setShowLeadForm] = useState(false);

  if (isLoading || !data) {
    return <div className="p-8 text-center text-muted-foreground">Загрузка…</div>;
  }
  const { conversation: c, messages, lead } = data;

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="size-4" /> К списку диалогов</button>

      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <GlassCard>
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Пользователь</p>
              <p className="mt-1 font-medium">{c.user_name || "—"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Контакт</p>
              <p className="mt-1">{c.user_email || "—"}</p>
              <p className="text-muted-foreground">{c.user_messenger || ""}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Источник</p>
              <p className="mt-1">{SOURCE_LABEL[c.source] || c.source}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Первое обращение</p>
              <p className="mt-1 text-xs">{c.first_message_at ? new Date(c.first_message_at).toLocaleString("ru-RU") : "—"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Последняя активность</p>
              <p className="mt-1 text-xs">{c.last_message_at ? new Date(c.last_message_at).toLocaleString("ru-RU") : "—"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Статус</p>
              <select
                value={c.status}
                onChange={async (e) => { await update({ data: { id: c.id, status: e.target.value } }); qc.invalidateQueries({ queryKey: ["bot_conversation", id] }); qc.invalidateQueries({ queryKey: ["bot_conversations"] }); }}
                className="mt-1 w-full rounded border border-border/60 bg-background/40 px-2 py-1 text-sm"
              >
                {CONV_STATUSES.map((s) => <option key={s} value={s}>{CONV_STATUS_LABEL[s]}</option>)}
              </select>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Связанная заявка</p>
              {lead ? (
                <div className="mt-1 space-y-1 text-xs">
                  <p>{lead.name} · {lead.status}</p>
                  <p className="text-muted-foreground">{lead.email || lead.phone_or_telegram}</p>
                  <button
                    onClick={() => { (window as unknown as { __adminGoLeads?: () => void }).__adminGoLeads?.(); }}
                    className="mt-1 rounded-full glass px-3 py-1 text-xs"
                  >Перейти к заявке</button>
                </div>
              ) : (
                <button onClick={() => setShowLeadForm((v) => !v)} className="mt-1 rounded-full bg-[image:var(--gradient-primary)] px-3 py-1 text-xs text-[color:var(--lime-foreground)]">
                  {showLeadForm ? "Отменить" : "Создать заявку"}
                </button>
              )}
            </div>

            {showLeadForm && !lead && (
              <form
                className="space-y-2 rounded-lg border border-border/60 bg-background/30 p-3"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  await createLead({ data: {
                    conversation_id: c.id,
                    name: String(f.get("name") || c.user_name || "—"),
                    email: String(f.get("email") || c.user_email || ""),
                    phone_or_telegram: String(f.get("phone_or_telegram") || c.user_messenger || ""),
                    task: String(f.get("task") || ""),
                    message: String(f.get("message") || ""),
                    source: `bot_dialog:${c.source}`,
                  } });
                  qc.invalidateQueries({ queryKey: ["bot_conversation", id] });
                  qc.invalidateQueries({ queryKey: ["bot_conversations"] });
                  qc.invalidateQueries({ queryKey: ["leads"] });
                  setShowLeadForm(false);
                }}
              >
                <AdminInput name="name" label="Имя" defaultValue={c.user_name || ""} />
                <AdminInput name="email" label="Email" defaultValue={c.user_email || ""} />
                <AdminInput name="phone_or_telegram" label="Telegram / телефон" defaultValue={c.user_messenger || ""} />
                <AdminTextarea name="task" label="Задача" defaultValue={messages.filter((m) => m.sender_type === "user").map((m) => m.message_text).join(" · ").slice(0, 500)} />
                <AdminTextarea name="message" label="Краткое содержание диалога" defaultValue={`Диалог #${c.id.slice(0, 8)} · сообщений: ${messages.length}`} />
                <button className="w-full rounded-full bg-[image:var(--gradient-primary)] px-3 py-1.5 text-xs text-[color:var(--lime-foreground)]">Создать</button>
              </form>
            )}

            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Заметка администратора</p>
              <textarea
                defaultValue={c.admin_note || ""}
                rows={4}
                onBlur={async (e) => { if (e.currentTarget.value !== (c.admin_note || "")) { await update({ data: { id: c.id, admin_note: e.currentTarget.value } }); qc.invalidateQueries({ queryKey: ["bot_conversation", id] }); } }}
                className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm"
              />
            </div>

            <button
              onClick={async () => { if (confirm("Удалить диалог? Сообщения будут удалены безвозвратно.")) { await del({ data: { id: c.id } }); qc.invalidateQueries({ queryKey: ["bot_conversations"] }); onBack(); } }}
              className="inline-flex items-center gap-2 text-xs text-destructive hover:opacity-80"
            ><Trash2 className="size-3" /> Удалить диалог</button>
          </div>
        </GlassCard>

        <GlassCard>
          <div className="max-h-[70vh] space-y-3 overflow-y-auto pr-2">
            {messages.length === 0 && <p className="py-6 text-center text-sm text-muted-foreground">В этом диалоге ещё нет сообщений.</p>}
            {messages.map((m) => {
              const isUser = m.sender_type === "user";
              const isBot = m.sender_type === "bot";
              return (
                <div key={m.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
                    isUser ? "bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)]"
                    : isBot ? "glass"
                    : "border border-amber-500/40 bg-amber-500/10"
                  }`}>
                    <p className="whitespace-pre-wrap">{m.message_text}</p>
                    <p className={`mt-1 text-[10px] ${isUser ? "text-[color:var(--lime-foreground)]/70" : "text-muted-foreground"}`}>
                      {m.sender_type === "user" ? "Пользователь" : m.sender_type === "bot" ? "Бот" : "Админ"}
                      {" · "}{new Date(m.created_at).toLocaleString("ru-RU")}
                      {m.message_channel ? ` · ${m.message_channel}` : ""}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}