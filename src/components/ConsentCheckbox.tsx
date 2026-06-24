import { Link } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

type Props = {
  id?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  error?: string;
  className?: string;
};

export function ConsentCheckbox({ id = "consent", checked, onChange, error, className }: Props) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <label htmlFor={id} className="flex items-start gap-2 cursor-pointer select-none">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="mt-0.5 size-4 shrink-0 cursor-pointer rounded border-border/60 bg-background/40 text-[color:var(--lime)] accent-[color:var(--lime)] focus:ring-1 focus:ring-[color:var(--lime)]/40"
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
        />
        <span className="text-[12px] leading-snug text-muted-foreground/80">
          Я даю согласие на обработку персональных данных в соответствии с{" "}
          <Link
            to="/privacy"
            className="underline underline-offset-2 decoration-muted-foreground/40 hover:text-foreground/80"
          >
            Политикой обработки персональных данных
          </Link>
          {" "}и принимаю условия{" "}
          <Link
            to="/offer"
            className="underline underline-offset-2 decoration-muted-foreground/40 hover:text-foreground/80"
          >
            Договора публичной оферты
          </Link>
          .
        </span>
      </label>
      {error && (
        <p id={`${id}-error`} className="ml-6 text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}