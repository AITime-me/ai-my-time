import { createFileRoute, useNavigate, useSearch, Link } from "@tanstack/react-router";
import { useState } from "react";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow } from "@/components/SectionHeading";
import { supabase } from "@/integrations/supabase/client";
import { z } from "zod";

export const Route = createFileRoute("/auth")({
  validateSearch: (s) => z.object({ redirect: z.string().optional() }).parse(s),
  head: () => ({
    meta: [
      { title: "Вход — AI My Time" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const { redirect } = useSearch({ from: "/auth" });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) { setError(error.message); return; }
    navigate({ to: redirect || "/admin" });
  }

  return (
    <SiteLayout>
      <section className="mx-auto max-w-md px-4 py-20 sm:px-6 lg:px-8">
        <Eyebrow>Админка</Eyebrow>
        <h1 className="mt-5 text-3xl font-semibold">Вход</h1>
        <p className="mt-2 text-sm text-muted-foreground">Доступ только для администраторов проекта.</p>
        <form onSubmit={onSubmit} className="mt-8 glass space-y-4 rounded-2xl p-6">
          <div>
            <label className="text-sm text-muted-foreground">Email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-sm text-muted-foreground">Пароль</label>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm" />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <button disabled={loading} className="w-full rounded-full bg-[image:var(--gradient-primary)] px-5 py-2.5 text-sm font-medium text-[color:var(--lime-foreground)] disabled:opacity-60">
            {loading ? "Вход…" : "Войти"}
          </button>
          <p className="text-xs text-muted-foreground">
            Нет аккаунта? Зарегистрируйтесь через Lovable Cloud и попросите назначить роль admin. <Link to="/" className="underline">На главную</Link>
          </p>
        </form>
      </section>
    </SiteLayout>
  );
}
