#!/usr/bin/env bash
# Example freeze (run from repo root in a venv that already has torch + deps + pyinstaller).
# Expect to tune --hidden-import / --collect-all for your torch build.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec pyinstaller --noconfirm --onedir --name rm-bkg-cuda \
  --paths "$ROOT" \
  --collect-all PySide6 \
  "$ROOT/rm_bkg/__main__.py"
