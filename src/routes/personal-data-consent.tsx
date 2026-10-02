import { createFileRoute } from "@tanstack/react-router";

import { LegalDocumentPage } from "@/components/LegalDocumentPage";
import { legalDocuments } from "@/data/legal";
import { absoluteUrl } from "@/lib/site-url";

const doc = legalDocuments["personal-data-consent"];

export const Route = createFileRoute("/personal-data-consent")({
  head: () => ({
    meta: [
      { title: doc.seoTitle },
      { name: "description", content: doc.seoDescription },
      { property: "og:title", content: doc.seoTitle },
      { property: "og:description", content: doc.seoDescription },
      { property: "og:url", content: absoluteUrl("/personal-data-consent") },
    ],
    links: [{ rel: "canonical", href: absoluteUrl("/personal-data-consent") }],
  }),
  component: PersonalDataConsentPage,
});

function PersonalDataConsentPage() {
  return <LegalDocumentPage content={doc.content} />;
}
