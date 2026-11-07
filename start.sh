
#!/usr/bin/env bash
set -Eeuo pipefail

cd /usr/src/app

PYTHON="/usr/src/app/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    echo "ERROR: Python virtualenv interpreter missing: $PYTHON" >&2
    exit 1
fi

echo "Python version:"
"$PYTHON" --version

echo "Running application updater..."
"$PYTHON" /usr/src/app/update.py

echo "Starting Telegram bot..."
exec "$PYTHON" -m bot
