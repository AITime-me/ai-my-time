## Что строим

Многостраничный сайт-визитка эксперта Светланы Кузнецовой и проекта AI My Time на TanStack Start + Tailwind v4 + Lovable Cloud (Supabase). С админкой, заявками, BotWidget, заготовкой под Яндекс.Метрику и SEO.

## Этапы

### 1. Дизайн-система (src/styles.css)
- Палитра: графит `#0E1512`, тёмно-зелёный, хвойный, шалфейный, мягкий лайм-акцент, молочный, белый.
- Токены `--background`, `--foreground`, `--primary` (хвойный), `--accent` (лайм), `--card` с glass-эффектом, `--glow` (зелёное свечение), градиенты, тени.
- Sans-serif (Manrope или Geist через `<link>` в `__root.tsx`).
- Кастомные утилиты: `.glass`, `.glow`, hover, плавное появление при скролле.

### 2. Включаем Lovable Cloud
Создаём таблицы: `leads`, `services`, `cases`, `faq`, `site_settings`, `legal_pages`. RLS + GRANTы по правилам. Роли через отдельную `user_roles` + `has_role()`. Сидим начальные значения services/cases/faq/legal/site_settings через миграцию.

### 3. Глобальные компоненты
- `Header` (лого «Светлана Кузнецова · AI My Time», меню, CTA «Обсудить задачу», бургер на мобиле).
- `Footer` (контакты, ссылки, копирайт, ссылки на политику/оферту).
- `BotWidget` (плавающая кнопка справа снизу, тянет `bot_link` из `site_settings` через публичный server fn).
- `CTAButton` (использует `BOT_LINK`, шлёт события `ym(...)` и `gtag(...)`, если подключены).
- `Analytics` инжект в `__root.tsx` — добавляет Метрику/GA при наличии ID, не ломается без них.
- `Reveal` обёртка для анимации появления.

### 4. Страницы
- `/` — все 13 блоков из ТЗ (hero со схемой Клиент→сайт→AI→заявка→админка→собственник, боли, что создаю, как работает, не «бот ради бота», для кого, примеры, почему со мной, AI My Time, инструменты-бейджи, FAQ из БД, манифест, финальный CTA).
- `/services` + 5 дочерних страниц услуг (`ai-assistant`, `site-with-ai`, `automation`, `mini-crm`, `ai-audit`) — контент тянем из таблицы `services`, fallback на статический контент.
- `/cases` — карточки «решения, которые можно собрать», без фейковых цифр.
- `/about` — про Светлану, графический блок-плейсхолдер вместо стоковой фотки.
- `/contacts` — основной CTA на бота + резервная форма (валидация zod, чекбокс согласия, server fn `submitLead` сохраняет в `leads`).
- `/privacy`, `/offer` — контент из `legal_pages`.
- `/admin` — закрытая (роль `admin`), вкладки: Дашборд, Заявки, Услуги, Кейсы, FAQ, Контакты, Бот, Аналитика, Юр.страницы, SEO.

### 5. SEO
- `head()` на каждой странице: уникальные title/description/og по тексту из ТЗ.
- `sitemap.xml` route + `robots.txt`.
- JSON-LD Organization на root, Service на страницах услуг, FAQPage на главной.

### 6. Аналитика
- В `__root.tsx` подтягиваем `site_settings`. Если `analytics_enabled` + есть `yandex_metrika_id` — инжектим счётчик. Аналогично GA.
- Утилита `trackEvent(name)` — безопасный вызов `ym`/`gtag` если есть.
- События: `click_bot_*`, `open_bot_widget`, `submit_contact_form`, `click_telegram`, `click_email`, `click_service_card`, `click_case_card`.

### 7. Админка
- Auth: email/password через Supabase. Гейт `_authenticated/route.tsx` (управляется интеграцией). Дополнительная проверка роли `admin`.
- Страница `/auth` — вход.
- Все CRUD через защищённые server functions с `requireSupabaseAuth` + `has_role('admin')`.
- Простые формы (shadcn), таблица заявок с фильтрами/поиском.

### 8. Технические детали
- `BOT_LINK` хранится в `site_settings.bot_link`, отдаётся публичным server fn (`anon` SELECT по одной строке безопасных полей), фронт кеширует через React Query.
- Все CTA кнопки идут на `bot_link || "#"`.
- Адаптив, lazy-loading изображений, lucide-react иконки, framer-motion для анимаций.

## Допущения
- `BOT_LINK` = `#` по умолчанию.
- `YANDEX_METRIKA_ID` пустой по умолчанию.
- Юр. тексты — шаблонные, с пометкой о необходимости адаптации.
- Кейсы — «что можно собрать», без фейковых цифр и отзывов.
- Первый зарегистрированный пользователь не получает роль `admin` автоматически — роль выдаётся вручную через SQL/Cloud UI (скажу пользователю как).

Подтверди — и я начну строить.
