"""Stable cache location for transparent-background checkpoints."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import urllib.request
from collections.abc import Callable
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

    return (Path.home() / ".rm_bkg").resolve()


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
    (Qt AppData when a QApplication exists, else ~/.rm_bkg).
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


def _package_config_path() -> Path:
    import transparent_background

    return Path(transparent_background.__file__).resolve().parent / "config.yaml"


def _load_mode_meta(mode: str = "base") -> dict:
    """Read checkpoint URL/name/md5 for *mode* from the user or package config."""
    import yaml

    ensure_transparent_background_home()
    cache = transparent_background_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    user_cfg = cache / "config.yaml"
    if not user_cfg.is_file():
        shutil.copy(_package_config_path(), user_cfg)

    with user_cfg.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if mode not in data:
        raise KeyError(f"Unknown transparent-background mode: {mode!r}")
    meta = data[mode]
    return {
        "url": meta["url"],
        "md5": meta.get("md5"),
        "ckpt_name": meta["ckpt_name"],
    }


def _file_md5(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def checkpoint_needs_download(mode: str = "base") -> bool:
    """True if the checkpoint is missing or its MD5 does not match config."""
    meta = _load_mode_meta(mode)
    dest = transparent_background_cache_dir() / meta["ckpt_name"]
    if not dest.is_file():
        return True
    expected = meta.get("md5")
    if expected is None:
        return False
    return _file_md5(dest) != expected


def ensure_checkpoint(
    mode: str = "base",
    *,
    on_progress: Callable[[int, int], None] | None = None,
) -> Path:
    """
    Ensure the checkpoint for *mode* is present (and MD5-ok).

    Downloads with byte progress via *on_progress(bytes_done, bytes_total)*
    when the file is missing or the MD5 does not match. *bytes_total* may be
    0 if the server omits Content-Length.
    """
    meta = _load_mode_meta(mode)
    cache = transparent_background_cache_dir()
    dest = cache / meta["ckpt_name"]
    expected_md5 = meta.get("md5")

    if dest.is_file():
        if expected_md5 is None or _file_md5(dest) == expected_md5:
            return dest
        dest.unlink(missing_ok=True)

    url = meta["url"]
    tmp = dest.with_suffix(dest.suffix + ".partial")
    if tmp.exists():
        tmp.unlink()

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "rm_bkg"},
    )
    last_pct = -1
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        if on_progress is not None:
            on_progress(0, total)
            last_pct = 0
        with tmp.open("wb") as out:
            while True:
                block = resp.read(256 * 1024)
                if not block:
                    break
                out.write(block)
                done += len(block)
                if on_progress is None:
                    continue
                if total <= 0:
                    on_progress(done, 0)
                    continue
                pct = int(done * 100 / total)
                if pct != last_pct:
                    last_pct = pct
                    on_progress(done, total)

    if expected_md5 is not None:
        got = _file_md5(tmp)
        if got != expected_md5:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(
                f"Checksum mismatch for {dest.name}: expected {expected_md5}, got {got}"
            )

    tmp.replace(dest)
    if on_progress is not None and total > 0:
        on_progress(total, total)
    return dest
