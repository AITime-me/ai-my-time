# Lead Bot dual flow — release contract

## Product

One Telegram identity, one existing database, two independent intake paths.
`business_operations` retains the six canonical business answers and the
existing deep diagnostic provider. `ai_assistant` is deterministic reviewed
copy: work setup → activity → selected tasks → priority → examples → voluntary
consultation. The latter never constructs a model provider, including after
completion or on unstructured text.

Existing v2/acceptance profiles keep their original callbacks and questions.
Selecting business while such a profile remains open resumes it. New business
runs map plain-language labels by index to the unchanged canonical values.
No prompt, price, certificate condition, marketing consent or subscription
default is changed. The certificate is not displayed by the new flow.
Its optional post-result conference block requires both
`LEAD_CONFERENCE_CERTIFICATE_ENABLED=true` and owner-confirmed
`LEAD_CONFERENCE_CERTIFICATE_TEXT`; both are disabled/empty by default. There
are no assumed prices or automatic deductions.

## Persistence and delivery

- `lead_flow_runs` stores version, source, answers, state/status and revision per
  run. Completed results remain historical when the user edits via Back: a new
  run is created. Consultation snapshots do not follow subsequent profile edits.
- `lead_flow_actions` deduplicates interaction IDs under a per-user row lock.
  Ingress additionally uses a PostgreSQL advisory transaction lock per Telegram
  identity, including identity creation. Callbacks check ownership and revision.
- Consultation reuses the existing lifecycle, schedule and bot reply sender.
  A unique flow FK plus serialized active-request guard prevents duplicate
  requests. Outbox uses existing unique keys for owner notification and client
  confirmation. The AI path does not fabricate a diagnostic record.
- Business diagnosis snapshots refer to the originating run. Normal diagnostic
  consultation CTAs also retain this run's immutable context.
- Multi-selection persists every change and displays checkmarks. The existing
  Edge supports sendMessage but not editing; the safe compatible fallback is a
  fresh keyboard per accepted change, not an unverified Edge protocol extension.
- Direct/unknown start parameters are attributed as direct, never conference.
  Website allowlisted deep links and Radar intent retain existing attribution.
  Conference aliases: `conference_2026`, `conference-main`, `qr_conf_main`.
- Admin offers context, contact/Telegram ID, history, analytics and audience
  filters. These filters do not bypass existing broadcast eligibility gates.

## Verification

Use an explicitly disposable PostgreSQL database whose name contains
`ai_my_time_test`; never point the integration suite at production. Existing
tests perform TRUNCATE and migration tests replace the test schema.

```
alembic upgrade head
pytest -q tests
```

`test_lead_dual_flow.py` covers all seven task results via authenticated webhook,
three work setups, zero provider construction, direct attribution, duplicate
start/callbacks, multi-select/deselect, Other input, foreign run IDs, concurrent
consultation requests, Admin projection and analytics, unchanged consent, run
history and legacy v2 continuation with the feature enabled.
`test_dual_flow_migration.py` proves legacy preservation and guarded rollback.
Reviewed UI text is frozen in `tests/fixtures/lead_dual_copy_v1.json`.

Local browser acceptance uses synthetic users and no sending worker. It covers
login, protected analytics, both consultation rows, contact without username,
bot-reply enqueue and AI audience filter. Evidence: repository
`docs/evidence/lead-dual-flow/` (test data only).

## Rollout and rollback

1. Record live source/image SHAs, revision and health; preserve any local changes.
   Back up PostgreSQL with restricted file permissions and prove isolated restore.
2. Build a pinned candidate before altering production. Apply revision
   `20261015_27` with a 5-second lock timeout and a 60-second statement timeout.
   The revision is additive except relaxing the diagnostic FK's NOT NULL; a
   check still requires a supported actual flow context when diagnosis is absent.
3. Deploy compatible API with `LEAD_DUAL_FLOW_ENABLED=false`. Existing worker
   and Radar worker need not restart: all new outbox items retain kind=message
   and the existing transport contract. Do not recreate PostgreSQL or Edge.
4. Add only explicitly authorized test Telegram IDs to
   `LEAD_DUAL_FLOW_TEST_IDS`; verify actual delivery, duplicate CTA, Admin and
   owner notification. Do not run broadcast smoke or use client IDs as tests.
5. Enable `LEAD_DUAL_FLOW_ENABLED=true` only after acceptance; verify both paths
   and core/worker/Edge/Admin health again. Preserve previous images and backup.

Primary rollback is route flags on the **compatible new image**, retaining all
new records and Admin readability. Do not return to an old API image after
nullable-diagnostic requests exist: its old Admin schema cannot read them.
Migration downgrade explicitly refuses while new runs/actions exist. It is
only for empty disposable validation environments, never a data-loss shortcut.
No flag toggles, test sends or releases are scheduled automatically.
