import parserNedvizhimostiContent from "@/content/articles/parser-nedvizhimosti-amocrm.md?raw";

export type ArticleCard = {
  slug: string;
  title: string;
  description: string;
  label?: string;
};

export type Article = ArticleCard & {
  h1: string;
  seoTitle: string;
  seoDescription: string;
  eyebrow: string;
  publishedAt: string;
  content: string;
};

/** Published articles available on the site. */
export const articles: Article[] = [
  {
    slug: "parser-nedvizhimosti-amocrm",
    title: "Риелтор больше не ищет объекты",
    description:
      "Как мы связали парсер недвижимости с amoCRM и сделали так, чтобы подходящие объекты сами попадали в работу агента.",
    label: "Недвижимость · amoCRM",
    h1: "Риелтор больше не ищет объекты: как мы связали парсер недвижимости с amoCRM",
    seoTitle: "Парсер недвижимости + amoCRM: автоматизация подбора объектов | AI My Time",
    seoDescription:
      "Как автоматизировать подбор объектов недвижимости для покупателей и передавать подходящие объявления с ЦИАН, Авито, Домклик и других площадок в amoCRM. Парсер недвижимости, мониторинг цен и автоматизация агентства недвижимости.",
    eyebrow: "Статья · Недвижимость / автоматизация",
    publishedAt: "2026-10-05",
    content: parserNedvizhimostiContent,
  },
];

export function getArticleBySlug(slug: string): Article | undefined {
  return articles.find((article) => article.slug === slug);
}

export function isArticleSlug(slug: string): boolean {
  return articles.some((article) => article.slug === slug);
}

export function articlePath(slug: string): string {
  return `/articles/${slug}`;
}
