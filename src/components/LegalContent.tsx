import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function LegalContent({ content }: { content?: string | null }) {
  if (!content) return null;
  return (
    <article className="prose prose-invert mt-8 max-w-none text-base text-foreground/85 prose-headings:font-semibold prose-headings:tracking-tight prose-h1:mt-5 prose-h1:text-4xl prose-h1:leading-tight prose-h2:mt-10 prose-h2:text-2xl prose-h3:mt-6 prose-h3:text-xl prose-p:my-3 prose-li:my-1 prose-a:text-[color:var(--lime)] prose-a:no-underline hover:prose-a:underline prose-strong:text-foreground">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </article>
  );
}