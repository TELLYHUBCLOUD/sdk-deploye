
#!/usr/bin/env bash
set -Eeuo pipefail

source .venv/bin/activate && python3 update.py && python3 -m bot
