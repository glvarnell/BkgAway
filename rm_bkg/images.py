"""Image helpers for preview (checkerboard compositing)."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageOps
from PySide6.QtGui import QImage

PREVIEW_MAX_SIDE = 2048


def downscale_max_side(im: Image.Image, max_side: int = PREVIEW_MAX_SIDE) -> Image.Image:
    """Return a copy scaled so max(width, height) <= max_side."""
    w, h = im.size
    m = max(w, h)
    if m <= max_side:
        return im.copy()
    scale = max_side / m
    return im.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)


def apply_exif_orientation(im: Image.Image) -> Image.Image:
    """Honor EXIF orientation tag when present."""
    return ImageOps.exif_transpose(im)


def composite_on_checkerboard(rgba: Image.Image, tile: int = 10) -> Image.Image:
    """Flatten RGBA onto a gray checkerboard for preview (RGB output)."""
    rgba = rgba.convert("RGBA")
    w, h = rgba.size
    t = max(1, int(tile))
    pat = np.empty((2 * t, 2 * t, 3), dtype=np.uint8)
    pat[:t, :t] = (204, 204, 204)
    pat[:t, t:] = (153, 153, 153)
    pat[t:, :t] = (153, 153, 153)
    pat[t:, t:] = (204, 204, 204)
    reps_y = (h + 2 * t - 1) // (2 * t)
    reps_x = (w + 2 * t - 1) // (2 * t)
    bg_arr = np.tile(pat, (reps_y, reps_x, 1))[:h, :w]
    bg = Image.fromarray(bg_arr, "RGB").convert("RGBA")
    return Image.alpha_composite(bg, rgba).convert("RGB")


def pil_to_qimage_rgb(pil_rgb: Image.Image) -> QImage:
    """Convert PIL RGB image to an owned QImage (single detach copy)."""
    arr = np.ascontiguousarray(pil_rgb.convert("RGB"), dtype=np.uint8)
    h, w, _ = arr.shape
    # QImage does not take ownership of arr; copy() detaches into Qt-owned memory once.
    return QImage(arr.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()


def load_image_rgb(
    path: str,
    max_side: int = PREVIEW_MAX_SIDE,
    *,
    exif_transpose: bool = False,
) -> Image.Image:
    """Load image as RGB, optionally honor EXIF, downscale for UI responsiveness."""
    im = Image.open(path)
    if exif_transpose:
        im = apply_exif_orientation(im)
    im = im.convert("RGB")
    return downscale_max_side(im, max_side)
