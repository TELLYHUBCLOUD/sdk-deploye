"""Offline regression tests for the deployment-time Heroku policy patcher."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PATCHER = Path(__file__).resolve().parents[1] / "heroku_policy_patch.py"

FIXTURE_CONFIG = '''class Config:
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
    SUDO_USERS = "123456"
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


class HerokuPolicyPatchTests(unittest.TestCase):
    def _fixture(self, root):
        config_path = root / "bot" / "core" / "config_manager.py"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(FIXTURE_CONFIG, encoding="utf-8")
        (config_path.parent.parent / "__init__.py").write_text("", encoding="utf-8")
        (config_path.parent / "__init__.py").write_text("", encoding="utf-8")
        (config_path.parent.parent.parent / "__init__.py").write_text("", encoding="utf-8")
        return config_path

    def test_no_patch_outside_heroku_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = self._fixture(root)
            before = config_path.read_text(encoding="utf-8")
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
            self.assertEqual(config_path.read_text(encoding="utf-8"), before)

    def test_heroku_mode_patches_and_reapplies_guard_after_config_updates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = self._fixture(root)
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
            self.assertEqual(result.returncode, 0, result.stderr)
            patched_source = config_path.read_text(encoding="utf-8")
            self.assertIn("BEGIN TELLY_HEROKU_POLICY_GUARD", patched_source)
            compile(patched_source, str(config_path), "exec")

            check_code = r'''
from bot.core.config_manager import Config
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
