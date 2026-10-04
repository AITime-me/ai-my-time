import { ConsultantRateLimiter } from "./limits.server";
import { decideCta, normalizeDialogue, sanitizeModelText } from "./policy.server";
import { buildSystemPrompt } from "./prompt.server";
import type { ConsultantErrorCode, ConsultantReply, ConsultantTurn } from "./shared";

const MAX_BODY_BYTES = 16 * 1024;
const CORE_TIMEOUT_MS = 20_000;
const CORE_PATH = "/internal/consultant/complete";
const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "[::1]"]);

export type ConsultantServerConfig = {
  coreUrl: string;
  coreSecret: string;
  allowedOrigins: Set<string>;
};

export type CoreCaller = (
  config: ConsultantServerConfig,
  payload: { system: string; messages: ConsultantTurn[] },
) => Promise<string>;

/** Server-only: reads process.env (never import.meta.env, which Vite may inline). */
export function readConsultantConfig(env: NodeJS.ProcessEnv = process.env): ConsultantServerConfig | null {
  const coreUrl = env.CONSULTANT_CORE_URL?.trim();
  const coreSecret = env.CONSULTANT_CORE_SECRET?.trim();
  if (!coreUrl || !coreSecret) return null;
  let parsed: URL;
  try {
    parsed = new URL(coreUrl);
  } catch {
    return null;
  }
  // The shared secret may only travel to the local Core over loopback.
  if (parsed.protocol !== "http:" || !LOOPBACK_HOSTS.has(parsed.hostname)) return null;

  const allowedOrigins = new Set<string>();
  for (const raw of [env.SITE_URL, ...(env.CONSULTANT_ALLOWED_ORIGINS ?? "").split(",")]) {
    const value = raw?.trim();
    if (!value) continue;
    try {
      const origin = new URL(value);
      allowedOrigins.add(origin.origin);
      if (origin.protocol === "https:" && !origin.hostname.startsWith("www.")) {
        allowedOrigins.add(`${origin.protocol}//www.${origin.host}`);
      }
    } catch {
      // ignore malformed origin entries
    }
  }
  if (allowedOrigins.size === 0) return null;
  return { coreUrl: parsed.origin, coreSecret, allowedOrigins };
}

export const callCore: CoreCaller = async (config, payload) => {
  const response = await fetch(`${config.coreUrl}${CORE_PATH}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Aimytime-Consultant-Auth": config.coreSecret,
    },
    body: JSON.stringify({
      system: payload.system,
      messages: payload.messages.map((m) => ({ role: m.role, text: m.text })),
    }),
    signal: AbortSignal.timeout(CORE_TIMEOUT_MS),
    redirect: "error",
  });
  if (!response.ok) throw new Error(`core status ${response.status}`);
  const data = (await response.json()) as { text?: unknown };
  if (typeof data.text !== "string") throw new Error("core response invalid");
  return data.text;
};

function json(body: ConsultantReply | { enabled: boolean } | { error: ConsultantErrorCode }, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function fail(error: ConsultantErrorCode, status: number): Response {
  return json({ error }, status);
}

function originAllowed(request: Request, config: ConsultantServerConfig): boolean {
  const origin = request.headers.get("origin");
  if (!origin || !config.allowedOrigins.has(origin)) return false;
  const fetchSite = request.headers.get("sec-fetch-site");
  return fetchSite === null || fetchSite === "same-origin";
}

function clientKey(request: Request): string {
  // nginx overwrites X-Real-IP with $remote_addr; the app listens on loopback only.
  return request.headers.get("x-real-ip")?.trim() || "unknown";
}

export type ConsultantHandlerDeps = {
  getConfig?: () => ConsultantServerConfig | null;
  limiter?: ConsultantRateLimiter;
  core?: CoreCaller;
  log?: (event: string, details?: Record<string, unknown>) => void;
};

export function createConsultantHandlers(deps: ConsultantHandlerDeps = {}) {
  const getConfig = deps.getConfig ?? (() => readConsultantConfig());
  const limiter = deps.limiter ?? new ConsultantRateLimiter();
  const core = deps.core ?? callCore;
  const log = deps.log ?? ((event, details) => console.warn(`[consultant] ${event}`, details ?? {}));

  async function GET(): Promise<Response> {
    return json({ enabled: getConfig() !== null });
  }

  async function POST(request: Request): Promise<Response> {
    const config = getConfig();
    if (!config) return fail("unavailable", 503);
    if (!originAllowed(request, config)) return fail("forbidden", 403);
    const contentType = request.headers.get("content-type") ?? "";
    if (!contentType.toLowerCase().startsWith("application/json")) return fail("invalid_request", 415);
    const declared = Number(request.headers.get("content-length") ?? "0");
    if (!Number.isFinite(declared) || declared > MAX_BODY_BYTES) return fail("payload_too_large", 413);

    let raw: string;
    try {
      raw = await request.text();
    } catch {
      return fail("invalid_request", 400);
    }
    if (new TextEncoder().encode(raw).length > MAX_BODY_BYTES) return fail("payload_too_large", 413);
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return fail("invalid_request", 400);
    }
    const dialogue = normalizeDialogue(parsed);
    if (!dialogue) return fail("invalid_request", 400);

    const decision = limiter.consume(clientKey(request));
    if (!decision.allowed) {
      log("rate_limited", { scope: decision.reason });
      return fail("rate_limited", 429);
    }

    let modelText: string;
    try {
      modelText = await core(config, {
        system: buildSystemPrompt(),
        messages: [...dialogue.history, { role: "user", text: dialogue.message }],
      });
    } catch (error) {
      log("core_failed", { reason: error instanceof Error ? error.message.slice(0, 80) : "unknown" });
      return fail("unavailable", 502);
    }

    const { text, marker } = sanitizeModelText(modelText);
    if (!text) return fail("unavailable", 502);
    return json({ text, cta: decideCta(dialogue.message, marker) });
  }

  return { GET, POST };
}
