# Demand Radar MVP — operator path

## Core pieces already in code

1. Headless Admin config API (`/admin/radar/...`)
2. Reader manifest + observation ingress (`/internal/radar/v1/...`)
3. Deterministic matcher + durable Signal
4. Isolated Radar alert outbox + `scripts/run_radar_alert_worker.py`
5. Alembic head: `20261010_26`

## One-time bootstrap

```bash
export DATABASE_URL=...
export RADAR_MVP_OWNER_EMAIL=owner@example.com
export RADAR_READER_CREDENTIALS_PATH=/secure/radar-reader-credentials.json
python -m scripts.bootstrap_radar_mvp
```

## Configure via Admin API (no UI)

With an Admin browser session + `ADMIN_TRUSTED_ORIGIN`:

1. `POST /admin/radar/sources` — Telegram source (`peer_type`, positive `peer_id`, `reader_id`)
2. `PATCH /admin/radar/sources/{id}` — set `is_approved=true`, `monitoring_capability=realtime`
3. `POST /admin/radar/destinations` — `bot_binding_key` + Svetlana `chat_id`
4. `POST /admin/radar/destinations/{id}/verify`
5. `POST /admin/radar/profiles` + version with include terms + source/destination bindings
6. `POST /admin/radar/profiles/{id}/activate`

## Radar Bot token file

JSON mapping binding key → bot token:

```json
{ "radar-owner": "123456:ABC..." }
```

```bash
export RADAR_ALERT_BOT_TOKENS_PATH=/secure/radar-alert-bots.json
python -m scripts.run_radar_alert_worker
```

## Reader continuous runtime

```bash
export RADAR_CORE_BASE_URL=https://core.example
export RADAR_READER_CREDENTIAL_KEY_ID=...
export RADAR_READER_CREDENTIAL_SECRET=...
demand-radar-telegram run
```
