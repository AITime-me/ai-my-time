#!/bin/sh
set -eu

for setting in DATABASE_URL TELEGRAM_BOT_TOKEN TELEGRAM_LEAD_WEBHOOK_SECRET TELEGRAM_EDGE_CORE_SECRET TELEGRAM_EDGE_INBOUND_SECRET; do
    file_var="${setting}_FILE"
    eval "secret_file=\${$file_var:-}"
    if [ -n "$secret_file" ]; then
        test -r "$secret_file"
        value=$(cat "$secret_file")
        test -n "$value"
        export "$setting=$value"
    fi
done

exec "$@"
