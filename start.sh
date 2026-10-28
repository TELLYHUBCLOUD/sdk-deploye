#!/usr/bin/env bash
set -Eeuo pipefail

# Heroku runs web dynos with DYNO set. An explicit mode switch also permits
# local verification of the same safety guard without deploying to Heroku.
if [[ -n "${DYNO:-}" ]] || [[ "${HEROKU_POLICY_MODE:-}" =~ ^(1|true|yes|on)$ ]]; then
    export HEROKU_POLICY_MODE=1
    export DISABLE_TORRENTS=true
    export DISABLE_LEECH=true
    export DISABLE_SEED=true
    export DISABLE_BULK=true
    export DISABLE_MULTI=true
    export AUTO_LEECH=false
    export AUTO_MIRROR=false
    export AUTO_YT_LEECH=false
    export AUTO_YTDL=false
    export AUTO_QBLEECH=false
    export AUTO_QBMIRROR=false
    export AUTO_JDLEECH=false
    export AUTO_JDMIRROR=false
    export AUTO_GDL_LEECH=false
    export AUTO_GDL_MIRROR=false
    export SEARCH_PLUGINS='[]'
    export SEARCH_API_LINK=''
    export SEARCH_LIMIT=0
    export RSS_CHAT=''
    export RCLONE_SERVE_URL=''
    export RESOLVER_ENABLED=false
    export RESOLVER_UI=false
    export AUTHORIZED_CHATS=''
    export SUDO_USERS=''
    export BOT_MAX_TASKS=1
    export USER_MAX_TASKS=1
    export QUEUE_ALL=2
    export QUEUE_DOWNLOAD=1
    export QUEUE_UPLOAD=1
    export HYPER_THREADS=1
    echo "[entrypoint] Heroku policy safety mode enabled; high-risk features restricted."
fi

# Fetch and run the bot in a fresh, writable runtime directory. The SDK
# base image deliberately protects /usr/src/app with ownership/mode settings;
# Heroku uses an arbitrary non-root UID, so do not git-reset source over image
# files there. /tmp is ephemeral on Heroku and the runtime UID owns this tree.
RUNTIME_DIR=/tmp/telly-runtime
mkdir -p "$RUNTIME_DIR"
cd "$RUNTIME_DIR"
export PYTHONPATH="$RUNTIME_DIR:/usr/src/app"

# The Dockerfile creates /opt/venv and puts it first on PATH. Do not source
# .venv: this wrapper's Dockerfile creates /opt/venv instead.
UPDATER=/usr/local/bin/telly-updater.py
[[ -f "$UPDATER" ]] || UPDATER=/usr/src/app/update.py
python3 "$UPDATER"

if [[ "${HEROKU_POLICY_MODE:-0}" == "1" ]]; then
    PATCHER=/usr/local/bin/heroku_policy_patch.py
    [[ -f "$PATCHER" ]] || PATCHER=/usr/src/app/heroku_policy_patch.py
    python3 "$PATCHER"
fi

# Support the two bot layouts that this deployment wrapper may fetch.
if [[ -f /usr/src/app/app/main.py ]]; then
    exec python3 -m app.main
elif [[ -f /usr/src/app/bot/__main__.py ]]; then
    exec python3 -m bot
else
    echo "[entrypoint] ERROR: no supported app/main.py or bot/__main__.py found." >&2
    exit 78
fi
