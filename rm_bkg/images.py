"""Image helpers for preview (checkerboard compositing)."""

from __future__ import annotations

import numpy as np
from PIL import Image
from PySide6.QtGui import QImage


def composite_on_checkerboard(rgba: Image.Image, tile: int = 10) -> Image.Image:
    """Flatten RGBA onto a gray checkerboard for preview (RGB output)."""
    rgba = rgba.convert("RGBA")
    w, h = rgba.size
    yy, xx = np.mgrid[0:h, 0:w]
    checker = ((xx // tile + yy // tile) % 2) == 0
    c1 = np.array([204, 204, 204], dtype=np.uint8)
    c2 = np.array([153, 153, 153], dtype=np.uint8)
    arr = np.empty((h, w, 3), dtype=np.uint8)
    arr[checker] = c1
    arr[~checker] = c2
    bg = Image.fromarray(arr, "RGB")
    return Image.alpha_composite(bg.convert("RGBA"), rgba).convert("RGB")


def pil_to_qimage_rgb(pil_rgb: Image.Image) -> QImage:
    """Convert PIL RGB image to QImage (copying pixel data)."""
    pil_rgb = pil_rgb.convert("RGB")
    w, h = pil_rgb.size
    data = pil_rgb.tobytes("raw", "RGB")
    qimg = QImage(data, w, h, w * 3, QImage.Format.Format_RGB888)
    return qimg.copy()


def load_image_rgb(path: str, max_side: int = 2048) -> Image.Image:
    """Load image as RGB, downscale large previews for UI responsiveness."""
    im = Image.open(path)
    im = im.convert("RGB")
    w, h = im.size
    m = max(w, h)
    if m > max_side:
        scale = max_side / m
        im = im.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    return im
