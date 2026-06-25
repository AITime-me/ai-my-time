import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow } from "@/components/SectionHeading";
import { getLegalPage } from "@/lib/site.functions";
import { LegalContent } from "@/components/LegalContent";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "Политика конфиденциальности — AI My Time" },
      { name: "description", content: "Политика конфиденциальности сайта проекта AI My Time." },
      { property: "og:title", content: "Политика конфиденциальности — AI My Time" },
      { property: "og:description", content: "Политика конфиденциальности сайта проекта AI My Time." },
      { property: "og:url", content: "/privacy" },
    ],
    links: [{ rel: "canonical", href: "/privacy" }],
  }),
  loader: ({ context }) => context.queryClient.ensureQueryData({ queryKey: ["legal","privacy"], queryFn: () => getLegalPage({ data: { type: "privacy" } }) }),
  component: PrivacyPage,
});

function PrivacyPage() {
  const { data } = useSuspenseQuery({ queryKey: ["legal","privacy"], queryFn: () => getLegalPage({ data: { type: "privacy" } }) });
  return (
    <SiteLayout>
      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
        <Eyebrow>Юридическое</Eyebrow>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight">{data?.title}</h1>
        <LegalContent content={data?.content} />
      </section>
    </SiteLayout>
  );
}