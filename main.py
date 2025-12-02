#!/usr/bin/env python3
"""
Visitor Management System
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

from utils.path_helper import resource_path
from ui.main_window import MainWindow
from ui.splashscreen import SplashScreen
from utils.styles import MAIN_STYLE


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

    # APP INITIALIZED HERE
    app = QApplication(sys.argv)


    app.setWindowIcon(QIcon(resource_path("assets/logo.ico")))
    app.setApplicationName("M-Neo VMS")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("M-Neo Solutions")
    app.setFont(QFont("Segoe UI", 9))

    # GLOBAL STYLESHEET — must be applied AFTER app is created
    app.setStyleSheet(MAIN_STYLE)

    splash = SplashScreen()
    splash.show()

    def start_app():
        try:
            window = MainWindow()
            window.show()
            app.main_window = window

            # Run license + profile + login flow AFTER window is visible
            if not window.run_startup_flow():
                window.close()
                splash.close()
                sys.exit(0)

            splash.close()
        except Exception as e:
            splash.close()
            msg = QMessageBox(QMessageBox.Critical, "Startup Error", str(e), QMessageBox.Ok, None)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
            sys.exit(1)

    QTimer.singleShot(2000, start_app)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
