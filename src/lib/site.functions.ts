import { createServerFn } from "@tanstack/react-start";
import { createClient } from "@supabase/supabase-js";
import { z } from "zod";
import type { Database } from "@/integrations/supabase/types";

function publicClient() {
  return createClient<Database>(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_PUBLISHABLE_KEY!,
    { auth: { storage: undefined, persistSession: false, autoRefreshToken: false } },
  );
}

export const getSiteSettings = createServerFn({ method: "GET" }).handler(async () => {
  const sb = publicClient();
  const { data } = await sb
    .from("site_settings")
    .select(
      "bot_link,bot_widget_enabled,bot_widget_text,main_cta_text,yandex_metrika_id,google_analytics_id,analytics_enabled,telegram,email,phone,social_links,site_title,site_description,og_image",
    )
    .eq("id", 1)
    .maybeSingle();
  return data ?? null;
});

export const getServices = createServerFn({ method: "GET" }).handler(async () => {
  const sb = publicClient();
  const { data } = await sb
    .from("services")
    .select("*")
    .eq("is_active", true)
    .order("sort_order");
  return data ?? [];
});

export const getServiceBySlug = createServerFn({ method: "GET" })
  .inputValidator((d) => z.object({ slug: z.string() }).parse(d))
  .handler(async ({ data }) => {
    const sb = publicClient();
    const { data: row } = await sb
      .from("services")
      .select("*")
      .eq("slug", data.slug)
      .eq("is_active", true)
      .maybeSingle();
    return row;
  });

export const getCases = createServerFn({ method: "GET" }).handler(async () => {
  const sb = publicClient();
  const { data } = await sb
    .from("cases")
    .select("*")
    .eq("is_active", true)
    .order("sort_order");
  return data ?? [];
});

export const getFaq = createServerFn({ method: "GET" }).handler(async () => {
  const sb = publicClient();
  const { data } = await sb
    .from("faq")
    .select("*")
    .eq("is_active", true)
    .order("sort_order");
  return data ?? [];
});

export const getLegalPage = createServerFn({ method: "GET" })
  .inputValidator((d) => z.object({ type: z.enum(["privacy", "offer"]) }).parse(d))
  .handler(async ({ data }) => {
    const sb = publicClient();
    const { data: row } = await sb
      .from("legal_pages")
      .select("title,content,updated_at")
      .eq("type", data.type)
      .maybeSingle();
    return row;
  });

const leadSchema = z.object({
  name: z.string().trim().min(1).max(100),
  phone_or_telegram: z.string().trim().max(100).optional().default(""),
  email: z.string().trim().max(200).optional().default(""),
  business_area: z.string().trim().max(200).optional().default(""),
  task: z.string().trim().max(200).optional().default(""),
  message: z.string().trim().max(2000).optional().default(""),
  consent: z.literal(true),
});

export const submitLead = createServerFn({ method: "POST" })
  .inputValidator((d) => leadSchema.parse(d))
  .handler(async ({ data }) => {
    const sb = publicClient();
    const { error } = await sb.from("leads").insert({
      name: data.name,
      phone_or_telegram: data.phone_or_telegram || null,
      email: data.email || null,
      business_area: data.business_area || null,
      task: data.task || null,
      message: data.message || null,
      source: "contact_form",
      status: "new",
    });
    if (error) throw new Error(error.message);
    return { ok: true };
  });