from sys import exit
from importlib import import_module
from logging import (
    FileHandler,
    StreamHandler,
    INFO,
    basicConfig,
    error as log_error,
    info as log_info,
    getLogger,
    ERROR,
)
from os import path, remove, environ, name as osname
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from subprocess import run as srun, call as scall

getLogger("pymongo").setLevel(ERROR)

var_list = [
    "BOT_TOKEN",
    "TELEGRAM_API",
    "TELEGRAM_HASH",
    "OWNER_ID",
    "DATABASE_URL",
    "BASE_URL",
    "UPSTREAM_REPO",
    "UPSTREAM_BRANCH",
    "UPDATE_PKGS",
]

if path.exists("log.txt"):
    with open("log.txt", "r+") as f:
        f.truncate(0)

if path.exists("rlog.txt"):
    remove("rlog.txt")

basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)
try:
    settings = import_module("config")
    config_file = {
        key: value.strip() if isinstance(value, str) else value
        for key, value in vars(settings).items()
        if not key.startswith("__")
    }
except ModuleNotFoundError:
    log_info("Config.py file is not Added! Checking ENVs..")
    config_file = {}

env_updates = {
    key: value.strip() if isinstance(value, str) else value
    for key, value in environ.items()
    if key in var_list
}
if env_updates:
    log_info("Config data is updated with ENVs!")
    config_file.update(env_updates)

BOT_TOKEN = config_file.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

BOT_ID = BOT_TOKEN.split(":", 1)[0]

if DATABASE_URL := config_file.get("DATABASE_URL", "").strip():
    try:
        conn = MongoClient(DATABASE_URL, server_api=ServerApi("1"))
        db = conn[config_file.get("DATABASE_NAME", "tellycloud")]
        old_config = db.settings.deployConfig.find_one({"_id": BOT_ID}, {"_id": 0})
        config_dict = db.settings.config.find_one({"_id": BOT_ID})
        if (
            old_config is not None and old_config == config_file or old_config is None
        ) and config_dict is not None:
            config_file["UPSTREAM_REPO"] = config_dict["UPSTREAM_REPO"]
            config_file["UPSTREAM_BRANCH"] = config_dict.get("UPSTREAM_BRANCH", "wzv3")
            config_file["UPDATE_PKGS"] = config_dict.get("UPDATE_PKGS", "True")
        conn.close()
    except Exception as e:
        log_error(f"Database ERROR: {e}")

UPSTREAM_REPO = config_file.get("UPSTREAM_REPO", "").strip()
UPSTREAM_BRANCH = config_file.get("UPSTREAM_BRANCH", "").strip() or "master"

if UPSTREAM_REPO:
    if path.exists(".git"):
        if osname == "nt":
            srun(["rmdir", "/s", "/q", ".git"], shell=True)
        else:
            srun(["rm", "-rf", ".git"])

    # Set non-interactive git environment
    update_env = environ.copy()
    update_env["GIT_TERMINAL_PROMPT"] = "0"

    try:
        srun(["git", "init", "-q"], check=True)
        srun(
            ["git", "config", "--global", "user.email", "bot@tellyhouse.com"],
            check=True,
        )
        srun(["git", "config", "--global", "user.name", "TellYBot"], check=True)
        srun(["git", "remote", "add", "origin", UPSTREAM_REPO], check=True)

        # Fetch attempt
        fetch_res = srun(["git", "fetch", "origin", "-q"], env=update_env)

        if fetch_res.returncode == 0:
            srun(
                ["git", "reset", "--hard", f"origin/{UPSTREAM_BRANCH}", "-q"],
                check=True,
            )
            log_info("Successfully updated with latest code!")
        else:
            log_error(
                "Failed to fetch from Upstream. Incorrect token, branch, or repo URL?"
            )
            log_info("Continuing with existing code...")
    except Exception as e:
        log_error(f"Update process failed: {e}")
        log_info("Skipping update and trying to start...")

    # Log sanitized URL
    repo_parts = UPSTREAM_REPO.split("/")
    if len(repo_parts) >= 2:
        sanitized_repo = f"https://github.com/{repo_parts[-2]}/{repo_parts[-1]}"
    else:
        sanitized_repo = UPSTREAM_REPO
    log_info(f"UPSTREAM_REPO: {sanitized_repo} | UPSTREAM_BRANCH: {UPSTREAM_BRANCH}")


UPDATE_PKGS = config_file.get("UPDATE_PKGS", "True")
if (isinstance(UPDATE_PKGS, str) and UPDATE_PKGS.lower() == "true") or UPDATE_PKGS:
    scall("uv pip install -U -r requirements.txt", shell=True)
    log_info("Successfully Updated all the Packages !")
