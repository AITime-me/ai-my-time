/** Real AI-consultant / bot destination — not empty and not the legacy "#" sentinel. */
export function isRealBotUrl(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const v = value.trim();
  return v !== "" && v !== "#";
}
