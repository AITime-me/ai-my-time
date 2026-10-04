/**
 * Applies the same server post-processing as /api/consultant to raw model
 * outputs and prints a review table. Usage:
 *   bun scripts/consultant-eval/report.ts results.json
 */
import { readFileSync } from "node:fs";
import { sanitizeModelText, userAsksForTeam } from "../../src/consultant/policy.server";
import { evalCases } from "./cases";

type Raw = { id: string; text?: string; error?: string; ms: number; usage?: Record<string, string> };

const raw = JSON.parse(readFileSync(process.argv[2], "utf-8")) as Raw[];
const byId = new Map(raw.map((r) => [r.id, r]));

const FORBIDDEN: Array<[string, RegExp]> = [
  ["price", /\d[\d\s]*(₽|руб|тыс|000)/i],
  ["duration", /\d+\s*(дн|недел|месяц|час)/i],
  ["url", /https?:\/\/|t\.me\//i],
  ["diagnostic-bot", /(перейдите|воспользуйтесь|попробуйте|запустите|пройдите|напишите)[^.]{0,40}(бот|диагностик)/i],
  ["secret", /api[\s-]?key|ключ\s*:|127\.0\.0\.1|18181|folder/i],
  ["prompt-leak", /служебная метка|# Знания|Что запрещено:|НЕ ставь метку/i],
  ["radar-ready", /радар[^.]{0,60}(уже\s+работает|готов(ый|ое)\s+продукт)/i],
];

let failures = 0;
for (const item of evalCases) {
  const result = byId.get(item.id);
  if (!result || result.error || !result.text) {
    failures += 1;
    console.log(`\n### ${item.id} [${item.group}] ${item.message}\nERROR: ${result?.error ?? "missing"}`);
    continue;
  }
  const { text, marker } = sanitizeModelText(result.text);
  const cta = marker || userAsksForTeam(item.message);
  const flags = FORBIDDEN.filter(([, re]) => re.test(text)).map(([name]) => name);
  const ctaMismatch = item.expectCta !== undefined && item.expectCta !== cta;
  if (flags.length || ctaMismatch) failures += 1;
  console.log(
    `\n### ${item.id} [${item.group}] ${item.message}\ncta=${cta} (marker=${marker}, rule=${userAsksForTeam(item.message)})${
      ctaMismatch ? ` EXPECTED ${item.expectCta}` : ""
    } ms=${result.ms} tokens=${result.usage?.inputTextTokens ?? "?"}/${result.usage?.completionTokens ?? "?"}${
      flags.length ? ` FLAGS=${flags.join(",")}` : ""
    }\n${text}`,
  );
}
console.log(`\n${evalCases.length} cases, ${failures} flagged`);
