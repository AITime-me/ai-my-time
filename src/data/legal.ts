import privacyContent from "@/content/legal/privacy.md?raw";
import personalDataConsentContent from "@/content/legal/personal-data-consent.md?raw";
import offerContent from "@/content/legal/offer.md?raw";

export type LegalDocumentId = "privacy" | "personal-data-consent" | "offer";

export type LegalDocument = {
  id: LegalDocumentId;
  /** Document body — verbatim markdown from approved legal files. */
  content: string;
  seoTitle: string;
  seoDescription: string;
};

/**
 * Public legal documents are stored as static markdown in the repo
 * so /privacy, /offer and /personal-data-consent stay available
 * even if optional external services (e.g. Supabase) are down.
 */
export const legalDocuments: Record<LegalDocumentId, LegalDocument> = {
  privacy: {
    id: "privacy",
    content: privacyContent,
    seoTitle: "Политика в отношении обработки персональных данных — AI My Time",
    seoDescription:
      "Политика AI My Time в отношении обработки персональных данных. Редакция от 1 октября 2026 года.",
  },
  "personal-data-consent": {
    id: "personal-data-consent",
    content: personalDataConsentContent,
    seoTitle: "Согласие на обработку персональных данных — AI My Time",
    seoDescription:
      "Согласие на обработку персональных данных AI My Time. Редакция от 1 октября 2026 года.",
  },
  offer: {
    id: "offer",
    content: offerContent,
    seoTitle: "Публичная оферта — AI My Time",
    seoDescription:
      "Публичная оферта на заключение рамочного договора об оказании услуг AI My Time. Редакция от 1 октября 2026 года.",
  },
};
