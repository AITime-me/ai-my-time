import { createFileRoute, notFound, Link } from "@tanstack/react-router";

import { SiteLayout } from "@/components/SiteLayout";
import { SolutionDetailPage } from "@/components/SolutionDetailPage";
import { getSolutionBySlug, isSolutionSlug } from "@/data/solutions";

export const Route = createFileRoute("/solutions/$slug")({
  beforeLoad: ({ params }) => {
    if (!isSolutionSlug(params.slug)) throw notFound();
  },
  head: ({ params }) => {
    const solution = getSolutionBySlug(params.slug);
    if (!solution) return {};
    const url = `/solutions/${solution.slug}`;
    const image = solution.steps[0]?.src;
    return {
      meta: [
        { title: solution.seoTitle },
        { name: "description", content: solution.seoDescription },
        { property: "og:title", content: solution.seoTitle },
        { property: "og:description", content: solution.seoDescription },
        { property: "og:url", content: url },
        { property: "og:type", content: "website" },
        ...(image ? [{ property: "og:image", content: image }] : []),
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
            isPartOf: { "@type": "WebSite", name: "AI My Time" },
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
