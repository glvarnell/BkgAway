#!/usr/bin/env bash
# Build a standalone onedir bundle for Linux with CUDA PyTorch in the *current* venv.
#
#   python3 -m venv .venv-cuda
#   source .venv-cuda/bin/activate
#   pip install -U pip
#   pip install -r requirements-cuda.txt pyinstaller
#   ./packaging/build_nvidia.sh
#
# Output: dist/rm-bkg-cuda/  (run dist/rm-bkg-cuda/rm-bkg-cuda)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec pyinstaller --noconfirm --clean "${ROOT}/packaging/rm_bkg_cuda.spec"
