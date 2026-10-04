/**
 * Builds the evaluation bundle (system prompt + normalized dialogues) exactly
 * as /api/consultant would send them to Core. Usage:
 *   bun scripts/consultant-eval/build-bundle.ts > bundle.json
 */
import { normalizeDialogue } from "../../src/consultant/policy.server";
import { buildSystemPrompt } from "../../src/consultant/prompt.server";
import { evalCases } from "./cases";

const cases = evalCases.map((item) => {
  const dialogue = normalizeDialogue({ message: item.message, history: item.history ?? [] });
  if (!dialogue) throw new Error(`case ${item.id} is rejected by normalizeDialogue`);
  return { id: item.id, messages: [...dialogue.history, { role: "user", text: dialogue.message }] };
});

process.stdout.write(JSON.stringify({ system: buildSystemPrompt(), cases }));
