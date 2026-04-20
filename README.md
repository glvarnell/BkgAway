# Remove background (Qt)

Small desktop app that mirrors the ComfyUI **Inspyrenet Rembg** path: it uses
[`transparent-background`](https://github.com/plemeri/transparent-background)
(InSPyReNet) with `Remover()` and writes PNGs with an alpha channel.

## Setup

Create a virtual environment, then install **one** of the GPU/CPU requirement files.

```bash
cd /path/to/rm_bkg
python3 -m venv .venv
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

On first run, `transparent-background` may download model weights into
`~/.transparent-background/`.

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

## Packaging

Later you can freeze separate **CUDA** and **ROCm** (and optional **CPU**) bundles
with PyInstaller or Nuitka; each bundle must ship the matching PyTorch wheel.
See [`packaging/pyinstaller_example.sh`](packaging/pyinstaller_example.sh) for a
minimal starting command (expect to add `--collect-all` / `--hidden-import` for
your torch stack).
