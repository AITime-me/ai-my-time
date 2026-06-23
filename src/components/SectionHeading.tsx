import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 rounded-full border border-border/60 bg-white/5 px-3 py-1 text-xs uppercase tracking-wider text-muted-foreground", className)}>
      <span className="size-1.5 rounded-full bg-[color:var(--lime)] shadow-[0_0_10px_var(--lime)]" />
      {children}
    </span>
  );
}

export function H2({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn("text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl", className)}>{children}</h2>;
}

export function Lead({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("mt-4 max-w-2xl text-base text-muted-foreground sm:text-lg", className)}>{children}</p>;
}

export function GlassCard({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("glass group rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[color:var(--lime)]/30 hover:shadow-[var(--shadow-glow)]", className)}>
      {children}
    </div>
  );
}