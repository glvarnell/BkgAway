"""Qt desktop background removal using transparent-background (InSPyReNet)."""

__version__ = "1.0.0"

# Newest first. Shown on the About tab.
CHANGELOG = """\
## 1.0.0 — Initial release

- Standalone Qt app (**rm_bkg**) matching ComfyUI Inspyrenet Rembg (`Remover`, RGBA PNG)
- Open files or folders; batch processing with progress and log
- Optional mask PNG (`_nobg_mask.png`)
- Zoom / pan / double-click-fit previews; drag-and-drop input
- Persistent model weight cache under app data; Re-download weights option
- CUDA and CPU PyInstaller onedir builds (`rm-bkg-cuda`, `rm-bkg-cpu`)
"""
