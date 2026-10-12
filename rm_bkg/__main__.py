"""Entry point: python -m rm_bkg"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from rm_bkg import __version__
from rm_bkg.main_window import MainWindow
from rm_bkg.paths import ensure_transparent_background_home


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("rm_bkg")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("rm_bkg")
    ensure_transparent_background_home()
    w = MainWindow()
    w.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
