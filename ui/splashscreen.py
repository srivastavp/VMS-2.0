from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

from utils.path_helper import resource_path


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()

        # Frameless + transparent background
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignCenter)

        # LOGO ONLY — no text
        logo_label = QLabel()
        pixmap = QPixmap(resource_path("assets/VMS.png"))

        # DPI-safe size
        pixmap = pixmap.scaled(
            200, 200,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(logo_label)

        # Size of splash (auto-fit to logo)
        self.setFixedSize(260, 260)
