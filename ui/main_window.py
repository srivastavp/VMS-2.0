# ui/main_window.py

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QLabel,
    QPushButton, QHBoxLayout, QToolBar, QAction, QApplication, QMenu, QMenuBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from pathlib import Path
import json
from datetime import datetime
import sys
import logging

# must import license manager early so ui.* imports don't circularly import license
from utils.license import LicenseManager
from database import DatabaseManager
from utils.styles import MAIN_STYLE

# Now import the UI widgets
from ui.registration import RegistrationWidget
from ui.dashboard import DashboardWidget
from ui.active_visitors import ActiveVisitorsWidget
from ui.history import HistoryWidget
from ui.all_records import AllRecordsWidget


# -------------------------
# small helpers for config
# -------------------------
APP_BASE = Path(__file__).resolve().parents[1]
DATA_DIR = APP_BASE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = DATA_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(data: dict):
    try:
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        logging.exception("Failed to save config")


# -------------------------
# Welcome dialog (org details)
# -------------------------
class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome — Organization Details")
        self.setModal(True)
        self.setFixedSize(520, 420)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)

        self.org_name = QLineEdit()
        self.location_name = QLineEdit()
        self.region = QLineEdit()
        self.address = QLineEdit()
        self.country = QLineEdit()

        cfg = load_config()
        self.org_name.setText(cfg.get("organization_name", ""))
        self.location_name.setText(cfg.get("location_name", ""))
        self.region.setText(cfg.get("region", ""))
        self.address.setText(cfg.get("address", ""))
        self.country.setText(cfg.get("country", ""))

        layout.addRow("Organization Name:", self.org_name)
        layout.addRow("Location Name:", self.location_name)
        layout.addRow("Region:", self.region)
        layout.addRow("Address:", self.address)
        layout.addRow("Country:", self.country)

        instructions = QLabel("Please enter basic site details. These appear in the app header and About.")
        instructions.setWordWrap(True)
        layout.addRow("", instructions)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addRow("", buttons)

    def _on_ok(self):
        if not self.org_name.text().strip() or not self.location_name.text().strip():
            QMessageBox.warning(self, "Missing fields", "Please provide Organization and Location names.")
            return

        cfg = load_config()
        cfg.update({
            "organization_name": self.org_name.text().strip(),
            "location_name": self.location_name.text().strip(),
            "region": self.region.text().strip(),
            "address": self.address.text().strip(),
            "country": self.country.text().strip()
        })
        save_config(cfg)
        self.accept()


# -------------------------
# License dialog (improved UI)
# -------------------------
class LicenseDialog(QDialog):
    def __init__(self, license_manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.setWindowTitle("License Activation")
        self.setModal(True)
        self.setFixedSize(520, 320)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout(self)

        device_info = self.license_manager.get_current_device_info()
        mac_label_text = device_info.get("mac_address", "UNKNOWN")

        info_label = QLabel("Device Information")
        info_label.setStyleSheet("font-weight: bold;")
        layout.addRow("", info_label)

        # MAC row with copy button
        mac_row = QHBoxLayout()
        self.mac_display = QLineEdit(mac_label_text)
        self.mac_display.setReadOnly(True)
        self.mac_display.setStyleSheet("font-family: monospace;")
        mac_row.addWidget(self.mac_display)

        copy_btn = QPushButton("Copy MAC")
        copy_btn.setToolTip("Copy MAC to clipboard")
        copy_btn.clicked.connect(self._copy_mac)
        mac_row.addWidget(copy_btn)
        layout.addRow("MAC Address:", mac_row)

        self.expiry_input = QLineEdit()
        self.expiry_input.setPlaceholderText("YYYY-MM-DD")

        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.license_input.setStyleSheet("font-family: monospace;")

        layout.addRow("Expiry Date:", self.expiry_input)
        layout.addRow("License Key:", self.license_input)

        instructions = QLabel(
            "Ask your vendor for the license key generated using this MAC.\n"
            "Enter expiry and key, then click Activate."
        )
        instructions.setWordWrap(True)
        layout.addRow("", instructions)

        btn_row = QHBoxLayout()
        activate_btn = QPushButton("Activate")
        cancel_btn = QPushButton("Cancel")

        activate_btn.clicked.connect(self._on_activate)
        cancel_btn.clicked.connect(self.reject)

        btn_row.addStretch()
        btn_row.addWidget(activate_btn)
        btn_row.addWidget(cancel_btn)
        layout.addRow("", btn_row)

    # ------------------------------------
    # FIXED: Proper clipboard usage
    # ------------------------------------
    def _copy_mac(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.mac_display.text())

        QMessageBox.information(
            self,
            "Copied",
            "MAC address copied to clipboard."
        )

    def _on_activate(self):
        key = self.license_input.text().strip()
        expiry = self.expiry_input.text().strip()

        if not key or not expiry:
            QMessageBox.warning(self, "Missing", "Please enter both fields.")
            return

        try:
            datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError:
            QMessageBox.warning(self, "Invalid Date", "Expiry must be YYYY-MM-DD.")
            return

        if not self.license_manager.validate_license(key, expiry):
            QMessageBox.warning(self, "Invalid", "License key does not match this device + expiry.")
            return

        if not self.license_manager.activate_license(key, expiry):
            QMessageBox.critical(self, "Error", "Could not save license.")
            return

        QMessageBox.information(self, "Activated", "License activated successfully.")
        self.accept()


# -------------------------
# Main application window
# -------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.license_manager = LicenseManager(self.db_manager)

        # License workflow
        if not self.check_license_and_maybe_activate():
            QMessageBox.critical(None, "License Error", "License missing or invalid.")
            sys.exit(1)

        # UI
        self.init_ui()
        self.setup_auto_refresh()

    # -------------------------
    # License flow
    # -------------------------
    def check_license_and_maybe_activate(self) -> bool:
        try:
            if self.license_manager.is_licensed():
                cfg = load_config()
                if not cfg.get("organization_name") or not cfg.get("location_name"):
                    self._show_welcome_dialog_if_missing()
                return True

            dlg = LicenseDialog(self.license_manager, self)
            if dlg.exec_() != QDialog.Accepted:
                return False

            self._show_welcome_dialog_if_missing()
            return self.license_manager.is_licensed()

        except Exception:
            logging.exception("License check error")
            return False

    def _show_welcome_dialog_if_missing(self):
        cfg = load_config()
        if cfg.get("organization_name") and cfg.get("location_name"):
            return

        wd = WelcomeDialog(self)
        wd.exec_()

    # -------------------------
    # UI
    # -------------------------
    def init_ui(self):
        self.setWindowTitle("M-Neo VMS")
        self.setGeometry(100, 100, 1200, 800)

        ico = QIcon(str(Path(__file__).resolve().parents[1] / "assets" / "logo.ico"))
        self.setWindowIcon(ico)

        self.setStyleSheet(MAIN_STYLE)

        # Toolbar
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        toolbar.addAction(about_action)

        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self._on_logout_clicked)
        toolbar.addAction(logout_action)

        # org label
        cfg = load_config()
        org = cfg.get("organization_name", "")
        loc = cfg.get("location_name", "")
        self.org_label = QLabel(f" {org} — {loc} ")
        self.statusBar().addPermanentWidget(self.org_label)
        self.statusBar().showMessage("M-Neo VMS — Ready")

        # Tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        self.dashboard_widget = DashboardWidget(self.db_manager)
        self.registration_widget = RegistrationWidget(self.db_manager)
        self.active_visitors_widget = ActiveVisitorsWidget(self.db_manager)
        self.history_widget = HistoryWidget(self.db_manager)
        self.all_records_widget = AllRecordsWidget(self.db_manager)

        self.tabs.addTab(self.dashboard_widget, "Dashboard")
        self.tabs.addTab(self.registration_widget, "Registration")
        self.tabs.addTab(self.active_visitors_widget, "Active Visitors")
        self.tabs.addTab(self.history_widget, "Today's History")
        self.tabs.addTab(self.all_records_widget, "All Records")

        layout.addWidget(self.tabs)

        # signals
        try:
            self.dashboard_widget.active_visitors_clicked.connect(self.show_active_visitors)
            self.registration_widget.visitor_registered.connect(self.refresh_all_widgets)
            self.active_visitors_widget.visitor_checked_out.connect(self.refresh_all_widgets)
        except Exception:
            pass

    def _show_about(self):
        cfg = load_config()
        text = (
            f"<b>M-Neo VMS</b><br>"
            f"Organization: {cfg.get('organization_name','—')}<br>"
            f"Location: {cfg.get('location_name','—')}<br>"
            f"Region: {cfg.get('region','—')}<br>"
            f"Address: {cfg.get('address','—')}<br>"
            f"Country: {cfg.get('country','—')}"
        )
        QMessageBox.information(self, "About", text)

    def _on_logout_clicked(self):
        reply = QMessageBox.question(
            self, "Logout",
            "You will be required to re-enter the license key next time. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.db_manager.save_license("", self.license_manager.get_device_mac())
        QMessageBox.information(self, "Logged out", "License cleared.")
        self.close()

    def show_active_visitors(self):
        self.tabs.setCurrentIndex(2)

    def refresh_all_widgets(self):
        try: self.dashboard_widget.refresh_data()
        except: pass
        try: self.active_visitors_widget.refresh_data()
        except: pass
        try: self.history_widget.refresh_data()
        except: pass
        try: self.all_records_widget.refresh_data()
        except: pass

    def setup_auto_refresh(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all_widgets)
        self.refresh_timer.start(30000)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Exit", "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
