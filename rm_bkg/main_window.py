"""Main Qt window."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QElapsedTimer, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from rm_bkg.drop_widgets import ImageDropLabel
from rm_bkg.images import composite_on_checkerboard, load_image_rgb, pil_to_qimage_rgb
from rm_bkg.preview_widgets import ZoomPreviewView
from rm_bkg.remover_worker import RemoveBackgroundThread, SUPPORTED_SUFFIXES


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Remove background")
        self.resize(1100, 720)

        self._input_paths: list[Path] = []
        self._thread: RemoveBackgroundThread | None = None
        self._run_timer = QElapsedTimer()
        self._current_file = ""
        self._device_line = ""

        self._build_ui()
        self._build_toolbar()
        self._refresh_run_enabled()

    def _build_toolbar(self) -> None:
        bar = QToolBar()
        bar.setMovable(False)
        self.addToolBar(bar)

        act_open = QAction("Open…", self)
        act_open.triggered.connect(self._on_open_files)
        bar.addAction(act_open)

        act_folder = QAction("Open folder…", self)
        act_folder.triggered.connect(self._on_open_folder)
        bar.addAction(act_folder)

        self._act_run = QAction("Run", self)
        self._act_run.triggered.connect(self._on_run)
        bar.addAction(self._act_run)

        self._act_stop = QAction("Stop", self)
        self._act_stop.setEnabled(False)
        self._act_stop.triggered.connect(self._on_stop)
        bar.addAction(self._act_stop)

        act_reveal = QAction("Reveal output", self)
        act_reveal.triggered.connect(self._on_reveal_output)
        bar.addAction(act_reveal)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        io = QGroupBox("Input / output")
        iog = QGridLayout(io)
        self._input_label = ImageDropLabel("No files selected")
        self._input_label.setWordWrap(True)
        self._input_label.setMinimumHeight(48)
        self._input_label.setToolTip("Drag image files or folders here, or use Browse…")
        self._input_label.paths_dropped.connect(self._on_paths_dropped)
        btn_in = QPushButton("Browse files…")
        btn_in.clicked.connect(self._on_open_files)
        iog.addWidget(QLabel("Input:"), 0, 0)
        iog.addWidget(self._input_label, 0, 1)
        iog.addWidget(btn_in, 0, 2)

        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Output folder…")
        btn_out = QPushButton("Browse…")
        btn_out.clicked.connect(self._on_browse_output)
        iog.addWidget(QLabel("Output folder:"), 1, 0)
        iog.addWidget(self._out_edit, 1, 1)
        iog.addWidget(btn_out, 1, 2)
        layout.addWidget(io)

        opt = QGroupBox("Options")
        og = QHBoxLayout(opt)
        self._save_mask = QCheckBox("Save mask PNG (_nobg_mask.png)")
        og.addWidget(self._save_mask)
        og.addStretch()
        layout.addWidget(opt)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(QLabel("Original"))
        self._preview_orig = ZoomPreviewView(accept_file_drops=True)
        self._preview_orig.setMinimumHeight(320)
        self._preview_orig.setToolTip(
            "Scroll wheel to zoom; after zooming, drag to pan. Double-click to fit. "
            "Drag images or folders here…"
        )
        self._preview_orig.paths_dropped.connect(self._on_paths_dropped)
        lv.addWidget(self._preview_orig)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.addWidget(QLabel("Result (checkerboard = transparent)"))
        self._preview_result = ZoomPreviewView(accept_file_drops=False)
        self._preview_result.setMinimumHeight(320)
        self._preview_result.setToolTip(
            "Scroll wheel to zoom; after zooming, drag to pan. Double-click to fit."
        )
        rv.addWidget(self._preview_result)

        splitter.addWidget(left)
        splitter.addWidget(right)
        layout.addWidget(splitter, stretch=1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        log = QGroupBox("Log")
        lg = QVBoxLayout(log)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        self._log.setFixedHeight(120)
        lg.addWidget(self._log)
        layout.addWidget(log)

        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_left = QLabel("")
        sb.addWidget(self._status_left, stretch=1)

    def _browse_output_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Output folder")
        if path:
            self._out_edit.setText(path)
            self._refresh_run_enabled()

    def _on_browse_output(self) -> None:
        self._browse_output_path()

    def _on_paths_dropped(self, paths: list) -> None:
        if self._thread is not None:
            self._status_left.setText("Stop the current run before changing input.")
            return
        if not paths:
            return
        self._input_paths = [Path(p) for p in paths]
        if not self._out_edit.text().strip():
            self._out_edit.setText(str(self._input_paths[0].parent))
        self._update_input_summary()
        self._refresh_run_enabled()

    def _on_open_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Images",
            "",
            "Images ("
            + " ".join("*" + s for s in sorted(SUPPORTED_SUFFIXES))
            + ");;All files (*)",
        )
        if paths:
            self._input_paths = [Path(p) for p in paths]
            self._update_input_summary()
            self._refresh_run_enabled()

    def _on_open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Folder of images")
        if not folder:
            return
        from rm_bkg.remover_worker import list_images_in_dir

        self._input_paths = list_images_in_dir(folder)
        if not self._input_paths:
            QMessageBox.information(self, "No images", "No supported images found in that folder.")
        self._update_input_summary()
        if not self._out_edit.text().strip():
            self._out_edit.setText(folder)
        self._refresh_run_enabled()

    def _update_input_summary(self) -> None:
        n = len(self._input_paths)
        if n == 0:
            self._input_label.setText("No files selected")
        elif n == 1:
            self._input_label.setText(str(self._input_paths[0]))
        else:
            self._input_label.setText(f"{n} files selected")
        self._preview_input_selection()

    def _preview_input_selection(self) -> None:
        """Show the original image as soon as input is chosen; clear result until Run."""
        self._preview_result.show_placeholder("(Run to see result)")

        if not self._input_paths:
            self._preview_orig.show_placeholder("(No image selected)")
            return

        path = self._input_paths[0]
        try:
            pil = load_image_rgb(str(path))
            pm = QPixmap.fromImage(pil_to_qimage_rgb(pil))
            self._preview_orig.set_full_pixmap(pm)
        except Exception as e:
            self._preview_orig.show_placeholder(f"Could not load preview:\n{e}")

    def _output_dir(self) -> Path | None:
        t = self._out_edit.text().strip()
        return Path(t) if t else None

    def _refresh_run_enabled(self) -> None:
        ok = bool(self._input_paths) and self._output_dir() is not None
        busy = self._thread is not None
        self._act_run.setEnabled(ok and not busy)
        self._act_stop.setEnabled(busy)

    def _on_reveal_output(self) -> None:
        d = self._output_dir()
        if d and d.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(d.resolve())))
        else:
            QMessageBox.warning(self, "Output", "Choose a valid output folder first.")

    def _on_run(self) -> None:
        out = self._output_dir()
        if not out:
            return
        self._log.clear()
        self._progress.setRange(0, 0)
        self._current_file = ""
        self._device_line = ""
        self._run_timer.start()
        self._update_status_bar("Starting…")

        self._thread = RemoveBackgroundThread(
            list(self._input_paths),
            out,
            save_mask=self._save_mask.isChecked(),
        )
        self._thread.model_status.connect(self._on_model_status)
        self._thread.processing_file.connect(self._on_processing_file)
        self._thread.progress.connect(self._on_progress)
        self._thread.file_finished.connect(self._on_file_finished)
        self._thread.log_line.connect(self._append_log)
        self._thread.failed.connect(self._on_failed)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()  # QThread.finished fires when run() returns
        self._refresh_run_enabled()

    def _on_stop(self) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._append_log("Stop requested…")

    def _on_model_status(self, text: str) -> None:
        if text.startswith("Ready"):
            self._device_line = text
        self._update_status_bar(text)
        if text.startswith("Ready"):
            total = len(self._input_paths)
            self._progress.setRange(0, max(1, total))
            self._progress.setValue(0)

    def _on_processing_file(self, name: str) -> None:
        self._current_file = name
        self._update_status_bar()

    def _on_progress(self, cur: int, total: int) -> None:
        self._progress.setMaximum(max(1, total))
        self._progress.setValue(cur)
        self._update_status_bar()

    def _update_status_bar(self, message: str | None = None) -> None:
        if message is not None and not self._device_line:
            self._status_left.setText(message)
            return
        elapsed_s = self._run_timer.elapsed() / 1000.0
        parts: list[str] = []
        if self._current_file:
            parts.append(self._current_file)
        parts.append(f"{elapsed_s:.1f}s")
        if self._device_line:
            parts.append(self._device_line)
        self._status_left.setText("  •  ".join(parts))

    def _on_file_finished(self, _out_path: str, orig, rgba) -> None:
        if isinstance(orig, Image.Image):
            pm = QPixmap.fromImage(pil_to_qimage_rgb(orig))
            self._preview_orig.set_full_pixmap(pm)
        if isinstance(rgba, Image.Image):
            flat = composite_on_checkerboard(rgba)
            pm = QPixmap.fromImage(pil_to_qimage_rgb(flat))
            self._preview_result.set_full_pixmap(pm)

    def _append_log(self, line: str) -> None:
        self._log.appendPlainText(line)

    def _on_failed(self, msg: str) -> None:
        QMessageBox.critical(self, "Error", msg)

    def _on_thread_finished(self) -> None:
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._refresh_run_enabled()
        self._current_file = ""
        self._device_line = ""
        self._status_left.setText("Idle")
        self._act_stop.setEnabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.wait(5000)
        super().closeEvent(event)
