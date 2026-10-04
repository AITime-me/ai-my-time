import { getActiveCases } from "@/data/cases";
import { faqItems } from "@/data/faq";
import { getActiveServices } from "@/data/services";
import { getSolutionBySlug, type SolutionSlug } from "@/data/solutions";

export const RADAR_DEFINITION =
  "Радар спроса — направление AI My Time, где мы ищем и анализируем реальные запросы людей и бизнеса, чтобы видеть уже существующий спрос и понимать, где есть потенциальные клиенты.";

/**
 * FAQ answers that point to the diagnostic Telegram bot must not reach the
 * consultant; the site consultant never routes visitors there.
 */
const FAQ_OVERRIDES: Record<string, string> = {
  "6": "С разбора процесса, а не с выбора технологии. Сначала смотрим, как работа устроена сейчас, где возникают разрывы и лишняя ручная работа, и находим первый участок, который имеет смысл упростить или автоматизировать. Обсудить конкретную ситуацию можно с командой в Telegram-канале.",
};

const SCENARIO_SLUGS: SolutionSlug[] = [
  "online-booking",
  "detailing-booking",
  "avito-leads",
  "service-orders",
  "online-orders",
];

function line(label: string, value: string | null | undefined): string {
  return value ? `${label}: ${value}` : "";
}

function block(lines: string[]): string {
  return lines.filter(Boolean).join("\n");
}

function servicesSection(): string {
  return getActiveServices()
    .map((s) =>
      block([
        `- ${s.title}`,
        line("  Суть", s.short_description),
        line("  Для кого", s.audience),
        line("  Что входит", s.includes),
        line("  Результат", s.result),
      ]),
    )
    .join("\n");
}

function scenariosSection(): string {
  return SCENARIO_SLUGS.map((slug) => getSolutionBySlug(slug))
    .filter((s) => s !== undefined)
    .map((s) =>
      block([
        `- ${s.title}`,
        line("  Ситуация клиента", s.quote),
        line("  Как работает", s.intro),
        s.outcomes.length ? `  Что даёт: ${s.outcomes.join(" ")}` : "",
      ]),
    )
    .join("\n");
}

function aiAgentSection(): string {
  const agent = getSolutionBySlug("ai-agent");
  if (!agent) return "";
  return block([
    `- ${agent.title}: ${agent.intro}`,
    agent.heroNote ? `  Важно: ${agent.heroNote}` : "",
    agent.capabilities?.length
      ? `  Возможные направления работы (зависят от подключённых данных и инструментов): ${agent.capabilities.map((c) => c.title).join("; ")}.`
      : "",
  ]);
}

function radarSection(): string {
  const radar = getSolutionBySlug("demand-radar")?.radar;
  return block([
    RADAR_DEFINITION,
    radar ? `Какие запросы и сигналы можно искать (определяется под задачи конкретного бизнеса): ${radar.searchExamples.join("; ")}.` : "",
    radar ? `Ограничение: ${radar.boundaryText}` : "",
    "Статус: сценарий Радара проектируется под задачи конкретного бизнеса. Отдельного готового автоматического Радар-бота как самостоятельного продукта сейчас нет. Радар не рассылает сообщения и не пишет людям сам. Любой контакт с потенциальным клиентом — только после решения владельца.",
    "Где искать: в открытых источниках (публичные каналы, сообщества, площадки), которые выбираются под конкретный бизнес. Конкретный список источников заранее не обещается.",
  ]);
}

function casesSection(): string {
  return getActiveCases()
    .map((c) =>
      block([
        `- ${c.title} (статус: ${c.status ?? "не указан"})`,
        line("  Задача", c.task),
        line("  Решение", c.solution),
      ]),
    )
    .join("\n");
}

function faqSection(): string {
  return faqItems
    .map((item) => `- Вопрос: ${item.question}\n  Ответ: ${(FAQ_OVERRIDES[item.id] ?? item.answer).replace(/\n+/g, " ")}`)
    .join("\n");
}

export function buildKnowledge(): string {
  return [
    "## Кто такие AI My Time",
    "AI My Time проектирует и автоматизирует бизнес-процессы: CRM, AI-сотрудники, интеграции, сайты и цифровые сервисы для работы с клиентами, продажами и аналитикой. Основатель — Светлана Кузнецова.",
    "Подход: сначала разбираем, как работа устроена на самом деле, находим разрывы и лишнюю ручную работу, разделяем работу человека и системы, затем собираем решение под конкретный процесс. Можно начать с одного участка, без перестройки всего бизнеса.",
    "Для кого: малый и растущий бизнес, сервисные компании, эксперты, онлайн-школы, локальный бизнес, онлайн-магазины; в том числе предприниматели, которые всё делают сами.",
    "amoCRM: AI My Time — официальный партнёр программы amoSTART компании amoCRM. Делает настройки и автоматизацию в amoCRM (поля, воронки, права, шаблоны, виджеты, действия, интеграции, аналитика). На сайте есть демонстрационные сценарии с передачей заказов и заявок в amoCRM. Это не значит, что любой проект обязательно строится только на amoCRM.",
    "",
    "## Услуги",
    servicesSection(),
    "",
    "## Примеры решений (демонстрационные сценарии на сайте)",
    scenariosSection(),
    "",
    "## AI-агент для бизнеса",
    aiAgentSection(),
    "",
    "## Радар спроса",
    radarSection(),
    "",
    "## Кейсы и проекты (называть только их и только с указанным статусом)",
    casesSection(),
    "",
    "## Частые вопросы",
    faqSection(),
    "",
    "## Цены и сроки",
    "Публичных цен и фиксированных сроков нет. Стоимость и сроки зависят от задачи и объёма решения и обсуждаются после разбора конкретного процесса.",
    "",
    "## Связь с командой",
    "Продолжить общение и обсудить конкретную задачу можно в Telegram-канале AI My Time. В окне чата есть кнопка «Перейти в Telegram» — ссылку показывает интерфейс, сам ссылки не пиши.",
    "Телефон и email на сайте не указаны; оставлять контакты в этом чате не нужно.",
  ].join("\n");
}
