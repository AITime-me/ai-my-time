import { createFileRoute } from "@tanstack/react-router";

import { LegalDocumentPage } from "@/components/LegalDocumentPage";
import { legalDocuments } from "@/data/legal";
import { absoluteUrl } from "@/lib/site-url";

const doc = legalDocuments.privacy;

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: doc.seoTitle },
      { name: "description", content: doc.seoDescription },
      { property: "og:title", content: doc.seoTitle },
      { property: "og:description", content: doc.seoDescription },
      { property: "og:url", content: absoluteUrl("/privacy") },
    ],
    links: [{ rel: "canonical", href: absoluteUrl("/privacy") }],
  }),
  component: PrivacyPage,
});

function PrivacyPage() {
  return <LegalDocumentPage content={doc.content} />;
}
