import { createFileRoute, notFound, Link } from "@tanstack/react-router";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow, GlassCard } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { getServiceBySlug } from "@/data/services";
import { absoluteUrl } from "@/lib/site-url";
import { ArrowLeft } from "lucide-react";

export const Route = createFileRoute("/services/$slug")({
  loader: ({ params }) => {
    const data = getServiceBySlug(params.slug);
    if (!data) throw notFound();
    return data;
  },
  head: ({ loaderData }) => {
    const path = loaderData ? `/services/${loaderData.slug}` : "";
    const url = path ? absoluteUrl(path) : "";
    return {
      meta: loaderData
        ? [
            { title: loaderData.seo_title || loaderData.title },
            {
              name: "description",
              content: loaderData.seo_description || loaderData.short_description || "",
            },
            { property: "og:title", content: loaderData.seo_title || loaderData.title },
            {
              property: "og:description",
              content: loaderData.seo_description || loaderData.short_description || "",
            },
            { property: "og:url", content: url },
          ]
        : [],
      links: loaderData ? [{ rel: "canonical", href: url }] : [],
      scripts: loaderData
        ? [
            {
              type: "application/ld+json",
              children: JSON.stringify({
                "@context": "https://schema.org",
                "@type": "Service",
                name: loaderData.title,
                description: loaderData.short_description,
                url,
                provider: { "@type": "Organization", name: "AI My Time" },
              }),
            },
          ]
        : [],
    };
  },
  component: ServiceDetail,
  notFoundComponent: () => (
    <SiteLayout>
      <div className="mx-auto max-w-2xl px-4 py-24 text-center">
        <h1 className="text-3xl font-semibold">Услуга не найдена</h1>
        <Link to="/services" className="mt-4 inline-block text-[color:var(--lime)]">
          К списку услуг
        </Link>
      </div>
    </SiteLayout>
  ),
  errorComponent: () => (
    <SiteLayout>
      <div className="mx-auto max-w-2xl px-4 py-24 text-center">
        <h1 className="text-3xl font-semibold">Что-то пошло не так</h1>
        <Link to="/services" className="mt-4 inline-block text-[color:var(--lime)]">
          К списку услуг
        </Link>
      </div>
    </SiteLayout>
  ),
});

function ServiceDetail() {
  const data = Route.useLoaderData();
  return (
    <SiteLayout>
      <section className="mx-auto max-w-4xl px-4 pt-14 sm:px-6 lg:px-8">
        <Link
          to="/services"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> Все услуги
        </Link>
        <Eyebrow className="mt-4">Услуга</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">
          {data.h1 || data.title}
        </h1>
        {data.full_description && (
          <p className="mt-5 text-lg text-muted-foreground">{data.full_description}</p>
        )}
      </section>

      <section className="mx-auto max-w-4xl px-4 py-12 sm:px-6 sm:py-14 lg:px-8 lg:py-16">
        <div className="grid gap-4 sm:grid-cols-2 sm:gap-5 lg:gap-6">
          {data.audience && (
            <GlassCard>
              <p className="text-xs uppercase tracking-wider text-muted-foreground">
                Кому подходит
              </p>
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
        <div className="mt-10 flex flex-col gap-3">
          <div className="flex flex-wrap gap-3">
            <CTAButton event="click_bot_services" size="lg">
              {data.cta_text || "Обсудить задачу"}
            </CTAButton>
            <Link
              to="/services"
              className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm glass"
            >
              Другие услуги
            </Link>
          </div>
        </div>
      </section>
    </SiteLayout>
  );
}
