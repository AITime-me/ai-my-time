import { createFileRoute, notFound, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, GlassCard } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { getServiceBySlug } from "@/lib/site.functions";
import { ArrowLeft } from "lucide-react";

export const Route = createFileRoute("/services/$slug")({
  loader: async ({ context, params }) => {
    try {
      const data = await context.queryClient.ensureQueryData({
        queryKey: ["service", params.slug],
        queryFn: () => getServiceBySlug({ data: { slug: params.slug } }),
      });
      return data ?? null;
    } catch {
      return null;
    }
  },
  head: ({ loaderData }) => ({
    meta: loaderData
      ? [
          { title: loaderData.seo_title || loaderData.title },
          { name: "description", content: loaderData.seo_description || loaderData.short_description || "" },
          { property: "og:title", content: loaderData.seo_title || loaderData.title },
          { property: "og:description", content: loaderData.seo_description || loaderData.short_description || "" },
          { property: "og:url", content: `/services/${loaderData.slug}` },
        ]
      : [],
    links: loaderData ? [{ rel: "canonical", href: `/services/${loaderData.slug}` }] : [],
    scripts: loaderData
      ? [{
          type: "application/ld+json",
          children: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Service",
            name: loaderData.title,
            description: loaderData.short_description,
            provider: { "@type": "Organization", name: "AI My Time" },
          }),
        }]
      : [],
  }),
  component: ServiceDetail,
  notFoundComponent: () => (
    <SiteLayout>
      <div className="mx-auto max-w-2xl px-4 py-24 text-center">
        <h1 className="text-3xl font-semibold">Услуга не найдена</h1>
        <Link to="/services" className="mt-4 inline-block text-[color:var(--lime)]">К списку услуг</Link>
      </div>
    </SiteLayout>
  ),
  errorComponent: () => (
    <SiteLayout>
      <div className="mx-auto max-w-2xl px-4 py-24 text-center">
        <h1 className="text-3xl font-semibold">Что-то пошло не так</h1>
        <Link to="/services" className="mt-4 inline-block text-[color:var(--lime)]">К списку услуг</Link>
      </div>
    </SiteLayout>
  ),
});

function ServiceDetail() {
  const { slug } = Route.useParams();
  const { data } = useSuspenseQuery({
    queryKey: ["service", slug],
    queryFn: () => getServiceBySlug({ data: { slug } }),
  });
  if (!data) return null;
  return (
    <SiteLayout>
      <section className="mx-auto max-w-4xl px-4 pt-14 sm:px-6 lg:px-8">
        <Link to="/services" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" /> Все услуги
        </Link>
        <Eyebrow className="mt-4">Услуга</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">{data.h1 || data.title}</h1>
        {data.full_description && (
          <p className="mt-5 text-lg text-muted-foreground">{data.full_description}</p>
        )}
      </section>

      <section className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-4 sm:grid-cols-2">
          {data.audience && (
            <GlassCard>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Кому подходит</p>
              <p className="mt-3 text-base">{data.audience}</p>
            </GlassCard>
          )}
          {data.includes && (
            <GlassCard>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Что входит</p>
              <p className="mt-3 text-base">{data.includes}</p>
            </GlassCard>
          )}
          {data.result && (
            <GlassCard className="sm:col-span-2">
              <p className="text-xs uppercase tracking-wider text-[color:var(--lime)]">Результат</p>
              <p className="mt-3 text-base">{data.result}</p>
            </GlassCard>
          )}
        </div>
        <div className="mt-10 flex flex-wrap gap-3">
          <CTAButton event="click_bot_services" size="lg">{data.cta_text || "Обсудить задачу"}</CTAButton>
          <Link to="/services" className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm glass">
            Другие услуги
          </Link>
        </div>
      </section>
    </SiteLayout>
  );
}