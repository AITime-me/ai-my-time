# Closed Diagnostic AI acceptance restart

This mechanism is disabled by default. It is not a Telegram product feature,
and normal `/start` can never restart a completed v2 diagnostic.

After a separately approved release, an operator may issue exactly one short-
lived link for an existing Telegram identity with:

```bash
python -m scripts.issue_diagnostic_acceptance_link \
  --telegram-user-id '<existing identity>' \
  --bot-username '<production bot username>' \
  --ttl-minutes 30
```

The command prints the link once. Only its SHA-256 digest is stored. The first
valid use by that identity atomically consumes the grant and creates a separate
acceptance v2 flow at the first profile card. Repeated, expired or foreign use
is a no-op.

The existing `LeadBotSession` is not changed. Every `DiagnosticSession`, report,
turn and diagnostic snapshot also stays unchanged. The grant records the
historical lead-flow projection as an audit snapshot. Do not issue a link
until the owner explicitly approves the live manual acceptance test.
