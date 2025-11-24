# ui/main_window.py

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QLabel,
    QPushButton, QHBoxLayout, QToolBar, QAction, QApplication, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from pathlib import Path
import json
from datetime import datetime
import sys
import logging

from utils.license import LicenseManager
from database import DatabaseManager
from utils.styles import MAIN_STYLE

from ui.registration import RegistrationWidget
from ui.dashboard import DashboardWidget
from ui.active_visitors import ActiveVisitorsWidget
from ui.history import HistoryWidget
from ui.all_records import AllRecordsWidget


# -------------------------
# Paths & Config
# -------------------------
APP_BASE = Path(__file__).resolve().parents[1]
DATA_DIR = APP_BASE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = DATA_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except:
            return {}
    return {}


def save_config(data: dict):
    try:
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except:
        logging.exception("Failed to save config")


# -------------------------
# Shared Popup Style (A1-C)
# -------------------------
POPUP_BG = """
background-color: #ffffff;
border-radius: 14px;
"""

HEADER_STYLE = """
background: qlineargradient(
    x1:0, y1:0, x2:1, y2:0,
    stop:0 #7C5F7E, stop:1 #9d8fa0
);
color: white;
padding: 18px;
font-size: 18px;
font-weight: bold;
border-top-left-radius: 14px;
border-top-right-radius: 14px;
"""

INPUT_STYLE = """
QLineEdit {
    border: 2px solid #d8cfe0;
    border-radius: 6px;
    padding: 8px;
    font-size: 11pt;
}
QLineEdit:focus {
    border-color: #7C5F7E;
}
"""

BTN_PRIMARY = """
QPushButton {
    background-color: #7C5F7E;
    color: white;
    padding: 10px 24px;
    border-radius: 6px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #8d6f8f;
}
"""

BTN_SECONDARY = """
QPushButton {
    background-color: #f3edf7;
    color: #4a3b4d;
    padding: 10px 24px;
    border-radius: 6px;
}
"""


# ==============================================================
# License Dialog — supports "activate" and "login"
# ==============================================================
class LicenseDialog(QDialog):
    def __init__(self, license_manager: LicenseManager, mode: str = "activate", parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.mode = mode  # activate | login
        self.setModal(True)
        self.setFixedSize(520, 380)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._build_ui()

    def _build_ui(self):
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)

        # Header
        title = "License Activation" if self.mode == "activate" else "Log In"
        header = QLabel(title)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(HEADER_STYLE)
        wrapper.addWidget(header)

        # Body Frame
        body = QFrame()
        body.setStyleSheet(POPUP_BG)
        layout = QFormLayout(body)
        layout.setContentsMargins(30, 30, 30, 30)
        wrapper.addWidget(body)

        # MAC
        device_info = self.license_manager.get_current_device_info()
        mac = device_info.get("mac_address", "")

        mac_row = QHBoxLayout()
        self.mac_display = QLineEdit(mac)
        self.mac_display.setReadOnly(True)
        self.mac_display.setStyleSheet(INPUT_STYLE)
        mac_row.addWidget(self.mac_display)

        copy_btn = QPushButton("Copy")
        copy_btn.setStyleSheet(BTN_SECONDARY)
        copy_btn.clicked.connect(self._copy_mac)
        mac_row.addWidget(copy_btn)

        layout.addRow("MAC Address:", mac_row)

        # Expiry only for activation
        if self.mode == "activate":
            self.expiry_input = QLineEdit()
            self.expiry_input.setPlaceholderText("YYYY-MM-DD")
            self.expiry_input.setStyleSheet(INPUT_STYLE)
            layout.addRow("Expiry Date:", self.expiry_input)

        # License Key
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.license_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("License Key:", self.license_input)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()

        action_label = "Activate" if self.mode == "activate" else "Log In"
        action_btn = QPushButton(action_label)
        action_btn.setStyleSheet(BTN_PRIMARY)
        action_btn.clicked.connect(self._on_action)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(BTN_SECONDARY)
        cancel_btn.clicked.connect(self.reject)

        btns.addWidget(cancel_btn)
        btns.addWidget(action_btn)
        layout.addRow("", btns)

    def _copy_mac(self):
        QApplication.clipboard().setText(self.mac_display.text())
        QMessageBox.information(self, "Copied", "MAC address copied to clipboard.")

    def _on_action(self):
        key = self.license_input.text().strip()

        if not key:
            QMessageBox.warning(self, "Missing", "License key is required.")
            return

        if self.mode == "activate":
            expiry = self.expiry_input.text().strip()
            try:
                datetime.strptime(expiry, "%Y-%m-%d")
            except:
                QMessageBox.warning(self, "Invalid", "Expiry must be YYYY-MM-DD.")
                return

            if not self.license_manager.validate_license(key, expiry):
                QMessageBox.warning(self, "Invalid", "Key does not match device + expiry.")
                return

            if not self.license_manager.activate_license(key, expiry):
                QMessageBox.critical(self, "Error", "Failed to save license.")
                return

        else:  # login
            if not self.license_manager.login_with_key(key):
                QMessageBox.warning(self, "Login Failed", "Invalid or expired key.")
                return

        self.accept()


# ==============================================================
# Welcome Dialog — organization details (A1-C styled)
# ==============================================================
class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setFixedSize(520, 460)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._build_ui()

    def _build_ui(self):
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Welcome — Organization Setup")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(HEADER_STYLE)
        wrapper.addWidget(header)

        body = QFrame()
        body.setStyleSheet(POPUP_BG)
        layout = QFormLayout(body)
        layout.setContentsMargins(30, 30, 30, 30)
        wrapper.addWidget(body)

        # Inputs
        self.org = QLineEdit()
        self.loc = QLineEdit()
        self.region = QLineEdit()
        self.address = QLineEdit()
        self.country = QLineEdit()

        for w in [self.org, self.loc, self.region, self.address, self.country]:
            w.setStyleSheet(INPUT_STYLE)

        cfg = load_config()
        self.org.setText(cfg.get("organization_name", ""))
        self.loc.setText(cfg.get("location_name", ""))
        self.region.setText(cfg.get("region", ""))
        self.address.setText(cfg.get("address", ""))
        self.country.setText(cfg.get("country", ""))

        layout.addRow("Organization:", self.org)
        layout.addRow("Location:", self.loc)
        layout.addRow("Region:", self.region)
        layout.addRow("Address:", self.address)
        layout.addRow("Country:", self.country)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(BTN_PRIMARY)
        save_btn.clicked.connect(self._save)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(BTN_SECONDARY)
        cancel_btn.clicked.connect(self.reject)

        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addRow("", btns)

    def _save(self):
        if not self.org.text().strip() or not self.loc.text().strip():
            QMessageBox.warning(self, "Missing", "Organization and Location are required.")
            return

        cfg = load_config()
        cfg.update({
            "organization_name": self.org.text().strip(),
            "location_name": self.loc.text().strip(),
            "region": self.region.text().strip(),
            "address": self.address.text().strip(),
            "country": self.country.text().strip(),
        })
        save_config(cfg)
        self.accept()


# ==============================================================
# MAIN WINDOW
# ==============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.db_manager = DatabaseManager()
        self.license_manager = LicenseManager(self.db_manager)

        # ------------------------
        # License Flow
        # ------------------------
        if not self._ensure_license():
            QMessageBox.critical(None, "License Error", "License missing or invalid.")
            sys.exit(1)

        self.init_ui()
        self.setup_auto_refresh()

    # ------------------------------------------------------
    # Startup License Logic
    # ------------------------------------------------------
    def _ensure_license(self) -> bool:
        info = self.db_manager.get_license_info()

        if info and info.get("license_key"):
            # Active?
            if info.get("is_active"):
                if self.license_manager.is_licensed():
                    # Require org setup if missing
                    cfg = load_config()
                    if not cfg.get("organization_name"):
                        WelcomeDialog(self).exec_()
                    return True
            else:
                # Not active → LOGIN popup (key only)
                dlg = LicenseDialog(self.license_manager, mode="login", parent=self)
                if dlg.exec_() == QDialog.Accepted:
                    cfg = load_config()
                    if not cfg.get("organization_name"):
                        WelcomeDialog(self).exec_()
                    return True
                return False

        # No license stored → Activation popup
        dlg = LicenseDialog(self.license_manager, mode="activate", parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return False

        # After activation → setup org details
        cfg = load_config()
        if not cfg.get("organization_name"):
            WelcomeDialog(self).exec_()

        return self.license_manager.is_licensed()

    # ------------------------------------------------------
    # Build UI
    # ------------------------------------------------------
    def init_ui(self):
        self.setWindowTitle("M-Neo VMS")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(MAIN_STYLE)

        # Icon
        ico = QIcon(str(APP_BASE / "assets" / "logo.ico"))
        if not ico.isNull():
            self.setWindowIcon(ico)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        about = QAction("About", self)
        about.triggered.connect(self._about)
        toolbar.addAction(about)

        logout = QAction("Log Out", self)
        logout.triggered.connect(self._logout)
        toolbar.addAction(logout)

        # Status bar
        cfg = load_config()
        org = cfg.get("organization_name", "—")
        loc = cfg.get("location_name", "—")
        self.org_label = QLabel(f"{org} — {loc}")
        self.statusBar().addPermanentWidget(self.org_label)
        self.statusBar().showMessage("Ready")

        # Tabs
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.dashboard_widget = DashboardWidget(self.db_manager)
        self.registration_widget = RegistrationWidget(self.db_manager)
        self.active_visitors_widget = ActiveVisitorsWidget(self.db_manager)
        self.history_widget = HistoryWidget(self.db_manager)
        self.all_records_widget = AllRecordsWidget(self.db_manager)

        self.tabs.addTab(self.dashboard_widget, "Dashboard")
        self.tabs.addTab(self.registration_widget, "Registration")
        self.tabs.addTab(self.active_visitors_widget, "Active Visitors")
        self.tabs.addTab(self.history_widget, "Today’s History")
        self.tabs.addTab(self.all_records_widget, "All Records")

        layout.addWidget(self.tabs)

    # ------------------------------------------------------
    # ABOUT
    # ------------------------------------------------------
    def _about(self):
        cfg = load_config()

        QMessageBox.information(
            self,
            "About",
            f"""
<b>M-Neo VMS</b><br>
Organization: {cfg.get('organization_name', '—')}<br>
Location: {cfg.get('location_name', '—')}<br>
Region: {cfg.get('region', '—')}<br>
Address: {cfg.get('address', '—')}<br>
Country: {cfg.get('country', '—')}<br>
"""
        )

    # ------------------------------------------------------
    # LOGOUT (sets is_active=0)
    # ------------------------------------------------------
    def _logout(self):
        reply = QMessageBox.question(
            self, "Log Out",
            "You will need to Log In with the license key next time.\nContinue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if not self.db_manager.set_license_active(False):
            QMessageBox.critical(self, "Error", "Could not deactivate license.")
            return

        QMessageBox.information(self, "Logged Out", "Next launch will ask for the license key.")
        self.close()

    # ------------------------------------------------------
    # Auto Refresh
    # ------------------------------------------------------
    def setup_auto_refresh(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh)
        self.refresh_timer.start(30000)

    def _refresh(self):
        try: self.dashboard_widget.refresh_data()
        except: pass
        try: self.active_visitors_widget.refresh_data()
        except: pass
        try: self.history_widget.refresh_data()
        except: pass
        try: self.all_records_widget.refresh_data()
        except: pass

    # ------------------------------------------------------
    # Exit dialog
    # ------------------------------------------------------
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Exit", "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
