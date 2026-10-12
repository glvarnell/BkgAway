"""Stable cache location for transparent-background checkpoints."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_NOTICES_FALLBACK = """\
Third-party notices file was not found in this install.

This app uses transparent-background (InSPyReNet, MIT), PySide6/Qt (LGPL),
PyTorch (BSD-style), Pillow, and NumPy, plus transitive vision dependencies.

See the project repository file THIRD_PARTY_NOTICES.md for the full summary.
"""


def third_party_notices_candidates() -> list[Path]:
    """Search order for THIRD_PARTY_NOTICES.md (dev tree and frozen builds)."""
    names = ("THIRD_PARTY_NOTICES.md",)
    out: list[Path] = []
    pkg = Path(__file__).resolve().parent
    repo = pkg.parent
    out.append(repo / "THIRD_PARTY_NOTICES.md")
    out.append(pkg / "THIRD_PARTY_NOTICES.md")
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            for name in names:
                out.append(Path(meipass) / name)
        exe_dir = Path(sys.executable).resolve().parent
        for name in names:
            out.append(exe_dir / name)
            out.append(exe_dir / "_internal" / name)
    return out


def load_third_party_notices() -> str:
    for path in third_party_notices_candidates():
        try:
            if path.is_file():
                return path.read_text(encoding="utf-8")
        except OSError:
            continue
    return _NOTICES_FALLBACK


def weights_parent_directory() -> Path:
    """
    Parent directory for the library's `.transparent-background/` folder
    (see env `TRANSPARENT_BACKGROUND_FILE_PATH` in transparent_background.Remover).
    """
    explicit = os.environ.get("RM_BKG_WEIGHTS_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    try:
        from PySide6.QtCore import QCoreApplication, QStandardPaths

        if QCoreApplication.instance() is not None:
            loc = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            if loc:
                return Path(loc)
    except ImportError:
        pass

    return (Path.home() / ".bkgaway").resolve()


def transparent_background_cache_dir() -> Path:
    """`.transparent-background` under the parent from env or `weights_parent_directory()`."""
    cfg = os.environ.get("TRANSPARENT_BACKGROUND_FILE_PATH", "").strip()
    if cfg:
        parent = Path(cfg).expanduser().resolve()
    else:
        parent = weights_parent_directory()
    return parent / ".transparent-background"


def ensure_transparent_background_home() -> Path:
    """
    If unset, set `TRANSPARENT_BACKGROUND_FILE_PATH` to a stable per-user directory
    (Qt AppData when a QApplication exists, else ~/.bkgaway).
    """
    existing = os.environ.get("TRANSPARENT_BACKGROUND_FILE_PATH", "").strip()
    if existing:
        p = Path(existing).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    parent = weights_parent_directory()
    parent.mkdir(parents=True, exist_ok=True)
    os.environ["TRANSPARENT_BACKGROUND_FILE_PATH"] = str(parent)
    return parent


def clear_transparent_background_cache() -> tuple[bool, str]:
    """
    Delete the local `.transparent-background` cache so the next Remover()
    re-copies config and re-downloads checkpoints.
    """
    cache = transparent_background_cache_dir()
    if not cache.is_dir():
        return True, f"No cache directory at:\n{cache}"

    shutil.rmtree(cache)
    return True, f"Removed:\n{cache}"
