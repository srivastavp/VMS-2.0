from PyQt5.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap, QFont, QPainter
from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtProperty

from utils.path_helper import resource_path
from utils.styles import PRIMARY_COLOR


class FadeLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._opacity = 0.0

    def setOpacity(self, value):
        self._opacity = value
        self.update()

    def getOpacity(self):
        return self._opacity

    opacity = pyqtProperty(float, fget=getOpacity, fset=setOpacity)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(self._opacity)
        super().paintEvent(event)


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(40, 40, 40, 40)

        # Load logo correctly from EXE
        logo = QLabel()
        pixmap = QPixmap(resource_path("assets/logo.png"))
        pixmap = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)

        self.title_label = FadeLabel("M-Neo Visitor Management System")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {PRIMARY_COLOR};")

        layout.addWidget(logo)
        layout.addWidget(self.title_label)

        self.setFixedSize(430, 350)

        self.animation = QPropertyAnimation(self.title_label, b"opacity")
        self.animation.setDuration(1200)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()
