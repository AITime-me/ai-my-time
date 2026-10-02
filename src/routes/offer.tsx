import { createFileRoute } from "@tanstack/react-router";

import { LegalDocumentPage } from "@/components/LegalDocumentPage";
import { legalDocuments } from "@/data/legal";
import { absoluteUrl } from "@/lib/site-url";

const doc = legalDocuments.offer;

export const Route = createFileRoute("/offer")({
  head: () => ({
    meta: [
      { title: doc.seoTitle },
      { name: "description", content: doc.seoDescription },
      { property: "og:title", content: doc.seoTitle },
      { property: "og:description", content: doc.seoDescription },
      { property: "og:url", content: absoluteUrl("/offer") },
    ],
    links: [{ rel: "canonical", href: absoluteUrl("/offer") }],
  }),
  component: OfferPage,
});

function OfferPage() {
  return <LegalDocumentPage content={doc.content} />;
}
