"""Background-removal worker thread (transparent-background Remover)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PIL import Image
from PySide6.QtCore import QThread, Signal

from rm_bkg.images import (
    PREVIEW_MAX_SIDE,
    apply_exif_orientation,
    composite_on_checkerboard,
    downscale_max_side,
)


SUPPORTED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

# One warm Remover reused across Runs (cleared when weights are deleted).
_cached_remover: Any | None = None


def clear_cached_remover() -> None:
    """Drop the cached Remover (call after deleting weight cache)."""
    global _cached_remover
    _cached_remover = None
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def get_cached_remover() -> Any:
    """Return a process-wide Remover(), creating it on first use."""
    global _cached_remover
    if _cached_remover is None:
        from transparent_background import Remover

        _cached_remover = Remover()
    return _cached_remover

def list_images_in_dir(folder: str, *, recursive: bool = False) -> list[Path]:
    root = Path(folder)
    if not root.is_dir():
        return []
    it = root.rglob("*") if recursive else root.iterdir()
    paths = [
        p
        for p in it
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    return sorted(paths)


class RemoveBackgroundThread(QThread):
    """Runs transparent_background.Remover on a list of images."""

    model_status = Signal(str)
    download_progress = Signal(int, int)  # bytes_done, bytes_total (0 = unknown)
    processing_file = Signal(str)
    progress = Signal(int, int)  # completed count, total
    file_finished = Signal(str, object, object)  # out_path, preview_orig_rgb, preview_result_rgb
    log_line = Signal(str)
    failed = Signal(str)
    batch_finished = Signal(int, int)  # ok_count, error_count

    def __init__(
        self,
        input_paths: list[Path],
        output_dir: Path,
        *,
        save_mask: bool,
        exif_transpose: bool = False,
        png_compress_level: int = 6,
    ):
        super().__init__()
        self.input_paths = input_paths
        self.output_dir = output_dir
        self.save_mask = save_mask
        self.exif_transpose = exif_transpose
        self.png_compress_level = max(0, min(9, int(png_compress_level)))

    def run(self) -> None:
        os.environ.setdefault("TQDM_DISABLE", "1")
        from rm_bkg.paths import (
            checkpoint_needs_download,
            ensure_checkpoint,
            ensure_transparent_background_home,
        )

        ensure_transparent_background_home()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            from transparent_background import Remover  # noqa: F401 — import check
        except ImportError as e:
            self.failed.emit(
                "Could not import transparent_background. Install dependencies "
                f"(see README): {e}"
            )
            self.batch_finished.emit(0, 0)
            return

        try:
            if _cached_remover is None:
                if checkpoint_needs_download():
                    self.model_status.emit("Downloading model weights…")
                    ensure_checkpoint(
                        on_progress=lambda done, total: self.download_progress.emit(
                            done, total
                        )
                    )
                self.model_status.emit("Loading model…")
            remover = get_cached_remover()
        except Exception as e:
            self.failed.emit(f"Failed to initialize Remover: {e}")
            self.batch_finished.emit(0, 0)
            return

        self.model_status.emit(f"Ready ({getattr(remover, 'device', 'unknown')})")
        total = len(self.input_paths)
        ok = 0
        err = 0
        self.progress.emit(0, total)

        for i, in_path in enumerate(self.input_paths, start=1):
            if self.isInterruptionRequested():
                self.log_line.emit("Stopped by user (after current image).")
                break
            self.processing_file.emit(in_path.name)
            try:
                self._process_one(remover, in_path)
                ok += 1
            except Exception as e:
                err += 1
                self.log_line.emit(f"{in_path.name}: ERROR — {e}")
            self.progress.emit(ok + err, total)

        self.batch_finished.emit(ok, err)

    def _process_one(self, remover, in_path: Path) -> None:
        out_path = self.output_dir / f"{in_path.stem}_nobg.png"
        img = Image.open(in_path)
        if self.exif_transpose:
            img = apply_exif_orientation(img)
        img = img.convert("RGB")

        out_rgba = remover.process(img, type="rgba")
        if not isinstance(out_rgba, Image.Image):
            raise TypeError("Unexpected process() return type")

        out_rgba.save(
            out_path,
            format="PNG",
            compress_level=self.png_compress_level,
        )

        if self.save_mask:
            alpha = out_rgba.split()[-1]
            mask_path = self.output_dir / f"{in_path.stem}_nobg_mask.png"
            alpha.save(
                mask_path,
                format="PNG",
                compress_level=self.png_compress_level,
            )

        # Downscale + checkerboard on worker thread so the UI only paints pixmaps.
        preview_orig = downscale_max_side(img, PREVIEW_MAX_SIDE)
        preview_rgba = downscale_max_side(out_rgba, PREVIEW_MAX_SIDE)
        preview_result = composite_on_checkerboard(preview_rgba)
        self.file_finished.emit(str(out_path), preview_orig, preview_result)
        self.log_line.emit(f"{in_path.name} → {out_path.name}")
