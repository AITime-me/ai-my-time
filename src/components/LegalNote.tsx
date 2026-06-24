import { Link } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  align?: "left" | "center" | "right";
};

export function LegalNote({ className, align = "left" }: Props) {
  const alignCls = align === "center" ? "text-center" : align === "right" ? "text-right" : "text-left";
  return (
    <p
      className={cn(
        "max-w-xs text-[11px] leading-snug text-muted-foreground/60",
        alignCls,
        className,
      )}
    >
      Начиная взаимодействие, вы соглашаетесь с{" "}
      <Link
        to="/privacy"
        className="underline underline-offset-2 decoration-muted-foreground/40 hover:text-foreground/80"
      >
        Политикой конфиденциальности
      </Link>
      {" "}и{" "}
      <Link
        to="/offer"
        className="underline underline-offset-2 decoration-muted-foreground/40 hover:text-foreground/80"
      >
        Договором оферты
      </Link>
      .
    </p>
  );
}