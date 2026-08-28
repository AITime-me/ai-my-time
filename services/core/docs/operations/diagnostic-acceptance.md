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
valid use by that identity atomically consumes the grant and opens the first
v2 profile card. Repeated, expired or foreign use is a no-op.

The current lead-flow projection is restarted, while every `DiagnosticSession`,
report, turn and diagnostic snapshot stays unchanged. The grant records the
pre-restart lead-flow projection as an audit snapshot. Do not issue a link
until the owner explicitly approves the live manual acceptance test.
