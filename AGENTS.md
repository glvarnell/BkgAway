# AGENTS.md — guidance for AI coding agents

This repository is **rm_bkg**: a **PySide6** desktop app that removes image backgrounds using
[`transparent-background`](https://github.com/plemeri/transparent-background) (InSPyReNet), matching the
ComfyUI **Inspyrenet Rembg** node (`Remover()`, `process(..., type="rgba")`).

## Layout

| Path | Role |
|------|------|
| `rm_bkg/__init__.py` | `__version__`, `CHANGELOG` (About tab) |
| `rm_bkg/__main__.py` | Entry: `python -m rm_bkg` |
| `rm_bkg/main_window.py` | Main window, tabs, toolbar, threading hooks |
| `THIRD_PARTY_NOTICES.md` | Dependency attribution (bundled in PyInstaller builds) |
| `rm_bkg/remover_worker.py` | `QThread` + `Remover` + batch I/O |
| `rm_bkg/preview_widgets.py` | Zoom / pan / double-click-fit previews (`QGraphicsView`) |
| `rm_bkg/drop_widgets.py` | File/folder drop helpers + `ImageDropLabel` (input summary only) |
| `rm_bkg/images.py` | PIL ↔ Qt, checkerboard compositing |
| `requirements-*.txt` | CUDA / CPU / common / ROCm (torch install split) |
| `packaging/` | PyInstaller specs, `entrypoint_gui.sh`, build scripts |

## Run (development)

From repo root (parent of package `rm_bkg/`). Prefer **Python 3.13** (see `.tool-versions`);
do not create venvs with system 3.14+.

```bash
asdf install   # if using asdf and 3.13.0 is missing
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-cuda.txt   # or requirements-cpu.txt
python -m rm_bkg
```

Needs a display (Qt GUI). First inference may download weights into the app data cache
(see `rm_bkg/paths.py` / About → model cache path).

## Frozen builds (PyInstaller)

- **CUDA:** → `./packaging/build_nvidia.sh` → `dist/rm-bkg-cuda/rm-bkg-cuda`
- **CPU:** → `./packaging/build_cpu.sh` → `dist/rm-bkg-cpu/rm-bkg-cpu`
- Specs: `packaging/rm_bkg_cuda.spec`, `packaging/rm_bkg_cpu.spec`

Always use the **PyInstaller from the same venv as the torch build** you intend to ship.

If you add imports that PyInstaller misses, extend **`hiddenimports`** (and if needed the `packages` `collect_all` loop) in **both** `packaging/rm_bkg_cuda.spec` and `packaging/rm_bkg_cpu.spec`.

## Conventions when editing

1. **Keep inference off the GUI thread** — all `Remover` / file work stays in `RemoveBackgroundThread` (`remover_worker.py`). Downscale + checkerboard previews in the worker; UI updates via Qt signals only. Reuse `get_cached_remover()` across Runs; call `clear_cached_remover()` when clearing weights.
2. **Match existing style** — minimal diffs; no unrelated refactors or new docs unless asked.
3. **Dependencies** — any new third-party import must be reflected in `requirements-common.txt` or the appropriate torch file; bump README if user-facing behavior changes.
4. **Outputs** — PNG naming is `{stem}_nobg.png`; optional mask `{stem}_nobg_mask.png` (see `remover_worker.py`).
5. **Qt previews** — zoom/pan/double-click live in `ZoomPreviewView`; drag-drop on the **original** preview is optional (`accept_file_drops`); input summary strip still uses `ImageDropLabel`.
6. **Do not** assume ComfyUI is present; the app is standalone.

## Testing

There is no automated test suite yet. After changes, at minimum:

```bash
python -m compileall -q rm_bkg
python -c "from rm_bkg.main_window import MainWindow"
```

Manually smoke-test: open image, run, batch folder, drag-drop, zoom/pan/reset, frozen binary if packaging changed.

## README

User-facing setup and packaging details live in [`README.md`](README.md). Prefer updating README for install/build instructions unless the user asks for a different doc.
