"""Zoomable image previews (mouse wheel) with optional file drop."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
    QPainter,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView

from rm_bkg.drop_widgets import paths_from_drop_mime


class ZoomPreviewView(QGraphicsView):
    """Fit-to-view pixmap; wheel zooms (cursor anchor); when zoomed, left-drag pans; double-click refits."""

    paths_dropped = Signal(list)

    def __init__(self, accept_file_drops: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._accept_file_drops = accept_file_drops
        self._manual_zoom = False
        self._pix_item = QGraphicsPixmapItem()
        self._text_item = QGraphicsTextItem()
        self._text_item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        scene = QGraphicsScene(self)
        scene.addItem(self._pix_item)
        scene.addItem(self._text_item)
        self.setScene(scene)

        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setStyleSheet("background: palette(mid);")

        if accept_file_drops:
            self.setAcceptDrops(True)

        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def _refresh_drag_mode(self) -> None:
        """Left-drag pan only after wheel-zoom; otherwise file drops / clicks behave normally."""
        if self._text_item.isVisible() or self._pix_item.pixmap().isNull():
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            return
        if self._manual_zoom:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def show_placeholder(self, text: str) -> None:
        self._manual_zoom = False
        self.resetTransform()
        self._pix_item.setPixmap(QPixmap())
        self._pix_item.setVisible(False)
        self._text_item.setPlainText(text)
        self._text_item.setVisible(True)
        self.scene().setSceneRect(-400, -300, 800, 600)
        r = self.scene().sceneRect()
        br = self._text_item.boundingRect()
        self._text_item.setPos(
            QPointF(r.center().x() - br.width() / 2, r.center().y() - br.height() / 2)
        )
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._refresh_drag_mode()

    def set_full_pixmap(self, pm: QPixmap | None) -> None:
        """Show full-resolution pixmap fitted to the view; clears placeholder."""
        self._manual_zoom = False
        self.resetTransform()
        self._text_item.setVisible(False)
        self._text_item.setPlainText("")
        if pm is None or pm.isNull():
            self._pix_item.setPixmap(QPixmap())
            self._pix_item.setVisible(False)
            self.scene().setSceneRect(0, 0, 1, 1)
            self._refresh_drag_mode()
            return
        self._pix_item.setVisible(True)
        self._pix_item.setPixmap(pm)
        self._pix_item.setPos(0, 0)
        self.scene().setSceneRect(self._pix_item.boundingRect())
        self.fitInView(self._pix_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._refresh_drag_mode()

    def clear(self) -> None:
        self.set_full_pixmap(None)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._text_item.isVisible():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            return
        if not self._pix_item.pixmap().isNull() and not self._manual_zoom:
            self.resetTransform()
            self.fitInView(self._pix_item, Qt.AspectRatioMode.KeepAspectRatio)
            self._refresh_drag_mode()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self._text_item.isVisible()
            and not self._pix_item.pixmap().isNull()
        ):
            self._manual_zoom = False
            self.resetTransform()
            self.fitInView(self._pix_item, Qt.AspectRatioMode.KeepAspectRatio)
            self._refresh_drag_mode()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._text_item.isVisible() or self._pix_item.pixmap().isNull():
            super().wheelEvent(event)
            return
        dy = event.angleDelta().y()
        if dy == 0:
            return
        factor = 1.12 if dy > 0 else 1 / 1.12
        self._manual_zoom = True
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.scale(factor, factor)
        self._refresh_drag_mode()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not self._accept_file_drops or not event.mimeData().hasUrls():
            event.ignore()
            return
        if paths_from_drop_mime(event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if not self._accept_file_drops:
            event.ignore()
            return
        if paths_from_drop_mime(event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if not self._accept_file_drops:
            event.ignore()
            return
        paths = paths_from_drop_mime(event.mimeData().urls())
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()
