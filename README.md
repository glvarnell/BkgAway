# rm_bkg

Desktop app that removes image backgrounds. It mirrors the ComfyUI **Inspyrenet
Rembg** path using
[`transparent-background`](https://github.com/plemeri/transparent-background)
(InSPyReNet) with `Remover()` and writes PNGs with an alpha channel.

Run with `python -m rm_bkg`.

## Acknowledgments

Built on open-source components including **transparent-background**,
**InSPyReNet**, **PySide6/Qt**, **PyTorch**, **Pillow**, and **NumPy**. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for attribution and license
pointers (also shown under **About → Third-party notices** in the app). Include
that file when redistributing frozen builds.

## Setup

Use **Python 3.13** (pinned in [`.tool-versions`](.tool-versions) for [asdf](https://asdf-vm.com/)).
Avoid 3.14+ for this stack; create venvs with the pinned interpreter, not system Python.

```bash
cd /path/to/rm_bkg
asdf install          # if needed: installs python 3.13.0 from .tool-versions
python -V             # expect 3.13.0
python -m venv .venv
source .venv/bin/activate
```

**NVIDIA (CUDA)** — edit `cu124` in `requirements-cuda.txt` if needed to match [PyTorch](https://pytorch.org/get-started/locally/).

```bash
pip install -U pip
pip install -r requirements-cuda.txt
```

**CPU only** (simpler, slower):

```bash
pip install -U pip
pip install -r requirements-cpu.txt
```

**AMD (Linux, ROCm)** — install ROCm PyTorch **first** (example; pick the index
URL that matches your stack):

```bash
pip install -U pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.2
pip install -r requirements-rocm.txt
```

`requirements-rocm.txt` only pulls the UI + `transparent-background` stack so
you do not accidentally overwrite ROCm torch with a CUDA wheel from PyPI.

On first run, `transparent-background` downloads model weights once into a
stable cache directory (see below). The app shows **Model cache:** in Options;
use **Re-download weights…** to clear that cache and fetch again on the next Run.

**Cache location:** before Run, the app sets `TRANSPARENT_BACKGROUND_FILE_PATH`
when it is unset so checkpoints live under the Qt **application data** directory
for this app (not necessarily `$HOME`). Override the parent directory with
`RM_BKG_WEIGHTS_ROOT` (the `.transparent-background` folder is created inside
it). If you already have weights under `~/.transparent-background/`, either
set `RM_BKG_WEIGHTS_ROOT` to your home directory or copy that folder into the
path shown in the UI.

## Run

From this directory (so the `rm_bkg` package resolves):

```bash
python -m rm_bkg
```

## Usage

1. **Open…** or **Open folder…** for batch processing.  
2. Choose an **output folder** (defaults to the folder when you used “Open folder…”).  
3. **Run** — progress and logs update in the window; previews show original vs result
   (checkerboard indicates transparency). **Stop** finishes after the current file
   (safe interruption between images).

Outputs are `{original_stem}_nobg.png` in the output folder. Optional **Save mask PNG**
writes `{stem}_nobg_mask.png` from the alpha channel.

## Standalone NVIDIA build (Linux, PyInstaller)

The CUDA bundle is a **onedir** tree (not a single file): easier for PyTorch and
Qt. Build on **Linux x86_64** in a venv that already has **CUDA PyTorch** from
`requirements-cuda.txt` (the wheel you install here is what gets frozen).

```bash
cd /path/to/rm_bkg
python3 -m venv .venv-cuda
source .venv-cuda/bin/activate
pip install -U pip
pip install -r requirements-cuda.txt
pip install -r packaging/requirements-build-cuda.txt
./packaging/build_nvidia.sh
```
to re-build
```bash
source .venv-cuda/bin/activate
./packaging/build_nvidia.sh
```
or
```bash
PYINSTALLER=.venv/bin/pyinstaller ./packaging/build_nvidia.sh
```

**Run the app:** `./dist/rm-bkg-cuda/rm-bkg-cuda`

**Ship:** zip or tarball the whole `dist/rm-bkg-cuda/` directory.

**Target machine:** needs a **compatible NVIDIA driver** for the CUDA version
bundled with your PyTorch wheel, and roughly compatible **glibc** (build on an
older distro if you need broader compatibility). First run still downloads
model weights into the app’s cache directory unless you ship that cache (or set
`RM_BKG_WEIGHTS_ROOT` / `TRANSPARENT_BACKGROUND_FILE_PATH` to a pre-populated tree).

Spec file: [`packaging/rm_bkg_cuda.spec`](packaging/rm_bkg_cuda.spec). If the
frozen app fails with a missing module, add it to `hiddenimports` or extend
`packages` in the spec and rebuild.

## Standalone CPU build (Linux, PyInstaller)

Same **onedir** layout as the CUDA build, but use **CPU PyTorch** from
`requirements-cpu.txt` so the bundle does **not** ship the NVIDIA CUDA stack
(smaller than `rm-bkg-cuda`, still large because of Qt + torch CPU + vision deps).

```bash
cd /path/to/rm_bkg
python3 -m venv .venv-cpu
source .venv-cpu/bin/activate
pip install -U pip
pip install -r requirements-cpu.txt
pip install -r packaging/requirements-build-cpu.txt
./packaging/build_cpu.sh
```

**Run the app:** `./dist/rm-bkg-cpu/rm-bkg-cpu`

**Ship:** the whole `dist/rm-bkg-cpu/` directory (including `_internal/`).

Spec: [`packaging/rm_bkg_cpu.spec`](packaging/rm_bkg_cpu.spec).

**Smaller bundles (already in the specs):** PySide6 is **not** `collect_all`’d
(use the default hook instead), **CPU** builds omit **Triton** native libs, both
specs **strip** ELF binaries where possible, and a few **dev-only** top-level
packages are listed under `excludes`. Further shrinking means dropping
`collect_all` targets and fixing missing-module errors as they appear, or
shipping a venv instead of PyInstaller.

**ROCm** frozen build is not scripted here; copy the CPU or CUDA spec and adjust
the venv (ROCm `torch` wheel) if you need it.
