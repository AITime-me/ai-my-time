# A.I. My Time Core API

Минимальный FastAPI-каркас будущего Telegram-контура.

На этом шаге есть только liveness endpoint `GET /healthz`. Нет базы данных,
webhook, токенов, AI-провайдеров и внешней отправки сообщений.

Следующие контролируемые этапы: PostgreSQL/Alembic, единая identity, durable
Telegram ingress и только затем сценарий `conference_2026`.
