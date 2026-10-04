import { describe, expect, test } from "bun:test";
import { ConsultantRateLimiter } from "../../src/consultant/limits.server";
import {
  decideCta,
  decideCtaIntent,
  sanitizeModelText,
  userAsksForTeam,
} from "../../src/consultant/policy.server";
import { buildKnowledge, RADAR_DEFINITION } from "../../src/consultant/knowledge.server";
import { buildSystemPrompt } from "../../src/consultant/prompt.server";
import {
  DIAGNOSTIC_BOT_BASE_URL,
  DIAGNOSTIC_SOURCES,
  getDiagnosticUrl,
} from "../../src/lib/diagnostic-url";

describe("decideCta", () => {
  test("explicit intent always shows the card", () => {
    expect(decideCta("Сколько стоит?", false)).toBe(true);
    expect(decideCta("Хочу обсудить мой бизнес", false)).toBe(true);
    expect(userAsksForTeam("Дайте ссылку на Telegram")).toBe(false);
    expect(decideCtaIntent("Дайте ссылку на Telegram", false)).toBe("content");
  });

  test("situational messages never show the card from a model marker alone", () => {
    for (const message of [
      "Мне пишут клиенты вечером",
      "У меня заявки в Telegram.",
      "Я всё делаю сама.",
      "У меня нет сотрудников, мне это подходит?",
      "Много сообщений, не успеваю отвечать",
    ]) {
      expect(decideCta(message, true)).toBe(false);
    }
  });

  test("model marker remains valid for non-situational unknowns", () => {
    expect(decideCta("Подойдёт ли это для клиники?", true)).toBe(true);
    expect(decideCta("Что такое CRM?", false)).toBe(false);
  });

  test("classifies required consultant messages", () => {
    expect(decideCtaIntent("Что такое Радар спроса?", true)).toBe("none");
    expect(decideCtaIntent("Где он ищет?", true)).toBe("none");
    expect(decideCtaIntent("Подойдёт ли Радар моему бизнесу?", false)).toBe(
      "radar_diagnostic",
    );
    expect(decideCtaIntent("Сколько стоит Радар?", false)).toBe("radar_diagnostic");
    expect(decideCtaIntent("Сколько стоит ваша работа?", false)).toBe("diagnostic");
    expect(decideCtaIntent("Хочу обсудить автоматизацию", false)).toBe("diagnostic");
    expect(decideCtaIntent("Хочу почитать ваши материалы", false)).toBe("content");
    expect(decideCtaIntent("Мне пишут клиенты вечером", true)).toBe("none");
  });

  test("commercial intent wins over mixed content intent", () => {
    expect(
      decideCtaIntent("Хочу почитать материалы и обсудить автоматизацию", false),
    ).toBe("diagnostic");
    expect(decideCtaIntent("Хочу почитать материалы и обсудить Радар", false)).toBe(
      "radar_diagnostic",
    );
  });

  test("recognizes bounded Radar fit variants without promoting informational questions", () => {
    expect(decideCtaIntent("Мне подойдёт Радар?", false)).toBe("radar_diagnostic");
    expect(decideCtaIntent("Можно Радар для моего бизнеса?", false)).toBe(
      "radar_diagnostic",
    );
    expect(decideCtaIntent("Что такое Радар?", true)).toBe("none");
    expect(decideCtaIntent("Где Радар ищет клиентов?", true)).toBe("none");
  });
});

describe("diagnostic URL", () => {
  test("allows only the four known payloads", () => {
    for (const source of DIAGNOSTIC_SOURCES) {
      expect(getDiagnosticUrl(source)).toBe(`${DIAGNOSTIC_BOT_BASE_URL}?start=${source}`);
    }
    expect(getDiagnosticUrl("site_consultant&start=attacker")).toBeNull();
    expect(getDiagnosticUrl("unknown")).toBeNull();
    expect(getDiagnosticUrl(null)).toBeNull();
  });
});

describe("sanitizeModelText", () => {
  test("removes markers, links and markdown", () => {
    const { text, marker } = sanitizeModelText(
      "## Ответ\n**Да**, пишите в [канал](https://t.me/fake) или https://evil.example t.me/other [[TG]]",
    );
    expect(marker).toBe(true);
    expect(text).toBe("Ответ\nДа, пишите в канал или");
    expect(text).not.toContain("t.me");
    expect(text).not.toContain("[[");
  });
});

describe("limiter", () => {
  const limits = {
    perKeyShort: { limit: 20, windowMs: 600_000 },
    perKeyDaily: { limit: 60, windowMs: 86_400_000 },
    globalMinute: { limit: 1000, windowMs: 60_000 },
    globalDaily: { limit: 100_000, windowMs: 86_400_000 },
    maxTrackedKeys: 2,
  };

  test("20 per 10 minutes, then 60 per day", () => {
    let now = 0;
    const limiter = new ConsultantRateLimiter(limits, () => now);
    for (let i = 0; i < 20; i += 1) expect(limiter.consume("a").allowed).toBe(true);
    expect(limiter.consume("a")).toEqual({ allowed: false, reason: "client" });
    for (let block = 1; block < 3; block += 1) {
      now = block * 600_001;
      for (let i = 0; i < 20; i += 1) expect(limiter.consume("a").allowed).toBe(true);
    }
    now = 3 * 600_001;
    expect(limiter.consume("a")).toEqual({ allowed: false, reason: "client" });
    now = 86_400_000 + 3 * 600_001;
    expect(limiter.consume("a").allowed).toBe(true);
  });

  test("global cap and tracked key cap fail closed", () => {
    const now = 1;
    const limiter = new ConsultantRateLimiter({ ...limits, globalMinute: { limit: 3, windowMs: 60_000 } }, () => now);
    expect(limiter.consume("a").allowed).toBe(true);
    expect(limiter.consume("b").allowed).toBe(true);
    expect(limiter.consume("c")).toEqual({ allowed: false, reason: "global" });
    expect(limiter.consume("a").allowed).toBe(true);
    expect(limiter.consume("a")).toEqual({ allowed: false, reason: "global" });
  });

  test("errors deny", () => {
    const limiter = new ConsultantRateLimiter(limits, () => {
      throw new Error("clock");
    });
    expect(limiter.consume("a")).toEqual({ allowed: false, reason: "global" });
  });
});

describe("knowledge", () => {
  const knowledge = buildKnowledge();

  test("contains radar definition, amoCRM partnership and real cases with status", () => {
    expect(knowledge).toContain(RADAR_DEFINITION);
    expect(knowledge).toContain("официальный партнёр программы amoSTART компании amoCRM");
    expect(knowledge).toContain("OpenClaw — AI-директор и центр управления бизнесом (статус: Проектируется)");
    expect(knowledge).toContain("Отдельного готового автоматического Радар-бота");
  });

  test("excludes unconfirmed radar workflow, diagnostic bot and URLs", () => {
    expect(knowledge).not.toContain("Начинается диалог");
    expect(knowledge).not.toContain("AI-агент готовит ответ");
    expect(knowledge).not.toMatch(/диагностика бизнеса: несколько вопросов/);
    expect(knowledge).not.toMatch(/https?:\/\//);
    expect(knowledge).not.toContain("t.me/");
  });

  test("prompt stays compact", () => {
    expect(buildSystemPrompt().length).toBeLessThan(30_000);
  });
});
