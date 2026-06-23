
-- ============== ROLES ==============
CREATE TYPE public.app_role AS ENUM ('admin', 'user');

CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role app_role NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, role)
);
GRANT SELECT ON public.user_roles TO authenticated;
GRANT ALL ON public.user_roles TO service_role;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own roles" ON public.user_roles FOR SELECT TO authenticated USING (user_id = auth.uid());

CREATE OR REPLACE FUNCTION public.has_role(_user_id uuid, _role app_role)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role = _role)
$$;

-- ============== UPDATED_AT ==============
CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS trigger LANGUAGE plpgsql SET search_path = public AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END $$;

-- ============== LEADS ==============
CREATE TABLE public.leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  name TEXT NOT NULL,
  phone_or_telegram TEXT,
  email TEXT,
  business_area TEXT,
  task TEXT,
  message TEXT,
  source TEXT DEFAULT 'contact_form',
  status TEXT NOT NULL DEFAULT 'new',
  admin_comment TEXT
);
GRANT INSERT ON public.leads TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.leads TO authenticated;
GRANT ALL ON public.leads TO service_role;
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can submit a lead" ON public.leads FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Admins can view leads" ON public.leads FOR SELECT TO authenticated USING (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins can update leads" ON public.leads FOR UPDATE TO authenticated USING (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins can delete leads" ON public.leads FOR DELETE TO authenticated USING (public.has_role(auth.uid(), 'admin'));

-- ============== SERVICES ==============
CREATE TABLE public.services (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  h1 TEXT,
  seo_title TEXT,
  seo_description TEXT,
  short_description TEXT,
  full_description TEXT,
  audience TEXT,
  includes TEXT,
  result TEXT,
  cta_text TEXT DEFAULT 'Обсудить задачу',
  sort_order INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT ON public.services TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON public.services TO authenticated;
GRANT ALL ON public.services TO service_role;
ALTER TABLE public.services ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can read active services" ON public.services FOR SELECT TO anon, authenticated USING (is_active OR public.has_role(auth.uid(),'admin'));
CREATE POLICY "Admins manage services" ON public.services FOR ALL TO authenticated USING (public.has_role(auth.uid(),'admin')) WITH CHECK (public.has_role(auth.uid(),'admin'));
CREATE TRIGGER trg_services_updated BEFORE UPDATE ON public.services FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============== CASES ==============
CREATE TABLE public.cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  category TEXT,
  task TEXT,
  solution TEXT,
  result TEXT,
  image_url TEXT,
  seo_title TEXT,
  seo_description TEXT,
  sort_order INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT ON public.cases TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON public.cases TO authenticated;
GRANT ALL ON public.cases TO service_role;
ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can read active cases" ON public.cases FOR SELECT TO anon, authenticated USING (is_active OR public.has_role(auth.uid(),'admin'));
CREATE POLICY "Admins manage cases" ON public.cases FOR ALL TO authenticated USING (public.has_role(auth.uid(),'admin')) WITH CHECK (public.has_role(auth.uid(),'admin'));
CREATE TRIGGER trg_cases_updated BEFORE UPDATE ON public.cases FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============== FAQ ==============
CREATE TABLE public.faq (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  category TEXT,
  sort_order INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT ON public.faq TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON public.faq TO authenticated;
GRANT ALL ON public.faq TO service_role;
ALTER TABLE public.faq ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can read active faq" ON public.faq FOR SELECT TO anon, authenticated USING (is_active OR public.has_role(auth.uid(),'admin'));
CREATE POLICY "Admins manage faq" ON public.faq FOR ALL TO authenticated USING (public.has_role(auth.uid(),'admin')) WITH CHECK (public.has_role(auth.uid(),'admin'));
CREATE TRIGGER trg_faq_updated BEFORE UPDATE ON public.faq FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============== SITE SETTINGS ==============
CREATE TABLE public.site_settings (
  id INT PRIMARY KEY DEFAULT 1,
  bot_link TEXT DEFAULT '#',
  bot_widget_enabled BOOLEAN NOT NULL DEFAULT true,
  bot_widget_text TEXT DEFAULT 'Задать вопрос AI-помощнику',
  main_cta_text TEXT DEFAULT 'Обсудить задачу',
  yandex_metrika_id TEXT DEFAULT '',
  google_analytics_id TEXT DEFAULT '',
  analytics_enabled BOOLEAN NOT NULL DEFAULT false,
  telegram TEXT DEFAULT '',
  email TEXT DEFAULT '',
  phone TEXT DEFAULT '',
  social_links JSONB DEFAULT '{}'::jsonb,
  site_title TEXT DEFAULT 'Светлана Кузнецова — AI My Time',
  site_description TEXT DEFAULT 'Сайты, AI-помощники, боты и автоматизация для малого бизнеса',
  og_image TEXT DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT single_row CHECK (id = 1)
);
GRANT SELECT ON public.site_settings TO anon, authenticated;
GRANT UPDATE ON public.site_settings TO authenticated;
GRANT ALL ON public.site_settings TO service_role;
ALTER TABLE public.site_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can read settings" ON public.site_settings FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Admins update settings" ON public.site_settings FOR UPDATE TO authenticated USING (public.has_role(auth.uid(),'admin')) WITH CHECK (public.has_role(auth.uid(),'admin'));
CREATE TRIGGER trg_site_settings_updated BEFORE UPDATE ON public.site_settings FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
INSERT INTO public.site_settings (id) VALUES (1);

-- ============== LEGAL PAGES ==============
CREATE TABLE public.legal_pages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT ON public.legal_pages TO anon, authenticated;
GRANT UPDATE ON public.legal_pages TO authenticated;
GRANT ALL ON public.legal_pages TO service_role;
ALTER TABLE public.legal_pages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can read legal" ON public.legal_pages FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Admins update legal" ON public.legal_pages FOR UPDATE TO authenticated USING (public.has_role(auth.uid(),'admin')) WITH CHECK (public.has_role(auth.uid(),'admin'));
CREATE TRIGGER trg_legal_updated BEFORE UPDATE ON public.legal_pages FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============== SEED CONTENT ==============
INSERT INTO public.services (slug, title, h1, seo_title, seo_description, short_description, full_description, audience, includes, result, sort_order) VALUES
('ai-audit', 'AI/digital-разбор бизнеса', 'AI/digital-разбор бизнеса',
 'AI-разбор бизнеса — с чего начать внедрение AI и автоматизации',
 'Разберём, где бизнесу не хватает людей, времени и порядка, и найдём первый процесс, который можно передать AI или автоматизировать.',
 'Смотрим, где не хватает людей, времени и порядка. Находим, что можно упростить, передать AI или связать в понятный процесс.',
 'Если вы понимаете, что AI и автоматизация нужны, но не понимаете, куда их поставить, начните с разбора.',
 'Предпринимателям, которые чувствуют хаос, но не понимают, с чего начать.',
 'Путь клиента, заявки, ответы, запись, повторяющиеся вопросы, ручные действия, точки хаоса.',
 'Карта процессов и понятный первый шаг.', 1),
('site-with-ai', 'Сайт с AI-помощником', 'Сайт с AI-помощником',
 'Сайт с AI-помощником для малого бизнеса',
 'Создание сайта с AI-помощником: структура, тексты, бот для заявок, админка и аналитика для малого бизнеса.',
 'Не просто страница, а место, где клиент может получить консультацию, понять предложение и сделать следующий шаг.',
 'Сайт должен не просто рассказывать о вас. Он должен вести клиента: объяснить, ответить, помочь выбрать и привести к заявке.',
 'Услугам, экспертам, локальному бизнесу, онлайн-магазинам.',
 'Структура сайта, SEO-тексты, дизайн, адаптив, бот/виджет, подготовка к Метрике, админка, юридические страницы.',
 'Сайт, структура, тексты, бот / виджет, подготовка к заявкам и аналитике.', 2),
('ai-assistant', 'AI-помощник для бизнеса', 'AI-помощник для бизнеса',
 'AI-помощник для бизнеса — заявки, ответы и консультации',
 'AI-помощник для малого бизнеса отвечает на частые вопросы, уточняет запросы, собирает заявки и передаёт данные человеку.',
 'Отвечает на частые вопросы, уточняет запрос, собирает данные и передаёт сложные ситуации человеку.',
 'AI-помощник отвечает на частые вопросы, уточняет запрос, собирает данные и передаёт сложные ситуации человеку.',
 'Бизнесу, где много типовых вопросов и консультаций.',
 'База знаний, сценарии, форма заявки, передача менеджеру, бот или виджет на сайте.',
 'Быстрее ответы, меньше ручной рутины, подготовленные заявки.', 3),
('automation', 'Автоматизация малого бизнеса', 'Автоматизация малого бизнеса',
 'Автоматизация малого бизнеса — заявки, ответы и ручная рутина',
 'Помогаю автоматизировать один процесс в малом бизнесе: заявки, ответы, запись, уведомления, таблицы и отчёты без цифровой каши.',
 'Берём один повторяющийся кусок работы и выводим его из ручного режима.',
 'Автоматизация — это когда повторяющиеся задачи уходят из ручного режима. Без цифровой каши и ремонта бизнеса на полгода.',
 'Тем, кто хочет начать без полной перестройки бизнеса.',
 'Заявки, ответы клиентам, запись, уведомления, таблицы, отчёты, напоминания, передача данных.',
 'Одна задача работает быстрее, понятнее и без постоянного ручного контроля.', 4),
('mini-crm', 'Мини-CRM и админка', 'Мини-CRM и админка для малого бизнеса',
 'Мини-CRM и админка для малого бизнеса',
 'Мини-CRM для заявок, клиентов, статусов и простой аналитики. Помогает навести порядок в обращениях и ручных процессах.',
 'Место, где видны клиенты, заявки, статусы и история.',
 'Когда клиенты, заявки и статусы живут в разных чатах, бизнес держится не на системе, а на хорошей памяти.',
 'Бизнесу, где заявки лежат в чатах, таблицах и памяти сотрудников.',
 'Заявки, клиенты, контакты, статусы, комментарии, услуги, источники заявок.',
 'Порядок вместо поиска «а где у нас этот клиент?».', 5);

INSERT INTO public.cases (title, category, task, solution, result, sort_order) VALUES
('Сайт для студии услуг с AI-помощником', 'Сайт + AI',
 'Помочь клиенту понять услуги, задать вопросы и дойти до записи.',
 'Сайт, структура, блок услуг, будущий бот, админка, Метрика.',
 'Понятный путь клиента от первого касания до заявки.', 1),
('Чек-лист или тест для аудитории', 'Лид-магнит',
 'Вовлечь человека и собрать ответы.',
 'Интерактивная форма, результат, сохранение ответов в админке.',
 'Тёплые контакты с понятным интересом.', 2),
('Мини-CRM для заявок', 'CRM',
 'Навести порядок в клиентах, статусах и обращениях.',
 'Админка, таблица заявок, фильтры, статусы, комментарии.',
 'Меньше поиска по чатам, понятная воронка.', 3),
('AI-администратор', 'AI',
 'Разгрузить человека от повторяющихся вопросов.',
 'База знаний, сценарии, бот, передача заявки.',
 'Администратор разгружен, клиент не остаётся без ответа.', 4),
('AI-аналитик для собственника', 'Аналитика',
 'Показывать, что происходит с заявками и клиентами.',
 'Сводки, отчёты, повторяющиеся вопросы, точки улучшения.',
 'Решения по цифрам, а не по ощущениям.', 5),
('Сайт-визитка с ботом', 'Сайт',
 'Объяснить услуги и довести клиента до диалога с ботом.',
 'Лендинг с SEO, BotWidget, форма заявки, админка.',
 'Сайт работает как точка пути клиента, а не просто визитка.', 6);

INSERT INTO public.faq (question, answer, sort_order) VALUES
('Клиенты будут общаться с AI?', 'Клиенты не любят бесполезных ботов. Но если помощник быстро отвечает, уточняет и помогает, он не раздражает. Особенно когда человек подключается там, где нужен человек.', 1),
('AI не будет звучать как робот?', 'Плохо настроенный AI видно сразу. Хорошо настроенный помощник работает по базе знаний, тону бренда и сценариям.', 2),
('Это сложно?', 'Вам не нужно разбираться в технологиях. Мы начинаем с одной понятной задачи и собираем решение вокруг неё.', 3),
('Это дорого?', 'Не нужно автоматизировать весь бизнес сразу. Можно начать с одного процесса, который каждый день съедает время.', 4),
('AI заменит сотрудников?', 'Нет. Он забирает повторяющуюся часть, чтобы человек занимался тем, где правда нужен человек.', 5),
('Можно начать без большого проекта?', 'Да. Первый шаг — AI/digital-разбор. Смотрим, где не хватает людей, времени и порядка, и выбираем один процесс для старта.', 6);

INSERT INTO public.legal_pages (type, title, content) VALUES
('privacy', 'Политика конфиденциальности',
'Настоящая Политика конфиденциальности описывает, как обрабатываются персональные данные посетителей сайта проекта AI My Time (далее — «Сайт»).

1. Какие данные мы собираем
- имя;
- телефон или Telegram;
- email;
- сфера бизнеса;
- комментарий;
- данные, передаваемые через формы и через бота.

2. Цели обработки
- ответ на ваш запрос;
- консультация по услугам;
- передача данных эксперту проекта AI My Time;
- ведение клиентской базы.

3. Передача третьим лицам
Данные не передаются третьим лицам, кроме случаев, когда это требуется по закону.

4. Хранение и защита
Данные хранятся в защищённой базе. Доступ имеют только администраторы проекта.

5. Права пользователя
Вы можете запросить удаление или изменение своих данных, написав на контактный email сайта.

ВАЖНО: текст шаблонный и должен быть адаптирован под реальные реквизиты, способ и сроки хранения, контактные данные оператора и применимое законодательство.'),
('offer', 'Договор оферты',
'Настоящий документ является публичной офертой на оказание digital-услуг в рамках проекта AI My Time.

1. Предмет договора
Исполнитель оказывает Заказчику услуги:
- разработка сайтов;
- настройка AI-помощников и ботов;
- автоматизация процессов;
- консультации и digital-разбор;
- настройка мини-CRM и админок;
- сопровождение и доработки.

2. Порядок работы
- стороны согласуют задачу;
- определяют объём и стоимость;
- Заказчик вносит предоплату;
- Исполнитель выполняет работы поэтапно;
- после приёмки производится итоговый расчёт.

3. Стоимость и оплата
Стоимость согласуется индивидуально и фиксируется в переписке или счёте.

4. Ответственность сторон
Исполнитель не отвечает за бизнес-результаты Заказчика, которые зависят от факторов вне зоны разработки.

5. Прочие условия
Все споры решаются переговорами. Принимая услуги, Заказчик соглашается с условиями оферты.

ВАЖНО: текст шаблонный. Необходимо адаптировать под реальные реквизиты, порядок оплаты, сроки, ответственность и условия работы.');
