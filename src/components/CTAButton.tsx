import { cn } from "@/lib/utils";
import { useSiteSettings } from "./SiteSettingsProvider";
import { trackEvent } from "@/lib/analytics";
import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  children?: ReactNode;
  event?: string;
  variant?: "primary" | "secondary" | "ghost";
  size?: "md" | "lg";
  className?: string;
  arrow?: boolean;
  label?: string;
};

export function CTAButton({ children, event = "click_bot_generic", variant = "primary", size = "md", className, arrow = true, label }: Props) {
  const s = useSiteSettings();
  const text = children ?? label ?? s.main_cta_text;
  const base =
    "inline-flex items-center justify-center gap-2 rounded-full font-medium transition-all duration-300 will-change-transform hover:-translate-y-0.5 active:translate-y-0";
  const sizes = size === "lg" ? "px-7 py-3.5 text-base" : "px-5 py-2.5 text-sm";
  const variants = {
    primary:
      "bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)] shadow-[var(--shadow-glow)] hover:brightness-110",
    secondary:
      "glass text-foreground hover:border-[color:var(--lime)]/40",
    ghost: "text-foreground/80 hover:text-foreground hover:bg-white/5",
  } as const;
  return (
    <a
      href={s.bot_link || "#"}
      target={s.bot_link && s.bot_link !== "#" ? "_blank" : undefined}
      rel="noopener noreferrer"
      onClick={() => trackEvent(event)}
      className={cn(base, sizes, variants[variant], className)}
    >
      <span>{text}</span>
      {arrow && <ArrowRight className="size-4" />}
    </a>
  );
}