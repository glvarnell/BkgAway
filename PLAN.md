# PLAN.md — technical plan and roadmap

## Product goal

Deliver a **small, standalone** desktop tool (no ComfyUI) that reproduces the user’s **Remove Background** workflow based on **Inspyrenet Rembg**, using the same underlying stack: **`transparent_background.Remover()`** and **`process(..., type="rgba")`**, with **PySide6** UI and optional **PyInstaller** bundles for **NVIDIA (CUDA)** and **CPU**.

## Current architecture

```text
┌─────────────────────────────────────────────────────────┐
│  MainWindow (PySide6)                                    │
│  toolbar · I/O · options · previews · progress · log     │
└───────────────┬─────────────────────────────────────────┘
                │ signals/slots
                ▼
┌─────────────────────────────────────────────────────────┐
│  RemoveBackgroundThread (QThread)                        │
│  Remover() once per run · process RGB → RGBA PNG         │
│  optional _nobg_mask.png · emits previews + log lines    │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
         transparent_background / torch / PIL
```

- **Input:** file dialog, folder scan (`remover_worker.list_images_in_dir`), drag-drop on input label + original preview.
- **Output:** `{stem}_nobg.png` in chosen directory; optional alpha mask file.
- **Previews:** `ZoomPreviewView` — wheel zoom, pan after zoom (`ScrollHandDrag`), double-click refit, checkerboard for transparency on the result side.

## Completed (baseline)

- [x] Core removal pipeline aligned with Inspyrenet Rembg (`Remover()`, no TorchScript JIT option).
- [x] Batch processing, stop between files, status (file + elapsed + device string).
- [x] Drag-and-drop; live original preview on selection; `_nobg` filename suffix.
- [x] Separate **requirements** lines: CUDA / CPU / ROCm (`requirements-rocm.txt` pulls common after manual ROCm torch).
- [x] **PyInstaller** onedir specs + scripts for **CUDA** and **CPU**; `strip`, reduced PySide6 `collect_all`, CPU omits Triton native libs.
- [x] README: install, run, frozen build, `_internal/` note for distributors.

## Near-term options (not committed)

- **ROCm frozen build** — mirror `rm_bkg_cpu.spec` with a ROCm venv; document index URL pinning.
- **Smaller bundles** — tighter `collect_all` / excludes; optional Qt plugin stripping; trade risk vs size.
- **Windows / macOS** — not primary; would need platform-specific PyInstaller notes and torch wheels.
- **Tests** — small pytest for `paths_from_drop_mime`, naming rules, optional headless worker smoke (heavy deps).
- **CI** — lint + `compileall` + optional CPU-only wheel build on Linux runners (no GPU).

## Non-goals (unless requirements change)

- Re-implementing Comfy graph execution or custom Comfy nodes beyond this single pipeline.
- Shipping model weights inside the repo (downloads on first use by `transparent-background`).

## References

- Upstream remover behavior: Comfy node `comfyui-inspyrenet-rembg` → `transparent_background.Remover`.
- User workflow file (on author’s machine, not in repo): ComfyUI `user/default/workflows/Remove Background.json`.
