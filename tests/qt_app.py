"""
Shared headless QApplication for tests that touch Qt (QPrinterInfo,
QPainter, etc.) without needing a real display or a physical printer.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


def get_app():
    return _app
