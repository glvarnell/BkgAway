"""Entry point: python -m rm_bkg"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from rm_bkg.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Remove background")
    app.setOrganizationName("rm_bkg")
    w = MainWindow()
    w.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
