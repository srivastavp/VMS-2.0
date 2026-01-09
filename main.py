#!/usr/bin/env python3
"""
Visitor Management System
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

from utils.path_helper import resource_path, get_log_file_path
from ui.main_window import MainWindow
from ui.splashscreen import SplashScreen
from utils.styles import MAIN_STYLE


def setup_logging():
    log_path = str(get_log_file_path())
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.insert(
            0,
            RotatingFileHandler(
                log_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            ),
        )
    except Exception:
        # If file logging fails for any reason, keep console logging.
        pass

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    logging.info("Log file: %s", log_path)


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

    window = None

    def start_app():
        try:
            nonlocal window
            if window is None:
                window = MainWindow()
                window.show()
                app.main_window = window

            # Run license + profile + login flow AFTER window is visible
            if not window.run_startup_flow():
                # User canceled startup flow. Attempt to close the main window.
                # If they cancel the close confirmation, keep the app open and
                # re-run the startup flow so the dialogs appear again.
                window.close()
                splash.close()

                if window.isVisible():
                    QTimer.singleShot(0, start_app)
                    return

                app.quit()
                return

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
