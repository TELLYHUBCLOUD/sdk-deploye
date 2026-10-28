#!/usr/bin/env python3
"""Apply a transparent, fail-closed Heroku policy guard to the fetched bot.

The deployment wrapper fetches its bot source at startup. This small patcher
runs after that fetch and before the bot starts, so upstream files or persisted
MongoDB settings cannot silently re-enable high-risk features on Heroku.
"""

from os import environ
from pathlib import Path
import sys

MODE_VALUES = {"1", "true", "yes", "on"}
mode = environ.get("HEROKU_POLICY_MODE", "").strip().lower()
if not environ.get("DYNO") and mode not in MODE_VALUES:
    raise SystemExit(0)

targets = (
    Path("bot/core/config_manager.py"),
    Path("app/core/config_loader.py"),
)
target = next((candidate for candidate in targets if candidate.is_file()), None)
if target is None:
    print(
        "[heroku-policy] ERROR: no supported Config module found; refusing to "
        "start without the safety guard.",
        file=sys.stderr,
    )
    raise SystemExit(78)

source = target.read_text(encoding="utf-8")
marker = "# BEGIN TELLY_HEROKU_POLICY_GUARD (managed by sdk-deploye)"
if marker in source:
    print(f"[heroku-policy] guard already installed in {target}")
    raise SystemExit(0)

required = ("class Config:", "def set(", "def load(", "def load_dict(")
missing = [item for item in required if item not in source]
if missing:
    print(
        f"[heroku-policy] ERROR: unsupported Config module {target}; missing "
        f"{', '.join(missing)}. Refusing to start.",
        file=sys.stderr,
    )
    raise SystemExit(78)

guard = r'''

# BEGIN TELLY_HEROKU_POLICY_GUARD (managed by sdk-deploye)
# This is intentionally visible in the runtime source and re-applied after
# config.py, environment variables, database settings, and bot-setting writes.
def _telly_heroku_policy_enforce(cls):
    import os as _telly_os
    mode = _telly_os.environ.get("HEROKU_POLICY_MODE", "").strip().lower()
    if not _telly_os.environ.get("DYNO") and mode not in ("1", "true", "yes", "on"):
        return

    enforced = {
        "DISABLE_TORRENTS": True,
        "DISABLE_LEECH": True,
        "DISABLE_SEED": True,
        "DISABLE_BULK": True,
        "DISABLE_MULTI": True,
        "AUTO_LEECH": False,
        "AUTO_MIRROR": False,
        "AUTO_YT_LEECH": False,
        "AUTO_YTDL": False,
        "AUTO_QBLEECH": False,
        "AUTO_QBMIRROR": False,
        "AUTO_JDLEECH": False,
        "AUTO_JDMIRROR": False,
        "AUTO_GDL_LEECH": False,
        "AUTO_GDL_MIRROR": False,
        "SEARCH_PLUGINS": [],
        "SEARCH_API_LINK": "",
        "SEARCH_LIMIT": 0,
        "RSS_CHAT": "",
        "RCLONE_SERVE_URL": "",
        "RESOLVER_ENABLED": False,
        "RESOLVER_UI": False,
        "AUTHORIZED_CHATS": "",
        "SUDO_USERS": "",
        "BOT_MAX_TASKS": 1,
        "USER_MAX_TASKS": 1,
        "QUEUE_ALL": 2,
        "QUEUE_DOWNLOAD": 1,
        "QUEUE_UPLOAD": 1,
        "HYPER_THREADS": 1,
    }
    changed = []
    for key, value in enforced.items():
        if hasattr(cls, key):
            old_value = getattr(cls, key)
            if old_value != value:
                setattr(cls, key, value.copy() if isinstance(value, (list, dict)) else value)
                changed.append(key)
    if changed:
        try:
            from logging import getLogger
            getLogger(__name__).warning(
                "Heroku policy safety mode enforced; disabled/restricted: %s",
                ", ".join(changed),
            )
        except Exception:
            pass


_telly_original_config_set = Config.set.__func__
def _telly_policy_config_set(cls, key, value):
    _telly_original_config_set(cls, key, value)
    _telly_heroku_policy_enforce(cls)
Config.set = classmethod(_telly_policy_config_set)

_telly_original_config_load = Config.load.__func__
def _telly_policy_config_load(cls):
    _telly_original_config_load(cls)
    _telly_heroku_policy_enforce(cls)
Config.load = classmethod(_telly_policy_config_load)

_telly_original_config_load_dict = Config.load_dict.__func__
def _telly_policy_config_load_dict(cls, config_dict):
    _telly_original_config_load_dict(cls, config_dict)
    _telly_heroku_policy_enforce(cls)
Config.load_dict = classmethod(_telly_policy_config_load_dict)

_telly_heroku_policy_enforce(Config)
# END TELLY_HEROKU_POLICY_GUARD
'''
target.write_text(source.rstrip() + "\n" + guard.lstrip("\n") + "\n", encoding="utf-8")
print(f"[heroku-policy] applied fail-closed guard to {target}")
