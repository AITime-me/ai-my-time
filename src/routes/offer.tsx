import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow } from "@/components/SectionHeading";
import { getLegalPage } from "@/lib/site.functions";

export const Route = createFileRoute("/offer")({
  head: () => ({
    meta: [
      { title: "Договор оферты — AI My Time" },
      { name: "description", content: "Договор оферты на digital-услуги проекта AI My Time." },
      { property: "og:url", content: "/offer" },
    ],
    links: [{ rel: "canonical", href: "/offer" }],
  }),
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: ["legal","offer"], queryFn: () => getLegalPage({ data: { type: "offer" } }) }),
  component: OfferPage,
});

function OfferPage() {
  const { data } = useSuspenseQuery({ queryKey: ["legal","offer"], queryFn: () => getLegalPage({ data: { type: "offer" } }) });
  return (
    <SiteLayout>
      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
        <Eyebrow>Юридическое</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight">{data?.title}</h1>
        <article className="prose prose-invert mt-8 max-w-none whitespace-pre-wrap text-base text-foreground/85">
          {data?.content}
        </article>
      </section>
    </SiteLayout>
  );
}