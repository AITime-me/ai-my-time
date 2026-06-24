import { cn } from "@/lib/utils";

/**
 * Small legal note shown under CTA buttons that lead to the bot
 * or open an AI-assistant dialog. Not for ordinary internal-page links.
 */
export function BotLegalNote({ className, align = "center" }: { className?: string; align?: "left" | "center" }) {
  return (
    <p
      className={cn(
        "mt-2 text-[11px] leading-snug text-muted-foreground/80",
        align === "center" ? "text-center" : "text-left",
        className,
      )}
    >
      Переходя к диалогу, вы соглашаетесь с обработкой персональных данных в соответствии с{" "}
      <a href="/privacy" className="underline decoration-dotted underline-offset-2 hover:text-foreground">
        Политикой обработки персональных данных
      </a>{" "}
      и условиями{" "}
      <a href="/offer" className="underline decoration-dotted underline-offset-2 hover:text-foreground">
        Договора публичной оферты
      </a>.
    </p>
  );
}