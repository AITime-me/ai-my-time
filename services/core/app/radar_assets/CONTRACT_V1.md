# Radar Reader–Core Contract v1

Scope: versioned **wire** DTOs, fixtures, JSON Schema, and fingerprint helpers only.
No DB tables, migrations, HTTP side effects, Telethon, journal, or delivery in this slice.

## Canonical identity

Telegram numeric IDs travel as **decimal strings** on the wire (never float).
Python domain code may use `int` later; float is forbidden.

Source/message identity:

- `connector = telegram`
- `source_id` (from manifest)
- `peer_type`
- `peer_id`
- `message_id`

Future Core semantic Signal identity:

- `tenant + source + message_id`

**Tenant is never accepted from Reader.** Core binds tenant via credential.

## Timestamps

All contract timestamps are timezone-aware and canonicalized to UTC.
Naive datetimes are rejected (same rule as Core appointment helpers).

## Revision fingerprint

SHA-256 over UTF-8 JSON with sorted keys and compact separators.
Included / excluded fields: see `app.schemas.radar_fingerprint`.

If Reader sends `revision_fingerprint`, Core recomputes and mismatches fail as
contract validation (`invalid_contract` / fingerprint mismatch).

Fingerprint does **not** use Python `hash()`.

## Transport retry vs semantic replay

A. **Transport idempotency** — same `observation_id` may retry only with the
   same immutable payload. Same id + different payload → future `409
   idempotency_conflict`.

B. **Semantic replay** — different `observation_id` with the same semantic
   Telegram revision / fingerprint must not create a new Signal revision.
   Slice 1 documents this; DB dedupe is deferred.

## ACK meaning

`accepted` = durable **receipt** committed by Core.
It does **not** mean matched, Signal created, fresh, delivered, Neo-approved,
or lead qualified.

`duplicate` = receipt already exists for this transport observation.

## Security exclusions

Payloads must not contain session data, bot/user tokens, `api_id`/`api_hash`,
`access_hash`, phone numbers, credentials, tenant overrides, or raw Telegram
objects. DTOs use `extra="forbid"`.

## Payload size

Maximum serialized Observation body: **65536 bytes** (`64 * 1024`), reused from
the existing Core internal consultant body bound (`MAX_BODY_BYTES`).

## Compatibility

Unknown / unsupported `schema_version` **fails closed**.

## Monitoring capability

Manifest `monitoring_capability`: `realtime` | `history_only` | `unverified`.
Search rules stay Core-side and are not shipped in the manifest.
