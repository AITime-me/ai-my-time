import { describe, expect, test } from "bun:test";
import { ConsultantRateLimiter } from "../../src/consultant/limits.server";
import { sanitizeModelText } from "../../src/consultant/policy.server";
import { buildKnowledge, RADAR_DEFINITION } from "../../src/consultant/knowledge.server";
import { buildSystemPrompt } from "../../src/consultant/prompt.server";

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

  test("contains radar definition and real cases with status", () => {
    expect(knowledge).toContain(RADAR_DEFINITION);
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
