# A.I. My Time Core API

Минимальный FastAPI-каркас будущего Telegram-контура.

В нём есть health-check, начальная Alembic-схема и изолированная бизнес-логика
первого шага `conference_2026`: стабильный Telegram ID → внутренний user_id →
источник → запись конференции. Telegram webhook, токены, LLM и production
deployment пока намеренно не подключены.
