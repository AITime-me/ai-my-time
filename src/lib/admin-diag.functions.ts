import { createServerFn } from "@tanstack/react-start";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

type Check = { name: string; ok: boolean; detail?: string; error?: string };
type TableProbe = {
  table: string;
  rls_enabled: boolean | null;
  policies: string[];
  grants_authenticated: string[];
  read: Check;
  write: Check;
};

async function probeRead(
  sb: { from: (t: string) => { select: (c: string) => { limit: (n: number) => Promise<{ error: { message: string } | null }> } } },
  table: string,
): Promise<Check> {
  try {
    const { error } = await sb.from(table).select("*").limit(1);
    if (error) return { name: "read", ok: false, error: error.message };
    return { name: "read", ok: true };
  } catch (e) {
    return { name: "read", ok: false, error: e instanceof Error ? e.message : String(e) };
  }
}

async function probeWrite(
  ctx: { supabase: { from: (t: string) => { update: (p: Record<string, unknown>) => { eq: (c: string, v: unknown) => Promise<{ error: { message: string } | null }> } } } },
  table: string,
  noop: { col: string; val: unknown; matchCol: string; matchVal: unknown },
): Promise<Check> {
  try {
    const { error } = await ctx.supabase.from(table).update({ [noop.col]: noop.val }).eq(noop.matchCol, noop.matchVal);
    if (error) return { name: "write", ok: false, error: error.message };
    return { name: "write", ok: true, detail: "обновление-заглушка прошло (то же значение)" };
  } catch (e) {
    return { name: "write", ok: false, error: e instanceof Error ? e.message : String(e) };
  }
}

export const adminDiagnostics = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");

    const out: {
      user: { id: string; email: string | null };
      isAdmin: boolean;
      env: Check[];
      functions: Check[];
      tables: TableProbe[];
    } = {
      user: { id: context.userId, email: (context.claims as { email?: string }).email ?? null },
      isAdmin: false,
      env: [],
      functions: [],
      tables: [],
    };

    // env
    out.env.push({ name: "SUPABASE_URL", ok: !!process.env.SUPABASE_URL });
    out.env.push({ name: "SUPABASE_PUBLISHABLE_KEY", ok: !!process.env.SUPABASE_PUBLISHABLE_KEY });
    out.env.push({ name: "SUPABASE_SERVICE_ROLE_KEY", ok: !!process.env.SUPABASE_SERVICE_ROLE_KEY });

    // is admin?
    const { data: adminFlag, error: adminErr } = await supabaseAdmin.rpc("has_role", { _user_id: context.userId, _role: "admin" });
    out.isAdmin = !!adminFlag;
    if (adminErr) out.functions.push({ name: "has_role (service_role вызов)", ok: false, error: adminErr.message });
    else out.functions.push({ name: "has_role (service_role вызов)", ok: true, detail: adminFlag ? "вы admin" : "вы НЕ admin" });

    if (!out.isAdmin) {
      return out;
    }

    // Привилегии через PostgREST недоступны напрямую — проверяем косвенно:
    // вызовем has_role от имени authenticated через user-scoped клиент.
    try {
      const { error } = await context.supabase.rpc("has_role", { _user_id: context.userId, _role: "admin" });
      if (error) out.functions.push({
        name: "has_role (вызов под authenticated)",
        ok: false,
        error: error.message,
        detail: "Если здесь permission denied — RLS-политики не могут проверить роль и любые UPDATE из админки падают. Нужен GRANT EXECUTE ON FUNCTION public.has_role(uuid, app_role) TO authenticated.",
      });
      else out.functions.push({ name: "has_role (вызов под authenticated)", ok: true });
    } catch (e) {
      out.functions.push({ name: "has_role (вызов под authenticated)", ok: false, error: e instanceof Error ? e.message : String(e) });
    }

    // Каталожная информация по таблицам
    const tables = [
      { table: "site_settings", noop: { col: "id", val: 1, matchCol: "id", matchVal: 1 } },
      { table: "legal_pages",   noop: null as null | { col: string; val: unknown; matchCol: string; matchVal: unknown } },
      { table: "services",      noop: null },
      { table: "cases",         noop: null },
      { table: "faq",           noop: null },
      { table: "leads",         noop: null },
      { table: "bot_conversations", noop: null },
      { table: "bot_messages",  noop: null },
    ];

    // pg_catalog недоступен через PostgREST. Делаем «честные» пробы read/write
    // от лица текущего пользователя — текст ошибки точно укажет причину.
    for (const t of tables) {
      const probe: TableProbe = {
        table: t.table,
        rls_enabled: null,
        policies: [],
        grants_authenticated: [],
        read: await probeRead(context.supabase as never, t.table),
        write: { name: "write", ok: true, detail: "пропущено (нет безопасной no-op)" },
      };

      // Безопасные no-op writes — пишем поле в то же значение, что лежит в БД.
      try {
        if (t.table === "site_settings") {
          const { data: row } = await context.supabase.from("site_settings").select("site_title").eq("id", 1).maybeSingle();
          if (row) probe.write = await probeWrite(context as never, "site_settings", { col: "site_title", val: row.site_title ?? "", matchCol: "id", matchVal: 1 });
        } else if (t.table === "legal_pages") {
          const { data: row } = await context.supabase.from("legal_pages").select("type,title").eq("type", "privacy").maybeSingle();
          if (row) probe.write = await probeWrite(context as never, "legal_pages", { col: "title", val: row.title, matchCol: "type", matchVal: "privacy" });
        } else if (t.table === "services") {
          const { data: row } = await context.supabase.from("services").select("id,title").limit(1).maybeSingle();
          if (row) probe.write = await probeWrite(context as never, "services", { col: "title", val: row.title, matchCol: "id", matchVal: row.id });
        } else if (t.table === "cases") {
          const { data: row } = await context.supabase.from("cases").select("id,title").limit(1).maybeSingle();
          if (row) probe.write = await probeWrite(context as never, "cases", { col: "title", val: row.title, matchCol: "id", matchVal: row.id });
        } else if (t.table === "faq") {
          const { data: row } = await context.supabase.from("faq").select("id,question").limit(1).maybeSingle();
          if (row) probe.write = await probeWrite(context as never, "faq", { col: "question", val: row.question, matchCol: "id", matchVal: row.id });
        } else if (t.table === "leads") {
          const { data: row } = await context.supabase.from("leads").select("id,status").limit(1).maybeSingle();
          if (row) probe.write = await probeWrite(context as never, "leads", { col: "status", val: row.status, matchCol: "id", matchVal: row.id });
          else probe.write = { name: "write", ok: true, detail: "нет строк для проверки" };
        } else if (t.table === "bot_conversations") {
          const { data: row } = await context.supabase.from("bot_conversations").select("id,status").limit(1).maybeSingle();
          if (row) probe.write = await probeWrite(context as never, "bot_conversations", { col: "status", val: row.status, matchCol: "id", matchVal: row.id });
          else probe.write = { name: "write", ok: true, detail: "нет строк для проверки" };
        } else if (t.table === "bot_messages") {
          const { data: row } = await context.supabase.from("bot_messages").select("id,message_text").limit(1).maybeSingle();
          if (row) probe.write = await probeWrite(context as never, "bot_messages", { col: "message_text", val: row.message_text, matchCol: "id", matchVal: row.id });
          else probe.write = { name: "write", ok: true, detail: "нет строк для проверки" };
        }
      } catch (e) {
        probe.write = { name: "write", ok: false, error: e instanceof Error ? e.message : String(e) };
      }

      out.tables.push(probe);
      void t.noop;
    }

    return out;
  });