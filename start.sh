#!/usr/bin/env bash
set -euo pipefail

cd /usr/src/app

PYTHON="/usr/src/app/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    echo "ERROR: base image virtualenv interpreter missing: $PYTHON" >&2
    exit 1
fi

exec "$PYTHON" -m update
