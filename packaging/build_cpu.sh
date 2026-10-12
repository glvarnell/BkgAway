#!/usr/bin/env bash
# Build a standalone onedir bundle for CPU-only PyTorch in the *current* venv.
#
#   python3 -m venv .venv-cpu
#   source .venv-cpu/bin/activate
#   pip install -U pip
#   pip install -r requirements-cpu.txt
#   pip install -r packaging/requirements-build-cpu.txt
#   ./packaging/build_cpu.sh
#
# Same without activating (forces this venv’s PyInstaller):
#   PYINSTALLER=.venv-cpu-build/bin/pyinstaller ./packaging/build_cpu.sh
#   # or:
#   .venv-cpu-build/bin/pyinstaller --noconfirm --clean packaging/rm_bkg_cpu.spec
#
# Output: dist/rm-bkg-cpu/  (run dist/rm-bkg-cpu/rm-bkg-cpu)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYI="${PYINSTALLER:-pyinstaller}"
exec "$PYI" --noconfirm --clean "${ROOT}/packaging/rm_bkg_cpu.spec"
