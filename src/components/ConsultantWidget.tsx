import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MessageCircle, RotateCcw, Send, X } from "lucide-react";
import { OFFICIAL_TELEGRAM_CHANNEL } from "@/config/site";
import { trackEvent } from "@/lib/analytics";
import {
  CONSULTANT_ENDPOINT,
  MAX_HISTORY_CHARS,
  MAX_HISTORY_MESSAGES,
  MAX_MESSAGE_CHARS,
  type ConsultantErrorBody,
  type ConsultantReply,
  type ConsultantTurn,
} from "@/consultant/shared";

const STORAGE_KEY = "aimytime.consultant.v1";
const GREETING =
  "Здравствуйте! Я AI-консультант AI My Time. Могу рассказать об автоматизации, CRM, AI-решениях и Радаре спроса. Что хотите узнать?";
const QUICK_QUESTIONS = ["Что вы делаете?", "Что такое Радар спроса?", "С чего начать?"];

type StoredTurn = ConsultantTurn & { cta?: boolean };
type Pending = { text: string; status: "loading" | "error"; error?: "rate_limited" | "unavailable" };

function loadTurns(): StoredTurn[] {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (t): t is StoredTurn =>
        !!t &&
        typeof t === "object" &&
        (t.role === "user" || t.role === "assistant") &&
        typeof t.text === "string",
    );
  } catch {
    return [];
  }
}

function saveTurns(turns: StoredTurn[]): void {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(turns.slice(-30)));
  } catch {
    // storage may be unavailable (private mode); the chat still works in memory
  }
}

function historyForRequest(turns: StoredTurn[], message: string): ConsultantTurn[] {
  const result: ConsultantTurn[] = [];
  let budget = MAX_HISTORY_CHARS - message.length;
  for (let i = turns.length - 1; i >= 0 && result.length < MAX_HISTORY_MESSAGES; i -= 1) {
    const { role, text } = turns[i];
    if (text.length > budget) break;
    budget -= text.length;
    result.unshift({ role, text });
  }
  while (result.length && result[0].role === "assistant") result.shift();
  return result;
}

function TelegramCard() {
  return (
    <div className="rounded-xl border border-[color:var(--lime)]/30 bg-[color:var(--lime)]/5 p-3 text-sm">
      <p className="text-foreground">Обсудить вашу задачу можно с командой AI My Time в Telegram-канале.</p>
      <a
        href={OFFICIAL_TELEGRAM_CHANNEL}
        target="_blank"
        rel="noopener noreferrer"
        onClick={() => trackEvent("consultant_telegram_click", { place: "card" })}
        className="mt-2 inline-flex items-center justify-center rounded-full bg-[image:var(--gradient-primary)] px-4 py-2 text-sm font-medium text-[color:var(--lime-foreground)]"
      >
        Перейти в Telegram
      </a>
    </div>
  );
}

function Bubble({ role, text }: ConsultantTurn) {
  const isUser = role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <p
        className={
          "max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-3 py-2 text-sm leading-relaxed " +
          (isUser
            ? "bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)]"
            : "bg-white/5 text-foreground")
        }
      >
        {text}
      </p>
    </div>
  );
}

export function ConsultantWidget() {
  const [enabled, setEnabled] = useState(false);
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<StoredTurn[]>([]);
  const [pending, setPending] = useState<Pending | null>(null);
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let cancelled = false;
    setTurns(loadTurns());
    fetch(CONSULTANT_ENDPOINT, { method: "GET", headers: { Accept: "application/json" } })
      .then((r) => (r.ok ? (r.json() as Promise<{ enabled?: unknown }>) : { enabled: false }))
      .then((data) => {
        if (!cancelled) setEnabled(data.enabled === true);
      })
      .catch(() => {
        if (!cancelled) setEnabled(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const mobile = window.matchMedia("(max-width: 639px)").matches;
    const previousOverflow = document.body.style.overflow;
    if (mobile) document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, pending, open]);

  const send = useCallback(
    async (raw: string) => {
      const message = raw.trim().slice(0, MAX_MESSAGE_CHARS);
      if (!message || pending?.status === "loading") return;
      setInput("");
      setPending({ text: message, status: "loading" });
      trackEvent("consultant_send");
      try {
        const response = await fetch(CONSULTANT_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ message, history: historyForRequest(turns, message) }),
        });
        if (!response.ok) {
          const body = (await response.json().catch(() => ({}))) as Partial<ConsultantErrorBody>;
          setPending({
            text: message,
            status: "error",
            error: body.error === "rate_limited" ? "rate_limited" : "unavailable",
          });
          return;
        }
        const reply = (await response.json()) as ConsultantReply;
        if (typeof reply.text !== "string" || !reply.text) throw new Error("empty reply");
        const next: StoredTurn[] = [
          ...turns,
          { role: "user", text: message },
          { role: "assistant", text: reply.text, cta: reply.cta === true },
        ];
        setTurns(next);
        saveTurns(next);
        setPending(null);
      } catch {
        setPending({ text: message, status: "error", error: "unavailable" });
      }
    },
    [pending, turns],
  );

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(input);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void send(input);
    }
  };

  const reset = () => {
    setTurns([]);
    setPending(null);
    setInput("");
    saveTurns([]);
    inputRef.current?.focus();
  };

  if (!enabled) return null;

  const loading = pending?.status === "loading";
  const showQuick = turns.length === 0 && !pending;

  return (
    <div className="fixed bottom-4 right-4 z-50 sm:bottom-6 sm:right-6">
      <AnimatePresence>
        {open && (
          <motion.section
            role="dialog"
            aria-label="AI-консультант AI My Time"
            initial={{ opacity: 0, y: 12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.97 }}
            className="glass fixed inset-0 z-50 flex flex-col bg-background/95 sm:static sm:inset-auto sm:mb-3 sm:h-[560px] sm:max-h-[calc(100vh-7rem)] sm:w-[380px] sm:rounded-2xl"
          >
            <header className="flex items-center justify-between gap-2 border-b border-white/10 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">AI-консультант AI My Time</p>
                <a
                  href={OFFICIAL_TELEGRAM_CHANNEL}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => trackEvent("consultant_telegram_click", { place: "header" })}
                  className="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                >
                  Telegram-канал
                </a>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={reset}
                  aria-label="Начать заново"
                  title="Начать заново"
                  className="rounded-full p-2 text-muted-foreground hover:bg-white/5 hover:text-foreground"
                >
                  <RotateCcw className="size-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="Закрыть"
                  className="rounded-full p-2 text-muted-foreground hover:bg-white/5 hover:text-foreground"
                >
                  <X className="size-4" />
                </button>
              </div>
            </header>

            <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
              <Bubble role="assistant" text={GREETING} />
              {showQuick && (
                <div className="flex flex-wrap gap-2">
                  {QUICK_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => void send(q)}
                      className="rounded-full border border-white/15 px-3 py-1.5 text-xs text-foreground hover:border-[color:var(--lime)]/50"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
              {turns.map((turn, index) => (
                <div key={index} className="space-y-2">
                  <Bubble role={turn.role} text={turn.text} />
                  {turn.role === "assistant" && turn.cta && <TelegramCard />}
                </div>
              ))}
              {pending && <Bubble role="user" text={pending.text} />}
              {loading && <p className="text-xs text-muted-foreground">Консультант печатает…</p>}
              {pending?.status === "error" && (
                <div className="rounded-xl border border-red-400/30 bg-red-400/5 p-3 text-sm">
                  <p>
                    {pending.error === "rate_limited"
                      ? "Слишком много сообщений подряд. Попробуйте чуть позже или напишите нам в Telegram."
                      : "Не получилось ответить. Попробуйте ещё раз или напишите нам в Telegram."}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {pending.error !== "rate_limited" && (
                      <button
                        type="button"
                        onClick={() => void send(pending.text)}
                        className="rounded-full border border-white/20 px-3 py-1.5 text-xs hover:bg-white/5"
                      >
                        Повторить
                      </button>
                    )}
                    <a
                      href={OFFICIAL_TELEGRAM_CHANNEL}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => trackEvent("consultant_telegram_click", { place: "error" })}
                      className="rounded-full border border-white/20 px-3 py-1.5 text-xs hover:bg-white/5"
                    >
                      Перейти в Telegram
                    </a>
                  </div>
                </div>
              )}
            </div>

            <form onSubmit={onSubmit} className="border-t border-white/10 p-3">
              <div className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value.slice(0, MAX_MESSAGE_CHARS))}
                  onKeyDown={onKeyDown}
                  rows={1}
                  maxLength={MAX_MESSAGE_CHARS}
                  placeholder="Напишите вопрос…"
                  aria-label="Ваш вопрос"
                  className="max-h-32 min-h-[40px] flex-1 resize-none rounded-xl border border-white/15 bg-transparent px-3 py-2 text-sm outline-none focus:border-[color:var(--lime)]/60"
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  aria-label="Отправить"
                  className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)] disabled:opacity-40"
                >
                  <Send className="size-4" />
                </button>
              </div>
              <p className="mt-2 flex justify-between text-[11px] text-muted-foreground">
                <span>AI может ошибаться. Не отправляйте персональные данные.</span>
                {input.length > MAX_MESSAGE_CHARS - 100 && (
                  <span>
                    {input.length}/{MAX_MESSAGE_CHARS}
                  </span>
                )}
              </p>
            </form>
          </motion.section>
        )}
      </AnimatePresence>

      {!open && (
        <button
          type="button"
          onClick={() => {
            trackEvent("consultant_open");
            setOpen(true);
          }}
          className="flex items-center gap-2 rounded-full bg-[image:var(--gradient-primary)] px-4 py-3 text-sm font-medium text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)] transition-transform hover:scale-105"
          aria-label="Задать вопрос AI-консультанту"
        >
          <MessageCircle className="size-5" />
          <span>Задать вопрос</span>
        </button>
      )}
    </div>
  );
}
