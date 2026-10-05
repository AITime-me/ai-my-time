import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SiteLayout } from "@/components/SiteLayout";
import { Eyebrow } from "@/components/SectionHeading";
import { CTAButton } from "@/components/CTAButton";
import { articlePath, getArticleBySlug, isArticleSlug } from "@/data/articles";
import { absoluteUrl, SITE_URL } from "@/lib/site-url";

const OG_IMAGE = absoluteUrl("/og-cover.jpg");

export const Route = createFileRoute("/articles/$slug")({
  beforeLoad: ({ params }) => {
    if (!isArticleSlug(params.slug)) throw notFound();
  },
  head: ({ params }) => {
    const article = getArticleBySlug(params.slug);
    if (!article) return {};
    const path = articlePath(article.slug);
    const url = absoluteUrl(path);
    return {
      meta: [
        { title: article.seoTitle },
        { name: "description", content: article.seoDescription },
        { property: "og:title", content: article.seoTitle },
        { property: "og:description", content: article.seoDescription },
        { property: "og:url", content: url },
        { property: "og:type", content: "article" },
        { property: "og:image", content: OG_IMAGE },
        { property: "og:image:width", content: "1200" },
        { property: "og:image:height", content: "630" },
        { name: "twitter:card", content: "summary_large_image" },
        { name: "twitter:title", content: article.seoTitle },
        { name: "twitter:description", content: article.seoDescription },
        { name: "twitter:image", content: OG_IMAGE },
        { property: "article:published_time", content: `${article.publishedAt}T00:00:00+05:00` },
        { property: "article:author", content: "Светлана Кузнецова" },
      ],
      links: [{ rel: "canonical", href: url }],
      scripts: [
        {
          type: "application/ld+json",
          children: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Article",
            headline: article.h1,
            description: article.seoDescription,
            datePublished: article.publishedAt,
            inLanguage: "ru-RU",
            url,
            mainEntityOfPage: {
              "@type": "WebPage",
              "@id": url,
            },
            author: {
              "@type": "Person",
              name: "Светлана Кузнецова",
            },
            publisher: {
              "@type": "Organization",
              name: "AI My Time",
              url: SITE_URL,
            },
            image: [OG_IMAGE],
          }),
        },
      ],
    };
  },
  component: ArticlePage,
  notFoundComponent: () => (
    <SiteLayout>
      <div className="mx-auto max-w-2xl px-4 py-24 text-center">
        <h1 className="text-3xl font-semibold">Статья не найдена</h1>
        <Link to="/" hash="articles" className="mt-4 inline-block text-[color:var(--lime)]">
          К статьям на главной
        </Link>
      </div>
    </SiteLayout>
  ),
});

function ArticlePage() {
  const { slug } = Route.useParams();
  const article = getArticleBySlug(slug);
  if (!article) return null;

  return (
    <SiteLayout>
      <article className="mx-auto max-w-3xl px-4 pb-20 pt-14 sm:px-6 lg:px-8">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">
          AI My Time · Автоматизация бизнеса
        </p>
        <Eyebrow className="mt-4">{article.eyebrow}</Eyebrow>
        <h1 className="mt-5 text-3xl font-semibold tracking-tight sm:text-4xl md:text-[2.75rem] md:leading-[1.15]">
          {article.h1}
        </h1>
        <p className="mt-4 text-sm text-muted-foreground">
          <time dateTime={article.publishedAt}>
            {formatPublishedDate(article.publishedAt)}
          </time>
          {" · "}
          Светлана Кузнецова
        </p>

        <div className="prose prose-invert mt-10 max-w-none text-base leading-relaxed text-foreground/85 prose-headings:font-semibold prose-headings:tracking-tight prose-h2:mt-12 prose-h2:text-2xl prose-h2:leading-snug sm:prose-h2:text-[1.65rem] prose-p:my-4 prose-li:my-1.5 prose-ul:my-5 prose-blockquote:my-6 prose-blockquote:border-l-[color:var(--lime)]/50 prose-blockquote:pl-4 prose-blockquote:text-foreground/80 prose-blockquote:not-italic prose-a:text-[color:var(--lime)] prose-a:no-underline hover:prose-a:underline prose-strong:text-foreground">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) => (
                <a
                  href={href}
                  className="text-[color:var(--lime)] no-underline hover:underline"
                  {...(href?.startsWith("http")
                    ? { target: "_blank", rel: "noopener noreferrer" }
                    : {})}
                >
                  {children}
                </a>
              ),
            }}
          >
            {article.content}
          </ReactMarkdown>
        </div>

        <aside className="glass mt-14 rounded-3xl p-6 sm:p-8">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
            Похожая задача есть в вашем бизнесе?
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
            Начните с диагностики процесса. Разберём, где сейчас остаётся ручная работа и что
            действительно имеет смысл автоматизировать.
          </p>
          <div className="mt-6">
            <CTAButton event="click_bot_article" source="site_header">
              Пройти диагностику
            </CTAButton>
          </div>
        </aside>
      </article>
    </SiteLayout>
  );
}

function formatPublishedDate(isoDate: string): string {
  const date = new Date(`${isoDate}T12:00:00+05:00`);
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Yekaterinburg",
  }).format(date);
}
