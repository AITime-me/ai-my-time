import { createFileRoute, notFound, Link, redirect } from "@tanstack/react-router";

import { SiteLayout } from "@/components/SiteLayout";
import { SolutionDetailPage } from "@/components/SolutionDetailPage";
import { AI_AGENT_LEGACY_SLUG, getSolutionBySlug, isSolutionSlug } from "@/data/solutions";
import { absoluteUrl } from "@/lib/site-url";

export const Route = createFileRoute("/solutions/$slug")({
  beforeLoad: ({ params }) => {
    if (params.slug === AI_AGENT_LEGACY_SLUG) {
      throw redirect({
        to: "/solutions/$slug",
        params: { slug: "ai-agent" },
        replace: true,
        statusCode: 301,
      });
    }
    if (!isSolutionSlug(params.slug)) throw notFound();
  },
  head: ({ params }) => {
    const solution = getSolutionBySlug(params.slug);
    if (!solution) return {};
    const path = `/solutions/${solution.slug}`;
    const url = absoluteUrl(path);
    const image = solution.steps[0]?.src ? absoluteUrl(solution.steps[0].src) : undefined;
    const ogTitle = solution.ogTitle ?? solution.seoTitle;
    const ogDescription = solution.ogDescription ?? solution.seoDescription;
    return {
      meta: [
        { title: solution.seoTitle },
        { name: "description", content: solution.seoDescription },
        { property: "og:title", content: ogTitle },
        { property: "og:description", content: ogDescription },
        { property: "og:url", content: url },
        { property: "og:type", content: "website" },
        { name: "twitter:card", content: "summary_large_image" },
        { name: "twitter:title", content: ogTitle },
        { name: "twitter:description", content: ogDescription },
        ...(image
          ? [
              { property: "og:image", content: image },
              { name: "twitter:image", content: image },
            ]
          : []),
      ],
      links: [{ rel: "canonical", href: url }],
      scripts: [
        {
          type: "application/ld+json",
          children: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "WebPage",
            name: solution.h1,
            description: solution.seoDescription,
            url,
            ...(image ? { image } : {}),
            isPartOf: { "@type": "WebSite", name: "AI My Time", url: absoluteUrl("/") },
          }),
        },
      ],
    };
  },
  component: SolutionPage,
  notFoundComponent: () => (
    <SiteLayout>
      <div className="mx-auto max-w-2xl px-4 py-24 text-center">
        <h1 className="text-3xl font-semibold">Сценарий не найден</h1>
        <Link to="/" hash="scenarios" className="mt-4 inline-block text-[color:var(--lime)]">
          К сценариям на главной
        </Link>
      </div>
    </SiteLayout>
  ),
});

function SolutionPage() {
  const { slug } = Route.useParams();
  const solution = getSolutionBySlug(slug);
  if (!solution) return null;
  return <SolutionDetailPage solution={solution} />;
}
