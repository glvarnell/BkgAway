"""Qt desktop background removal using transparent-background (InSPyReNet)."""

__version__ = "1.1.0"

# Newest first. Shown on the About tab.
CHANGELOG = """\
## 1.1.0

- Settings tab for processing options and model cache controls
- Real download progress for model weights (percent + MB in the status bar)
- Removed TorchScript (JIT) option (often OOMs on 8GB GPUs during first-time compile)
- Auto-fill output folder when browsing files; confirm before overwriting outputs
- CUDA PyTorch wheel index updated to cu130

## 1.0.0 — Initial release

- Standalone Qt app (**rm_bkg**) matching ComfyUI Inspyrenet Rembg (`Remover`, RGBA PNG)
- Open files or folders (optional recursive); batch processing with progress and log
- Optional mask PNG, EXIF orientation, PNG compress level
- Warm model reuse across Runs; downscaled previews prepared off the UI thread
- Zoom / pan / double-click-fit previews; drag-and-drop input
- Persistent model weight cache under app data; Re-download weights option
- CUDA and CPU PyInstaller onedir builds (`rm-bkg-cuda`, `rm-bkg-cpu`)
"""
