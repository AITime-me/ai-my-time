import { motion } from "framer-motion";
import { Globe, Bot, Inbox, Headset, UserCheck, UserPlus, ArrowRight, ArrowDown, ArrowDownLeft } from "lucide-react";

const nodes = [
  { icon: UserPlus, label: "Потенциальный клиент", hint: "человек с задачей" },
  { icon: Globe, label: "Сайт", hint: "объясняет предложение" },
  { icon: Bot, label: "AI-помощник", hint: "уточняет запрос" },
  { icon: Inbox, label: "Заявка", hint: "фиксирует контакт" },
  { icon: Headset, label: "Менеджер", hint: "обрабатывает заявку" },
  { icon: UserCheck, label: "Клиент", hint: "получает результат" },
];

function DesktopArrow({ index }: { index: number }) {
  if (index === 0 || index === 2 || index === 4) {
    return (
      <span className="pointer-events-none absolute -right-3 top-1/2 z-10 hidden -translate-y-1/2 sm:block">
        <ArrowRight className="size-4 text-[color:var(--lime)] drop-shadow-[0_0_6px_var(--lime)]" />
      </span>
    );
  }
  if (index === 1 || index === 3) {
    return (
      <span className="pointer-events-none absolute bottom-[-12px] left-3 z-10 hidden sm:block">
        <ArrowDownLeft className="size-4 text-[color:var(--lime)] drop-shadow-[0_0_6px_var(--lime)]" />
      </span>
    );
  }
  return null;
}

function MobileArrow({ index }: { index: number }) {
  if (index >= nodes.length - 1) return null;
  return (
    <span className="pointer-events-none absolute bottom-[-12px] left-1/2 z-10 -translate-x-1/2 sm:hidden">
      <ArrowDown className="size-4 text-[color:var(--lime)] drop-shadow-[0_0_6px_var(--lime)]" />
    </span>
  );
}

export function HeroSchema() {
  return (
    <div className="glass relative overflow-hidden rounded-3xl p-6 sm:p-8">
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute -top-20 right-0 size-64 rounded-full bg-[color:var(--lime)]/20 blur-3xl" />
      <div className="relative">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">Путь клиента</p>
        <p className="mt-1 text-sm text-foreground/80">Как сайт + AI становится одним механизмом</p>
        <div className="relative mt-6 grid auto-rows-fr grid-cols-1 gap-3 sm:grid-cols-2">
          {nodes.map((n, i) => (
            <motion.div
              key={n.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i, duration: 0.5 }}
              className="group relative flex h-full min-h-[140px] min-w-0 flex-col items-start justify-start gap-3 rounded-xl border border-[color:var(--lime)]/25 bg-background/40 px-4 py-5 shadow-[inset_0_0_0_1px_rgba(163,230,53,0.04)]"
            >
              <span className="grid size-9 place-items-center rounded-lg bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)]">
                <n.icon className="size-4" />
              </span>
              <div className="flex w-full min-w-0 flex-col gap-1">
                <span className="break-words text-sm font-medium leading-snug">{n.label}</span>
                <span className="break-words text-[11px] leading-snug text-muted-foreground">{n.hint}</span>
              </div>
              <span className="absolute -top-1 right-2 text-[10px] tabular-nums text-muted-foreground">0{i + 1}</span>
              <DesktopArrow index={i} />
              <MobileArrow index={i} />
            </motion.div>
          ))}
        </div>
        <div className="mt-6 flex items-center justify-between gap-3 rounded-xl border border-border/60 bg-background/40 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-[color:var(--lime)] shadow-[0_0_10px_var(--lime)]" />
            <span className="text-sm">Заявок сегодня</span>
          </div>
          <span className="font-mono text-sm tabular-nums">12 / 14</span>
        </div>
      </div>
    </div>
  );
}
