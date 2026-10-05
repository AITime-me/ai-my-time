import { createFileRoute } from "@tanstack/react-router";
import type {} from "@tanstack/react-start";
import { absoluteUrl } from "@/lib/site-url";

export const Route = createFileRoute("/sitemap.xml")({
  server: {
    handlers: {
      GET: async () => {
        const paths = [
          "/",
          "/services",
          "/services/ai-audit",
          "/services/site-with-ai",
          "/services/ai-assistant",
          "/services/automation",
          "/services/mini-crm",
          "/solutions/ai-agent",
          "/solutions/demand-radar",
          "/solutions/online-booking",
          "/solutions/detailing-booking",
          "/solutions/avito-leads",
          "/solutions/service-orders",
          "/solutions/online-orders",
          "/cases",
          "/about",
          "/contacts",
          "/privacy",
          "/offer",
          "/articles/parser-nedvizhimosti-amocrm",
        ];
        const xml = [
          `<?xml version="1.0" encoding="UTF-8"?>`,
          `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">`,
          ...paths.map(
            (p) => `  <url><loc>${absoluteUrl(p)}</loc><changefreq>weekly</changefreq></url>`,
          ),
          `</urlset>`,
        ].join("\n");
        return new Response(xml, {
          headers: { "Content-Type": "application/xml", "Cache-Control": "public, max-age=3600" },
        });
      },
    },
  },
});
