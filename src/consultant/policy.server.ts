import {
  MAX_ASSISTANT_CHARS,
  MAX_HISTORY_CHARS,
  MAX_HISTORY_MESSAGES,
  MAX_MESSAGE_CHARS,
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

const CTA_PATTERNS: RegExp[] = [
  /цен[аыуеой]|стоимост|сколько\s+(это\s+)?(стоит|будет\s+стоить|стоят)|прайс|бюджет|тариф|расценк|по\s+деньгам/i,
  /срок|за\s+сколько|как\s+быстро|сколько\s+(времени|дней|недель|месяцев)|когда\s+(будет\s+)?готов/i,
  /(хочу|давайте|готов[аы]?|можно)\s+(начать|начн[её]м|приступить)|начать\s+работ|с\s+чего\s+нам\s+начать\s+работ/i,
  /заказать|оформить\s+заказ|хочу\s+заказ|сделать\s+заказ/i,
  /связаться|связь\s+с\s+(вами|командой|менеджером)|как\s+(с\s+вами\s+)?связ|контакт|написать\s+вам|позвонить|менеджер/i,
  /консультаци[июяей]/i,
  /обсудить\s+(мой|мою|моё|мое|мои|наш|нашу|наше|задачу|проект|бизнес|ситуацию|детали)|хочу\s+обсудить/i,
  /(ссылк|канал|перейти|где\s+вас|ваш)[^.?!\n]{0,30}(телеграм|telegram|тг)|(телеграм|telegram)[^.?!\n]{0,20}(ссылк|канал)/i,
];

/** Explicit user intent that deserves the Telegram card, independent of the model. */
export function userAsksForTeam(message: string): boolean {
  return CTA_PATTERNS.some((pattern) => pattern.test(message));
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
 * CTA card: explicit user intent always wins; model marker is accepted only
 * when the message is not a plain situational description.
 */
export function decideCta(message: string, marker: boolean): boolean {
  if (userAsksForTeam(message)) return true;
  if (!marker) return false;
  if (isSituationalWithoutIntent(message)) return false;
  return true;
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
