"""Drag-and-drop targets for image inputs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QLabel

from rm_bkg.remover_worker import SUPPORTED_SUFFIXES, list_images_in_dir


def drop_mime_may_accept(urls: list[QUrl]) -> bool:
    """
    Cheap check for drag enter/move: true if any local file looks like a supported
    image or any local directory (without scanning folder contents).
    """
    for url in urls:
        if not url.isLocalFile():
            continue
        p = Path(url.toLocalFile())
        if p.is_dir():
            return True
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES:
            return True
    return False


def paths_from_drop_mime(
    urls: list[QUrl],
    *,
    recursive: bool = False,
) -> list[Path]:
    """Build a unique ordered list of image paths from local file URLs (files + folders)."""
    out: list[Path] = []
    seen: set[Path] = set()
    for url in urls:
        if not url.isLocalFile():
            continue
        p = Path(url.toLocalFile())
        if p.is_dir():
            for q in list_images_in_dir(str(p), recursive=recursive):
                key = q.resolve()
                if key not in seen:
                    seen.add(key)
                    out.append(q)
        elif p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES:
            key = p.resolve()
            if key not in seen:
                seen.add(key)
                out.append(p)
    return out


class ImageDropLabel(QLabel):
    """QLabel that accepts drops of image files and folders of images."""

    paths_dropped = Signal(list)

    def __init__(self, *args, recursive: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self._recursive = recursive

    def set_recursive(self, recursive: bool) -> None:
        self._recursive = recursive

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and drop_mime_may_accept(event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls() and drop_mime_may_accept(event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = paths_from_drop_mime(
            event.mimeData().urls(),
            recursive=self._recursive,
        )
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()
