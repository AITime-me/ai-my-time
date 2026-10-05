import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow } from "@/components/SectionHeading";
import { LegalContent } from "@/components/LegalContent";

/** Shared shell for static legal document pages. Markdown includes its own H1. */
export function LegalDocumentPage({ content }: { content: string }) {
  return (
    <SiteLayout>
      <section className="mx-auto max-w-3xl px-4 py-14 sm:px-6 sm:py-16 lg:px-8 lg:py-20">
        <Eyebrow>Юридическое</Eyebrow>
        <LegalContent content={content} />
      </section>
    </SiteLayout>
  );
}
