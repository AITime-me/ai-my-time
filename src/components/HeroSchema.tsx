import { motion } from "framer-motion";
import { Globe, Bot, Inbox, LayoutDashboard, Eye, User } from "lucide-react";

const nodes = [
  { icon: User, label: "Клиент" },
  { icon: Globe, label: "Сайт" },
  { icon: Bot, label: "AI-помощник" },
  { icon: Inbox, label: "Заявка" },
  { icon: LayoutDashboard, label: "Админка" },
  { icon: Eye, label: "Собственник" },
];

export function HeroSchema() {
  return (
    <div className="glass relative overflow-hidden rounded-3xl p-6 sm:p-8">
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute -top-20 right-0 size-64 rounded-full bg-[color:var(--lime)]/20 blur-3xl" />
      <div className="relative">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">Путь клиента</p>
        <p className="mt-1 text-sm text-foreground/80">Как сайт + AI становится одним механизмом</p>
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {nodes.map((n, i) => (
            <motion.div
              key={n.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i, duration: 0.5 }}
              className="group relative flex flex-col items-start gap-2 rounded-xl border border-border/60 bg-background/40 p-3.5"
            >
              <span className="grid size-9 place-items-center rounded-lg bg-[image:var(--gradient-primary)] text-[color:var(--lime-foreground)]">
                <n.icon className="size-4" />
              </span>
              <span className="text-sm font-medium">{n.label}</span>
              <span className="absolute -top-1 right-2 text-[10px] tabular-nums text-muted-foreground">0{i + 1}</span>
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