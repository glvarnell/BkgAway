"""Background-removal worker thread (transparent-background Remover)."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QThread, Signal

from rm_bkg.images import load_image_rgb


SUPPORTED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def list_images_in_dir(folder: str) -> list[Path]:
    paths: list[Path] = []
    root = Path(folder)
    for p in sorted(root.iterdir()):
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES:
            paths.append(p)
    return paths


class RemoveBackgroundThread(QThread):
    """Runs transparent_background.Remover on a list of images."""

    model_status = Signal(str)
    processing_file = Signal(str)
    progress = Signal(int, int)  # current 1-based, total
    file_finished = Signal(str, object, object)  # out_path, orig_pil_rgb, result_rgba_pil
    log_line = Signal(str)
    failed = Signal(str)

    def __init__(self, input_paths: list[Path], output_dir: Path, save_mask: bool):
        super().__init__()
        self.input_paths = input_paths
        self.output_dir = output_dir
        self.save_mask = save_mask

    def run(self) -> None:
        os.environ.setdefault("TQDM_DISABLE", "1")
        from rm_bkg.paths import ensure_transparent_background_home

        ensure_transparent_background_home()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            from transparent_background import Remover
        except ImportError as e:
            self.failed.emit(
                "Could not import transparent_background. Install dependencies "
                f"(see README): {e}"
            )
            return

        self.model_status.emit("Loading model (first run may download weights)…")
        try:
            remover = Remover()
        except Exception as e:
            self.failed.emit(f"Failed to initialize Remover: {e}")
            return

        self.model_status.emit(f"Ready ({getattr(remover, 'device', 'unknown')})")

        total = len(self.input_paths)
        for i, in_path in enumerate(self.input_paths, start=1):
            if self.isInterruptionRequested():
                self.log_line.emit("Stopped by user.")
                break
            self.processing_file.emit(in_path.name)
            self.progress.emit(i, total)
            try:
                self._process_one(remover, in_path)
            except Exception as e:
                self.log_line.emit(f"{in_path.name}: ERROR — {e}")
                continue

    def _process_one(self, remover, in_path: Path) -> None:
        out_path = self.output_dir / f"{in_path.stem}_nobg.png"
        img = Image.open(in_path).convert("RGB")
        out_rgba = remover.process(img, type="rgba")
        if not isinstance(out_rgba, Image.Image):
            raise TypeError("Unexpected process() return type")
        out_rgba.save(out_path, format="PNG")

        if self.save_mask:
            alpha = out_rgba.split()[-1]
            mask_path = self.output_dir / f"{in_path.stem}_nobg_mask.png"
            alpha.save(mask_path, format="PNG")

        orig_preview = load_image_rgb(str(in_path))
        self.file_finished.emit(str(out_path), orig_preview, out_rgba)
        self.log_line.emit(f"{in_path.name} → {out_path.name}")
