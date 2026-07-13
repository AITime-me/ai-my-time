import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

async function assertAdmin(ctx: { supabase: ReturnType<typeof import("@supabase/supabase-js").createClient>; userId: string }) {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  const { data, error } = await supabaseAdmin.rpc("has_role", { _user_id: ctx.userId, _role: "admin" });
  if (error) throw new Error(error.message);
  if (!data) throw new Error("Forbidden");
}

export const checkIsAdmin = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const { data } = await supabaseAdmin.rpc("has_role", { _user_id: context.userId, _role: "admin" });
    return { isAdmin: !!data, userId: context.userId };
  });

export const adminGetSettings = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    await assertAdmin(context as never);
    const { data, error } = await context.supabase.from("site_settings").select("*").eq("id", 1).maybeSingle();
    if (error) throw new Error(error.message);
    return data;
  });

export const adminListLeads = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    await assertAdmin(context as never);
    const { data, error } = await context.supabase.from("leads").select("*").order("created_at", { ascending: false });
    if (error) throw new Error(error.message);
    return data ?? [];
  });

export const adminUpdateLead = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ id: z.string().uuid(), status: z.string().optional(), admin_comment: z.string().optional() }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const patch: { status?: string; admin_comment?: string } = {};
    if (data.status !== undefined) patch.status = data.status;
    if (data.admin_comment !== undefined) patch.admin_comment = data.admin_comment;
    const { error } = await context.supabase.from("leads").update(patch).eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminDeleteLead = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ id: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { error } = await context.supabase.from("leads").delete().eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminUpdateSettings = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({
    bot_link: z.string().optional(),
    bot_widget_enabled: z.boolean().optional(),
    bot_widget_text: z.string().optional(),
    main_cta_text: z.string().optional(),
    yandex_metrika_id: z.string().optional(),
    google_analytics_id: z.string().optional(),
    analytics_enabled: z.boolean().optional(),
    telegram: z.string().optional(),
    email: z.string().optional(),
    phone: z.string().optional(),
    site_title: z.string().optional(),
    site_description: z.string().optional(),
  }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { error } = await context.supabase.from("site_settings").update(data).eq("id", 1);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminUpdateLegal = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ type: z.enum(["privacy", "offer"]), title: z.string(), content: z.string() }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { error } = await context.supabase.from("legal_pages").update({ title: data.title, content: data.content }).eq("type", data.type);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminUpsertService = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({
    id: z.string().uuid().optional(),
    slug: z.string(),
    title: z.string(),
    h1: z.string().optional().nullable(),
    seo_title: z.string().optional().nullable(),
    seo_description: z.string().optional().nullable(),
    short_description: z.string().optional().nullable(),
    full_description: z.string().optional().nullable(),
    audience: z.string().optional().nullable(),
    includes: z.string().optional().nullable(),
    result: z.string().optional().nullable(),
    cta_text: z.string().optional().nullable(),
    sort_order: z.number().optional(),
    is_active: z.boolean().optional(),
  }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { error } = await context.supabase.from("services").upsert(data, { onConflict: "slug" });
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminUpsertCase = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({
    id: z.string().uuid().optional(),
    title: z.string(),
    category: z.string().optional().nullable(),
    status: z.string().optional().nullable(),
    task: z.string().optional().nullable(),
    solution: z.string().optional().nullable(),
    result: z.string().optional().nullable(),
    ecosystem_role: z.string().optional().nullable(),
    note: z.string().optional().nullable(),
    image_url: z.string().optional().nullable(),
    sort_order: z.number().optional(),
    is_active: z.boolean().optional(),
  }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { error } = data.id
      ? await context.supabase.from("cases").update(data).eq("id", data.id)
      : await context.supabase.from("cases").insert(data);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminDeleteCase = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ id: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { error } = await context.supabase.from("cases").delete().eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminUpsertFaq = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({
    id: z.string().uuid().optional(),
    question: z.string(),
    answer: z.string(),
    sort_order: z.number().optional(),
    is_active: z.boolean().optional(),
  }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { error } = data.id
      ? await context.supabase.from("faq").update(data).eq("id", data.id)
      : await context.supabase.from("faq").insert(data);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminDeleteFaq = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ id: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { error } = await context.supabase.from("faq").delete().eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

// ============ Bot conversations ============

export const adminListConversations = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    await assertAdmin(context as never);
    const { data, error } = await context.supabase
      .from("bot_conversations")
      .select("*")
      .order("last_message_at", { ascending: false, nullsFirst: false })
      .order("created_at", { ascending: false });
    if (error) throw new Error(error.message);
    const convs = data ?? [];
    if (convs.length === 0) return [] as Array<typeof convs[number] & { last_user_message: string | null }>;
    const ids = convs.map((c) => c.id);
    const { data: lastMsgs } = await context.supabase
      .from("bot_messages")
      .select("conversation_id, message_text, created_at, sender_type")
      .in("conversation_id", ids)
      .eq("sender_type", "user")
      .order("created_at", { ascending: false });
    const lastByConv = new Map<string, string>();
    for (const m of lastMsgs ?? []) {
      if (!lastByConv.has(m.conversation_id)) lastByConv.set(m.conversation_id, m.message_text);
    }
    return convs.map((c) => ({ ...c, last_user_message: lastByConv.get(c.id) ?? null }));
  });

export const adminGetConversation = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ id: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { data: conv, error } = await context.supabase.from("bot_conversations").select("*").eq("id", data.id).maybeSingle();
    if (error) throw new Error(error.message);
    if (!conv) throw new Error("Not found");
    const { data: messages, error: mErr } = await context.supabase
      .from("bot_messages").select("*").eq("conversation_id", data.id).order("created_at", { ascending: true });
    if (mErr) throw new Error(mErr.message);
    let lead = null;
    if (conv.lead_id) {
      const { data: l } = await context.supabase.from("leads").select("*").eq("id", conv.lead_id).maybeSingle();
      lead = l;
    }
    return { conversation: conv, messages: messages ?? [], lead };
  });

export const adminUpdateConversation = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({
    id: z.string().uuid(),
    status: z.string().optional(),
    admin_note: z.string().optional(),
  }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const patch: { status?: string; admin_note?: string } = {};
    if (data.status !== undefined) patch.status = data.status;
    if (data.admin_note !== undefined) patch.admin_note = data.admin_note;
    const { error } = await context.supabase.from("bot_conversations").update(patch).eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminDeleteConversation = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ id: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { error } = await context.supabase.from("bot_conversations").delete().eq("id", data.id);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const adminCreateLeadFromConversation = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({
    conversation_id: z.string().uuid(),
    name: z.string().min(1),
    email: z.string().optional().nullable(),
    phone_or_telegram: z.string().optional().nullable(),
    task: z.string().optional().nullable(),
    message: z.string().optional().nullable(),
    source: z.string().optional().nullable(),
  }).parse(d))
  .handler(async ({ data, context }) => {
    await assertAdmin(context as never);
    const { data: lead, error } = await context.supabase.from("leads").insert({
      name: data.name,
      email: data.email || null,
      phone_or_telegram: data.phone_or_telegram || null,
      task: data.task || null,
      message: data.message || null,
      source: data.source || "bot_dialog",
      conversation_id: data.conversation_id,
      status: "new",
    }).select("id").single();
    if (error) throw new Error(error.message);
    const { error: uErr } = await context.supabase.from("bot_conversations")
      .update({ lead_id: lead.id, status: "lead_created" }).eq("id", data.conversation_id);
    if (uErr) throw new Error(uErr.message);
    return { ok: true, lead_id: lead.id };
  });