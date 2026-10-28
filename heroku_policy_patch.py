#!/usr/bin/env python3
"""Apply a transparent, fail-closed Heroku policy guard to fetched bot source.

The deployment wrapper fetches the selected upstream bot at startup. This
patcher runs after that fetch and before the bot starts, so persisted settings
cannot silently re-enable high-risk features or public command authorization.
"""

from os import environ
from pathlib import Path
import sys

MODE_VALUES = {"1", "true", "yes", "on"}
mode = environ.get("HEROKU_POLICY_MODE", "").strip().lower()
if not environ.get("DYNO") and mode not in MODE_VALUES:
    raise SystemExit(0)

LAYOUTS = (
    (Path("bot/core/config_manager.py"), Path("bot/helper/telegram_helper/filters.py")),
    (Path("app/core/config_loader.py"), Path("app/telegram/filters.py")),
)
layout = next(((config, filters) for config, filters in LAYOUTS if config.is_file()), None)
if layout is None:
    print(
        "[heroku-policy] ERROR: no supported Config module found; refusing to "
        "start without the safety guard.",
        file=sys.stderr,
    )
    raise SystemExit(78)

config_path, filters_path = layout
if not filters_path.is_file():
    print(
        f"[heroku-policy] ERROR: expected authorization filter {filters_path} "
        "is missing; refusing to start without owner-only authorization.",
        file=sys.stderr,
    )
    raise SystemExit(78)

config_source = config_path.read_text(encoding="utf-8")
config_marker = "# BEGIN TELLY_HEROKU_POLICY_GUARD (managed by sdk-deploye)"
required = ("class Config:", "def set(", "def load(", "def load_dict(")
missing = [item for item in required if item not in config_source]
if missing:
    print(
        f"[heroku-policy] ERROR: unsupported Config module {config_path}; missing "
        f"{', '.join(missing)}. Refusing to start.",
        file=sys.stderr,
    )
    raise SystemExit(78)

config_guard = r'''

# BEGIN TELLY_HEROKU_POLICY_GUARD (managed by sdk-deploye)
# Re-applied after config.py, environment variables, database settings, and
# bot-setting writes. This is a risk-reduction mode, not policy approval.
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
if config_marker not in config_source:
    config_source = config_source.rstrip() + "\n" + config_guard.lstrip("\n") + "\n"

filter_source = filters_path.read_text(encoding="utf-8")
if not all(
    f"async def {method}(self, _, update):" in filter_source
    for method in ("authorized_user", "sudo_user")
):
    print(
        f"[heroku-policy] ERROR: unsupported authorization filter {filters_path}; "
        "owner-only guard could not be applied. Refusing to start.",
        file=sys.stderr,
    )
    raise SystemExit(78)

def add_owner_only_guard(source, method):
    marker = f"# BEGIN TELLY_HEROKU_OWNER_ONLY_{method.upper()}"
    if marker in source:
        return source
    signature = f"    async def {method}(self, _, update):\n"
    addition = (
        signature
        + f"        {marker}\n"
        + "        import os as _telly_auth_os\n"
        + "        _telly_auth_mode = _telly_auth_os.environ.get(\"HEROKU_POLICY_MODE\", \"\").strip().lower()\n"
        + "        if _telly_auth_os.environ.get(\"DYNO\") or _telly_auth_mode in (\"1\", \"true\", \"yes\", \"on\"):\n"
        + "            _telly_auth_user = update.from_user or update.sender_chat\n"
        + "            return bool(_telly_auth_user and _telly_auth_user.id == Config.OWNER_ID)\n"
        + f"        # END TELLY_HEROKU_OWNER_ONLY_{method.upper()}\n"
    )
    if signature not in source:
        raise ValueError(f"method signature missing: {method}")
    return source.replace(signature, addition, 1)

try:
    filter_source = add_owner_only_guard(filter_source, "authorized_user")
    filter_source = add_owner_only_guard(filter_source, "sudo_user")
except ValueError as exc:
    print(f"[heroku-policy] ERROR: {exc}; refusing to start.", file=sys.stderr)
    raise SystemExit(78)

# qBittorrent is launched during package import in some legacy bot layouts,
# before Config has loaded. Do not start the torrent daemon at all in Heroku
# policy mode; the guard must work even before Config exists.
bot_init_path = Path("bot/__init__.py")
bot_init_source = None
qbit_start = 'srun([BinConfig.QBIT_NAME, "-d", f"--profile={getcwd()}"], check=False)'
if bot_init_path.is_file():
    bot_init_source = bot_init_path.read_text(encoding="utf-8")
    qbit_marker = "# BEGIN TELLY_HEROKU_SKIP_QBIT (managed by sdk-deploye)"
    if qbit_marker not in bot_init_source and qbit_start in bot_init_source:
        qbit_replacement = '''# BEGIN TELLY_HEROKU_SKIP_QBIT (managed by sdk-deploye)
import os as _telly_qbit_os
_telly_qbit_mode = _telly_qbit_os.environ.get("HEROKU_POLICY_MODE", "").strip().lower()
if not _telly_qbit_os.environ.get("DYNO") and _telly_qbit_mode not in ("1", "true", "yes", "on"):
    srun([BinConfig.QBIT_NAME, "-d", f"--profile={getcwd()}"], check=False)
else:
    LOGGER.warning("Heroku safety mode: qBittorrent daemon startup skipped.")
# END TELLY_HEROKU_SKIP_QBIT'''
        bot_init_source = bot_init_source.replace(qbit_start, qbit_replacement, 1)

# Validate all modified files before writing any of them.
try:
    compile(config_source, str(config_path), "exec")
    compile(filter_source, str(filters_path), "exec")
    if bot_init_source is not None:
        compile(bot_init_source, str(bot_init_path), "exec")
except SyntaxError as exc:
    print(f"[heroku-policy] ERROR: generated guard has invalid syntax: {exc}", file=sys.stderr)
    raise SystemExit(78)

config_path.write_text(config_source, encoding="utf-8")
filters_path.write_text(filter_source, encoding="utf-8")
if bot_init_source is not None:
    bot_init_path.write_text(bot_init_source, encoding="utf-8")
print(
    f"[heroku-policy] applied guarded settings to {config_path}, owner-only "
    f"authorization to {filters_path}, and torrent-start guard where supported"
)
