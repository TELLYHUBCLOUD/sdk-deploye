"""Offline regression tests for the deployment-time Heroku policy patcher."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PATCHER = Path(__file__).resolve().parents[1] / "heroku_policy_patch.py"

FIXTURE_CONFIG = '''class Config:
    OWNER_ID = 123456
    DISABLE_TORRENTS = False
    DISABLE_LEECH = False
    DISABLE_SEED = False
    DISABLE_BULK = False
    DISABLE_MULTI = False
    AUTO_LEECH = True
    AUTO_MIRROR = True
    AUTO_YT_LEECH = True
    AUTO_YTDL = True
    AUTO_QBLEECH = True
    AUTO_QBMIRROR = True
    AUTO_JDLEECH = True
    AUTO_JDMIRROR = True
    AUTO_GDL_LEECH = True
    AUTO_GDL_MIRROR = True
    SEARCH_PLUGINS = ["https://indexer.example/plugin.py"]
    SEARCH_API_LINK = "https://search.example"
    SEARCH_LIMIT = 50
    RSS_CHAT = "-1001234567"
    RCLONE_SERVE_URL = "https://files.example"
    RESOLVER_ENABLED = True
    RESOLVER_UI = True
    AUTHORIZED_CHATS = "-1001234567"
    SUDO_USERS = "987654"
    BOT_MAX_TASKS = 0
    USER_MAX_TASKS = 0
    QUEUE_ALL = 0
    QUEUE_DOWNLOAD = 0
    QUEUE_UPLOAD = 0
    HYPER_THREADS = 4

    @classmethod
    def set(cls, key, value):
        setattr(cls, key, value)

    @classmethod
    def load(cls):
        return None

    @classmethod
    def load_dict(cls, values):
        for key, value in values.items():
            setattr(cls, key, value)
'''

FIXTURE_FILTERS = '''from pyrogram.filters import create
from bot.core.config_manager import Config

class CustomFilters:
    async def authorized_user(self, _, update):
        user = update.from_user or update.sender_chat
        return bool(user and user.id == Config.OWNER_ID)

    authorized = create(authorized_user)

    async def sudo_user(self, _, update):
        user = update.from_user or update.sender_chat
        return bool(user and user.id == Config.OWNER_ID)

    sudo = create(sudo_user)
'''


class HerokuPolicyPatchTests(unittest.TestCase):
    def _fixture(self, root, layout="bot"):
        if layout == "bot":
            config_path = root / "bot" / "core" / "config_manager.py"
            filters_path = root / "bot" / "helper" / "telegram_helper" / "filters.py"
            config_import = "from bot.core.config_manager import Config"
            package_dirs = (
                root / "bot",
                root / "bot" / "core",
                root / "bot" / "helper",
                root / "bot" / "helper" / "telegram_helper",
            )
        else:
            config_path = root / "app" / "core" / "config_loader.py"
            filters_path = root / "app" / "telegram" / "filters.py"
            config_import = "from app.core.config_loader import Config"
            package_dirs = (
                root / "app",
                root / "app" / "core",
                root / "app" / "telegram",
            )
        config_path.parent.mkdir(parents=True)
        config_path.write_text(FIXTURE_CONFIG, encoding="utf-8")
        filters_path.parent.mkdir(parents=True)
        filters_path.write_text(
            FIXTURE_FILTERS.replace("from bot.core.config_manager import Config", config_import),
            encoding="utf-8",
        )
        for package_dir in package_dirs:
            (package_dir / "__init__.py").write_text("", encoding="utf-8")
        if layout == "bot":
            (root / "bot" / "__init__.py").write_text(
                "\n".join(
                    (
                        "from os import getcwd",
                        "import logging",
                        'class BinConfig: QBIT_NAME = "tellybit"',
                        "LOGGER = logging.getLogger(__name__)",
                        'def srun(*args, **kwargs): raise AssertionError("qBittorrent must not start in Heroku mode")',
                        'srun([BinConfig.QBIT_NAME, "-d", f"--profile={getcwd()}"], check=False)',
                        "",
                    )
                ),
                encoding="utf-8",
            )
        return config_path, filters_path

    def test_no_patch_outside_heroku_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path, filters_path = self._fixture(root)
            before_config = config_path.read_text(encoding="utf-8")
            before_filters = filters_path.read_text(encoding="utf-8")
            env = os.environ.copy()
            env.pop("DYNO", None)
            env["HEROKU_POLICY_MODE"] = "0"
            result = subprocess.run(
                [sys.executable, str(PATCHER)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(config_path.read_text(encoding="utf-8"), before_config)
            self.assertEqual(filters_path.read_text(encoding="utf-8"), before_filters)

    def test_app_layout_is_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path, filters_path = self._fixture(root, layout="app")
            env = os.environ.copy()
            env["HEROKU_POLICY_MODE"] = "1"
            env.pop("DYNO", None)
            result = subprocess.run(
                [sys.executable, str(PATCHER)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            config_source = config_path.read_text(encoding="utf-8")
            filter_source = filters_path.read_text(encoding="utf-8")
            self.assertIn("BEGIN TELLY_HEROKU_POLICY_GUARD", config_source)
            self.assertIn("BEGIN TELLY_HEROKU_OWNER_ONLY_AUTHORIZED_USER", filter_source)
            self.assertIn("BEGIN TELLY_HEROKU_OWNER_ONLY_SUDO_USER", filter_source)
            compile(config_source, str(config_path), "exec")
            compile(filter_source, str(filters_path), "exec")

    def test_heroku_mode_blocks_config_overrides_and_non_owner_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path, filters_path = self._fixture(root)
            env = os.environ.copy()
            env["DYNO"] = "web.1"
            env.pop("HEROKU_POLICY_MODE", None)
            result = subprocess.run(
                [sys.executable, str(PATCHER)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            patched_config = config_path.read_text(encoding="utf-8")
            patched_filters = filters_path.read_text(encoding="utf-8")
            self.assertIn("BEGIN TELLY_HEROKU_POLICY_GUARD", patched_config)
            self.assertIn("BEGIN TELLY_HEROKU_OWNER_ONLY_AUTHORIZED_USER", patched_filters)
            bot_init_path = root / "bot" / "__init__.py"
            patched_bot_init = bot_init_path.read_text(encoding="utf-8")
            self.assertIn("BEGIN TELLY_HEROKU_SKIP_QBIT", patched_bot_init)
            compile(patched_bot_init, str(bot_init_path), "exec")
            self.assertIn("BEGIN TELLY_HEROKU_OWNER_ONLY_SUDO_USER", patched_filters)
            compile(patched_config, str(config_path), "exec")
            compile(patched_filters, str(filters_path), "exec")

            check_code = r'''
import asyncio
import sys
import types

pyrogram = types.ModuleType("pyrogram")
filters = types.ModuleType("pyrogram.filters")
filters.create = lambda function: function
pyrogram.filters = filters
sys.modules["pyrogram"] = pyrogram
sys.modules["pyrogram.filters"] = filters

from bot.core.config_manager import Config
from bot.helper.telegram_helper.filters import CustomFilters

assert Config.DISABLE_TORRENTS is True
assert Config.DISABLE_LEECH is True
assert Config.DISABLE_SEED is True
assert Config.AUTO_LEECH is False
assert Config.SEARCH_PLUGINS == []
assert Config.RCLONE_SERVE_URL == ""
assert Config.AUTHORIZED_CHATS == ""
assert Config.BOT_MAX_TASKS == 1

Config.load_dict({
    "DISABLE_TORRENTS": False,
    "DISABLE_LEECH": False,
    "AUTO_LEECH": True,
    "SEARCH_PLUGINS": ["https://indexer.example/plugin.py"],
    "RCLONE_SERVE_URL": "https://files.example",
    "AUTHORIZED_CHATS": "-1001234567",
    "BOT_MAX_TASKS": 0,
})
assert Config.DISABLE_TORRENTS is True
assert Config.DISABLE_LEECH is True
assert Config.AUTO_LEECH is False
assert Config.SEARCH_PLUGINS == []
assert Config.RCLONE_SERVE_URL == ""
assert Config.AUTHORIZED_CHATS == ""
assert Config.BOT_MAX_TASKS == 1

Config.set("DISABLE_TORRENTS", False)
Config.set("AUTO_LEECH", True)
assert Config.DISABLE_TORRENTS is True
assert Config.AUTO_LEECH is False

class Update:
    def __init__(self, uid):
        self.from_user = types.SimpleNamespace(id=uid)
        self.sender_chat = None

async def verify_owner_only():
    instance = CustomFilters()
    owner = Config.OWNER_ID
    stranger = owner + 1
    assert await instance.authorized_user(None, Update(owner))
    assert not await instance.authorized_user(None, Update(stranger))
    assert await instance.sudo_user(None, Update(owner))
    assert not await instance.sudo_user(None, Update(stranger))

asyncio.run(verify_owner_only())
'''
            verify = subprocess.run(
                [sys.executable, "-c", check_code],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)


if __name__ == "__main__":
    unittest.main()
