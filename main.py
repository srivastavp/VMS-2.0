#!/usr/bin/env python3
"""
Visitor Management System
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

from utils.path_helper import resource_path
from ui.main_window import MainWindow
from ui.splashscreen import SplashScreen


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('visitor_management.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    setup_logging()

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("assets/logo.ico")))
    app.setApplicationName("M-Neo VMS")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("M-Neo Solutions")
    app.setFont(QFont("Segoe UI", 9))

    splash = SplashScreen()
    splash.show()

    def start_app():
        try:
            window = MainWindow()
            window.show()
            splash.close()
            app.main_window = window
        except Exception as e:
            splash.close()
            QMessageBox.critical(None, "Startup Error", str(e))
            sys.exit(1)

    QTimer.singleShot(2000, start_app)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
