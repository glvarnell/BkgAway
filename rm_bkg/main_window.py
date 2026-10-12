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
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from rm_bkg import CHANGELOG, __version__
from rm_bkg.drop_widgets import ImageDropLabel
from rm_bkg.images import load_image_rgb, pil_to_qimage_rgb
from rm_bkg.preview_widgets import ZoomPreviewView
from rm_bkg.remover_worker import (
    RemoveBackgroundThread,
    SUPPORTED_SUFFIXES,
    clear_cached_remover,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"rm_bkg {__version__}")
        self.resize(1100, 720)

        self._input_paths: list[Path] = []
        self._thread: RemoveBackgroundThread | None = None
        self._run_timer = QElapsedTimer()
        self._current_file = ""
        self._device_line = ""
        self._last_batch_ok = 0
        self._last_batch_err = 0

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
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        work = QWidget()
        layout = QVBoxLayout(work)

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

        tabs.addTab(work, "Remove background")
        tabs.addTab(self._build_settings_tab(), "Settings")
        tabs.addTab(self._build_about_tab(), "About")

        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_left = QLabel("")
        sb.addWidget(self._status_left, stretch=1)

    def _on_recursive_toggled(self, checked: bool) -> None:
        self._input_label.set_recursive(checked)
        self._preview_orig.set_recursive_drops(checked)

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        processing = QGroupBox("Processing")
        pg = QVBoxLayout(processing)

        row1 = QHBoxLayout()
        self._save_mask = QCheckBox("Save mask PNG (_nobg_mask.png)")
        row1.addWidget(self._save_mask)
        self._recursive = QCheckBox("Scan folders recursively")
        self._recursive.setToolTip(
            "When opening or dropping a folder, include images in subfolders."
        )
        self._recursive.toggled.connect(self._on_recursive_toggled)
        row1.addWidget(self._recursive)
        row1.addStretch()
        pg.addLayout(row1)

        row2 = QHBoxLayout()
        self._exif = QCheckBox("Apply EXIF orientation")
        self._exif.setToolTip("Rotate/flip inputs according to EXIF orientation tags.")
        row2.addWidget(self._exif)
        row2.addWidget(QLabel("PNG compress:"))
        self._png_compress = QSpinBox()
        self._png_compress.setRange(0, 9)
        self._png_compress.setValue(6)
        self._png_compress.setToolTip(
            "PNG zlib level 0–9 (0 = faster/larger, 9 = slower/smaller). Default 6."
        )
        row2.addWidget(self._png_compress)
        row2.addStretch()
        pg.addLayout(row2)
        layout.addWidget(processing)

        model = QGroupBox("Model")
        mg = QVBoxLayout(model)
        self._btn_redownload_weights = QPushButton("Re-download weights…")
        self._btn_redownload_weights.setToolTip(
            "Delete cached model files so the next Run downloads them again."
        )
        self._btn_redownload_weights.clicked.connect(self._on_redownload_weights)
        row3 = QHBoxLayout()
        row3.addWidget(self._btn_redownload_weights)
        row3.addStretch()
        mg.addLayout(row3)

        self._weights_path_label = QLabel()
        self._weights_path_label.setWordWrap(True)
        self._weights_path_label.setStyleSheet("color: palette(mid); font-size: 11px;")
        self._refresh_weights_path_label()
        mg.addWidget(self._weights_path_label)
        layout.addWidget(model)

        layout.addStretch(1)
        return page

    def _build_about_tab(self) -> QWidget:
        from rm_bkg.paths import load_third_party_notices

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("rm_bkg")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addWidget(QLabel(f"Version {__version__}"))
        blurb = QLabel(
            "Background removal with transparent-background (InSPyReNet), "
            "matching the ComfyUI Inspyrenet Rembg path.\n\n"
            "Uses transparent-background, InSPyReNet, PySide6/Qt, PyTorch, "
            "Pillow, and NumPy. See Third-party notices for details."
        )
        blurb.setWordWrap(True)
        layout.addWidget(blurb)

        about_tabs = QTabWidget()
        changelog = QPlainTextEdit()
        changelog.setReadOnly(True)
        changelog.setPlainText(CHANGELOG.strip() + "\n")
        about_tabs.addTab(changelog, "Changelog")

        notices = QPlainTextEdit()
        notices.setReadOnly(True)
        notices.setPlainText(load_third_party_notices().strip() + "\n")
        about_tabs.addTab(notices, "Third-party notices")
        layout.addWidget(about_tabs, stretch=1)
        return page

    def _refresh_weights_path_label(self) -> None:
        from rm_bkg.paths import transparent_background_cache_dir

        self._weights_path_label.setText(
            "Model cache: " + str(transparent_background_cache_dir())
        )

    def _on_redownload_weights(self) -> None:
        from rm_bkg.paths import clear_transparent_background_cache

        r = QMessageBox.question(
            self,
            "Re-download weights?",
            "Delete the cached checkpoint (and local config copy) for transparent-background?\n\n"
            "The next Run will download the model again.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        clear_cached_remover()
        _ok, msg = clear_transparent_background_cache()
        QMessageBox.information(self, "Weights cache", msg)
        self._refresh_weights_path_label()

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
            if not self._out_edit.text().strip():
                self._out_edit.setText(str(self._input_paths[0].parent))
            self._update_input_summary()
            self._refresh_run_enabled()

    def _on_open_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Folder of images")
        if not folder:
            return
        from rm_bkg.remover_worker import list_images_in_dir

        self._input_paths = list_images_in_dir(
            folder, recursive=self._recursive.isChecked()
        )
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
            pil = load_image_rgb(
                str(path),
                exif_transpose=self._exif.isChecked(),
            )
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

    def _existing_outputs(self, out: Path) -> list[Path]:
        existing: list[Path] = []
        for p in self._input_paths:
            cand = out / f"{p.stem}_nobg.png"
            if cand.exists():
                existing.append(cand)
            if self._save_mask.isChecked():
                mask = out / f"{p.stem}_nobg_mask.png"
                if mask.exists():
                    existing.append(mask)
        return existing

    def _on_run(self) -> None:
        out = self._output_dir()
        if not out:
            return

        existing = self._existing_outputs(out)
        if existing:
            sample = "\n".join(str(p.name) for p in existing[:8])
            more = "" if len(existing) <= 8 else f"\n… and {len(existing) - 8} more"
            r = QMessageBox.question(
                self,
                "Overwrite outputs?",
                f"{len(existing)} output file(s) already exist and will be overwritten:\n\n"
                f"{sample}{more}\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                return

        self._log.clear()
        self._progress.setRange(0, 0)
        self._progress.setFormat("%p%")
        self._current_file = ""
        self._device_line = ""
        self._last_batch_ok = 0
        self._last_batch_err = 0
        self._run_timer.start()
        self._update_status_bar("Starting…")

        self._thread = RemoveBackgroundThread(
            list(self._input_paths),
            out,
            save_mask=self._save_mask.isChecked(),
            exif_transpose=self._exif.isChecked(),
            png_compress_level=self._png_compress.value(),
        )
        self._thread.model_status.connect(self._on_model_status)
        self._thread.download_progress.connect(self._on_download_progress)
        self._thread.processing_file.connect(self._on_processing_file)
        self._thread.progress.connect(self._on_progress)
        self._thread.file_finished.connect(self._on_file_finished)
        self._thread.log_line.connect(self._append_log)
        self._thread.failed.connect(self._on_failed)
        self._thread.batch_finished.connect(self._on_batch_finished)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()
        self._refresh_run_enabled()

    def _on_stop(self) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._append_log("Stop requested — will finish after the current image…")
            self._status_left.setText("Stopping after current image…")

    def _on_model_status(self, text: str) -> None:
        if text.startswith("Ready"):
            self._device_line = text
            total = len(self._input_paths)
            self._progress.setFormat("%v / %m")
            self._progress.setRange(0, max(1, total))
            self._progress.setValue(0)
        elif text.startswith("Loading"):
            # GPU/CPU load has no byte progress — busy indicator only.
            self._progress.setRange(0, 0)
            self._progress.setFormat("%p%")
        self._update_status_bar(text)

    def _on_download_progress(self, done: int, total: int) -> None:
        if total <= 0:
            self._progress.setRange(0, 0)
            self._progress.setFormat("Downloading…")
            self._status_left.setText(f"Downloading weights… {done / (1024 * 1024):.0f} MB")
            return
        pct = int(done * 100 / total)
        self._progress.setRange(0, 100)
        self._progress.setValue(pct)
        self._progress.setFormat("Downloading… %p%")
        self._status_left.setText(
            f"Downloading weights… {done / (1024 * 1024):.0f} / {total / (1024 * 1024):.0f} MB"
        )

    def _on_processing_file(self, name: str) -> None:
        self._current_file = name
        self._update_status_bar()

    def _on_progress(self, cur: int, total: int) -> None:
        self._progress.setFormat("%v / %m")
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

    def _on_file_finished(self, _out_path: str, orig, result_rgb) -> None:
        # Worker already downscaled and checkerboard-composited result_rgb.
        if isinstance(orig, Image.Image):
            pm = QPixmap.fromImage(pil_to_qimage_rgb(orig))
            self._preview_orig.set_full_pixmap(pm)
        if isinstance(result_rgb, Image.Image):
            pm = QPixmap.fromImage(pil_to_qimage_rgb(result_rgb))
            self._preview_result.set_full_pixmap(pm)

    def _append_log(self, line: str) -> None:
        self._log.appendPlainText(line)

    def _on_failed(self, msg: str) -> None:
        QMessageBox.critical(self, "Error", msg)

    def _on_batch_finished(self, ok: int, err: int) -> None:
        self._last_batch_ok = ok
        self._last_batch_err = err

    def _on_thread_finished(self) -> None:
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        self._progress.setFormat("%p%")
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._refresh_run_enabled()
        self._current_file = ""
        device = self._device_line
        self._device_line = ""
        ok, err = self._last_batch_ok, self._last_batch_err
        if err and not ok:
            self._status_left.setText(f"Finished with errors ({err} failed)")
            QMessageBox.warning(
                self,
                "Batch finished with errors",
                f"No images succeeded.\n\n{err} file(s) failed. See the log for details.",
            )
        elif err:
            self._status_left.setText(f"Done — {ok} ok, {err} failed")
            QMessageBox.warning(
                self,
                "Batch finished with errors",
                f"{ok} succeeded, {err} failed. See the log for details.",
            )
        else:
            parts = ["Idle"]
            if device:
                parts.append(device)
            if ok:
                parts.append(f"{ok} ok")
            self._status_left.setText("  •  ".join(parts))
        self._act_stop.setEnabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.wait(5000)
        super().closeEvent(event)
