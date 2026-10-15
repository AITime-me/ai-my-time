# Telegram Edge ingress

The existing Edge remains transport-only. Bot credentials stay on the Edge
host; Core owns identities, business state and durable idempotency. Updates and
personal data are never persisted or logged by Edge.

## Explicit receive mode

Default: `webhook`, preserving the original deployment. Select `polling` with
`EDGE_UPDATE_MODE=polling`, or a release-local `runtime.json` containing exactly:

```json
{"update_mode":"polling"}
```

The environment takes precedence. Invalid/unknown settings fail closed. This
is a deliberate deployment choice, not an automatic transport failover.

Polling uses Telegram's official `getUpdates` through the same existing IPv6
egress. It removes only this Edge's own webhook with
`drop_pending_updates=false`. A foreign webhook is never taken over.
Public relay operations still cannot call `getUpdates` or `deleteWebhook`.
`configureWebhook` returns 409 while polling mode is selected.

The positive next offset is sent to Telegram only after Core durably returns
204. A Core failure stops the batch suffix; a restart replays an unconfirmed
tail instead of discarding it. Core must deduplicate interaction IDs. There
is exactly one poller in the existing service; never run a second consumer.

`/healthz` returns 503 until polling succeeds, when Core rejects an update, or
when no successful poll has happened for 90 seconds. It exposes only mode and
accepted count, never update bodies, tokens or user IDs. Retry logs likewise
contain metadata only. The normal outbound relay runs independently.

## Controlled release / rollback

1. Inspect actual source hashes, current mode and queue state. Preserve the
   previous release, systemd unit, credentials and Caddy/firewall configuration.
2. Stage a pinned release, its explicit mode file and the existing interpreter.
   Atomically switch the existing release pointer and restart the same service.
3. Verify health, actual Core receipt of queued Telegram updates, response
   delivery and absence of queue purging before accepting the release.
4. Never switch back to webhook merely to hide a polling incident. First prove
   Telegram can reach the inbound address. A controlled webhook rollback stops
   the sole poller, selects a webhook release and re-registers the same fixed
   URL/secret with pending updates retained; then proves genuine ingress.
5. Lead Bot route rollback is separate: disable routes on its compatible API
   image, retaining consultation rows and Admin readability. Never downgrade
   old Admin models over nullable-diagnostic consultation records.

## Verification

```sh
python3 -m unittest -q
```

Tests include Core-failure acknowledgement order, batch suffix retry, restart
replay, malformed updates, foreign-webhook refusal, queue preservation, relay
isolation, token-safe logs, stale health and existing outbound/menu behavior.

On 15 October 2026 the existing webhook address was publicly healthy, but
Telegram repeatedly reported a TCP connection timeout and two undelivered
updates. Root UFW inspection showed HTTPS allowed and no matching log blocks;
the precise network-filtering location was not established. Explicit polling
restored both updates without purging the queue or changing firewall, Caddy,
credentials, the systemd unit, Core or its database.

Official protocol: https://core.telegram.org/bots/api#getupdates
