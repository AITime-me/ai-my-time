import {
  MAX_ASSISTANT_CHARS,
  MAX_HISTORY_CHARS,
  MAX_HISTORY_MESSAGES,
  MAX_MESSAGE_CHARS,
  type ConsultantCtaIntent,
  type ConsultantTurn,
} from "./shared";

export const TELEGRAM_MARKER = "[[TG]]";

export type NormalizedDialogue = {
  message: string;
  history: ConsultantTurn[];
};

// Control characters except tab/newline; zero-width and bidi overrides.
const UNSAFE_CHARS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F\u200B-\u200F\u202A-\u202E\u2066-\u2069]/g;

function cleanText(value: string): string {
  return value.replace(UNSAFE_CHARS, "").replace(/\r\n?/g, "\n").trim();
}

/**
 * Validates the browser payload. Roles other than user/assistant (system, tool,
 * developer, ...) are dropped, never forwarded. Returns null when invalid.
 */
export function normalizeDialogue(input: unknown): NormalizedDialogue | null {
  if (!input || typeof input !== "object" || Array.isArray(input)) return null;
  const { message, history } = input as { message?: unknown; history?: unknown };
  if (typeof message !== "string") return null;
  const cleanMessage = cleanText(message);
  if (!cleanMessage || cleanMessage.length > MAX_MESSAGE_CHARS) return null;

  const rawHistory = history === undefined ? [] : history;
  if (!Array.isArray(rawHistory)) return null;

  const turns: ConsultantTurn[] = [];
  for (const item of rawHistory) {
    if (!item || typeof item !== "object") return null;
    const { role, text } = item as { role?: unknown; text?: unknown };
    if (role !== "user" && role !== "assistant") continue;
    if (typeof text !== "string") return null;
    const clean = cleanText(text);
    if (!clean) continue;
    const limit = role === "user" ? MAX_MESSAGE_CHARS : MAX_ASSISTANT_CHARS;
    if (clean.length > limit) return null;
    turns.push({ role, text: clean });
  }
  if (turns.length > MAX_HISTORY_MESSAGES) return null;
  const total = turns.reduce((sum, turn) => sum + turn.text.length, cleanMessage.length);
  if (total > MAX_HISTORY_CHARS) return null;
  return { message: cleanMessage, history: turns };
}

const CONTENT_PATTERNS: RegExp[] = [
  /(хочу|можно|где|дайте|покажите).{0,40}(почитать|материал|стать|публикац)/i,
  /(хочу|как|можно).{0,30}(подписаться|следить\s+за\s+проектом)/i,
  /(ссылк|канал|подпис).{0,30}(телеграм|telegram|тг)|(телеграм|telegram).{0,30}(ссылк|канал|подпис)/i,
];

const COMMERCIAL_PATTERNS: RegExp[] = [
  /цен[аыуеой]|стоимост|сколько\s+(это\s+)?(стоит|будет\s+стоить|стоят)|прайс|бюджет|тариф|расценк|по\s+деньгам/i,
  /срок|за\s+сколько|как\s+быстро|сколько\s+(времени|дней|недель|месяцев)|когда\s+(будет\s+)?готов/i,
  /(хочу|давайте|готов[аы]?|можно)\s+(начать|начн[её]м|приступить)|начать\s+работ|с\s+чего\s+(нам\s+)?начать|как\s+начать/i,
  /заказать|оформить\s+заказ|хочу\s+заказ|сделать\s+заказ/i,
  /связаться|связь\s+с\s+(вами|командой|менеджером)|как\s+(с\s+вами\s+)?связ|контакт|написать\s+вам|позвонить|менеджер/i,
  /консультаци[июяей]/i,
  /обсудить\s+(мой|мою|моё|мое|мои|наш|нашу|наше|задачу|проект|бизнес|ситуацию|детали|автоматизац)|хочу.{0,60}обсудить/i,
  /подойд[её]т\s+ли.{0,60}(мо(ему|ей)|нашему)\s+бизнес/i,
  /(хочу|нужно|можете|давайте|готов[аы]?).{0,80}(внедр|реализ|автоматиз|подключ)/i,
];

const RADAR_COMMERCIAL_PATTERNS: RegExp[] = [
  /подойд[её]т(?:\s+ли)?.{0,30}радар(?:.{0,30}(?:мне|бизнес))?|(?:мне|бизнес).{0,30}подойд[её]т(?:\s+ли)?.{0,30}радар/i,
  /(хочу|нужен|интересует).{0,30}радар|радар.{0,30}(хочу|нужен|интересует)/i,
  /(цен|стоимост|сколько.{0,15}стоит).{0,40}радар|радар.{0,40}(цен|стоимост|сколько.{0,15}стоит)/i,
  /(подключ|внедр|заказ).{0,30}радар|радар.{0,30}(подключ|внедр|заказ)/i,
  /(можно|хочу|нужен|использ|примен).{0,30}радар.{0,30}(бизнес|компани)|радар.{0,30}(бизнес|компани).{0,30}(можно|хочу|нужен|использ|примен)/i,
  /обсудить.{0,30}радар|радар.{0,30}обсудить/i,
];

const RADAR_INFORMATIONAL_NO_CTA: RegExp[] = [
  /что\s+такое\s+радар(\s+спроса)?/i,
  /где\s+(он|радар)\s+ищет/i,
];

function matchesAny(message: string, patterns: RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(message));
}

/** Explicit user intent that deserves the diagnostic card, independent of the model. */
export function userAsksForTeam(message: string): boolean {
  return matchesAny(message, RADAR_COMMERCIAL_PATTERNS) || matchesAny(message, COMMERCIAL_PATTERNS);
}

/**
 * Ordinary problem statements. The model sometimes appends [[TG]] for these;
 * the card must not appear unless the user also expresses explicit team intent.
 */
const SITUATIONAL_NO_CTA: RegExp[] = [
  /пишут\s+(клиенты|люди)|клиенты\s+пишут|вечером|в\s+нерабоч/i,
  /заявк[аиуе].{0,40}(теря|теряют|теряются|в\s+telegram|в\s+телеграм)/i,
  /вс[её]\s+делаю\s+сам[ао]?|нет\s+сотрудник|без\s+сотрудник|один[ао]?\s+работаю/i,
  /много\s+(сообщений|обращений|заявок)|не\s+успеваю\s+отвечать/i,
];

function isSituationalWithoutIntent(message: string): boolean {
  if (userAsksForTeam(message)) return false;
  return SITUATIONAL_NO_CTA.some((pattern) => pattern.test(message));
}

/**
 * The server decides only a small intent enum. URLs and payloads remain
 * client-owned and allowlisted.
 */
export function decideCtaIntent(message: string, marker: boolean): ConsultantCtaIntent {
  if (matchesAny(message, RADAR_COMMERCIAL_PATTERNS)) return "radar_diagnostic";
  if (matchesAny(message, COMMERCIAL_PATTERNS)) return "diagnostic";
  if (matchesAny(message, CONTENT_PATTERNS)) return "content";
  if (matchesAny(message, RADAR_INFORMATIONAL_NO_CTA)) return "none";
  if (!marker || isSituationalWithoutIntent(message)) return "none";
  return "diagnostic";
}

/** Backward-compatible boolean for callers that do not need destination intent. */
export function decideCta(message: string, marker: boolean): boolean {
  return decideCtaIntent(message, marker) !== "none";
}

/**
 * Removes service markers and anything the UI must never receive from the
 * model as actionable content (links, markdown control syntax).
 */
export function sanitizeModelText(raw: string): { text: string; marker: boolean } {
  const marker = /\[\[\s*TG\s*\]\]/i.test(raw);
  const text = raw
    .replace(/\[\[[^\]]{0,40}\]\]/g, "")
    .replace(/\[([^\]]{1,200})\]\((?:[^)\s]{1,500})\)/g, "$1")
    .replace(/\b(?:https?:\/\/|www\.)\S+/gi, "")
    .replace(/\bt\.me\/\S+/gi, "")
    .replace(/<[^>]{1,200}>/g, "")
    .replace(/\*\*|__|`/g, "")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
    .slice(0, MAX_ASSISTANT_CHARS);
  return { text, marker };
}
