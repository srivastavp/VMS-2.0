from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QLabel
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from database import DatabaseManager
from utils.license import LicenseManager
from utils.styles import MAIN_STYLE
from ui.registration import RegistrationWidget
from ui.dashboard import DashboardWidget
from ui.active_visitors import ActiveVisitorsWidget
from ui.history import HistoryWidget
from ui.all_records import AllRecordsWidget
import sys
import logging


class LicenseDialog(QDialog):
    def __init__(self, license_manager: LicenseManager):
        super().__init__()
        self.license_manager = license_manager
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("License Activation")
        self.setFixedSize(400, 250)
        self.setModal(True)

        layout = QFormLayout()
        device_info = self.license_manager.get_current_device_info()

        info_label = QLabel("Device Information:")
        info_label.setStyleSheet("font-weight: bold; color: #441b48; margin-bottom: 10px;")
        layout.addRow("", info_label)

        mac_label = QLabel(f"MAC Address: {device_info['mac_address']}")
        mac_label.setStyleSheet("color: #666; font-size: 10pt; font-family: monospace;")
        layout.addRow("", mac_label)

        correct_key_label = QLabel(f"Correct Key: {device_info['license_key']}")
        correct_key_label.setStyleSheet("color: #4CAF50; font-size: 9pt; font-family: monospace;")
        layout.addRow("", correct_key_label)

        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("Enter license key (XXXX-XXXX-XXXX-XXXX)")
        self.license_input.setStyleSheet("font-family: monospace; font-size: 10pt;")
        layout.addRow("License Key:", self.license_input)

        instructions = QLabel("Enter the license key for this device to activate the application.")
        instructions.setStyleSheet("color: #666; font-size: 9pt; margin: 10px 0;")
        instructions.setWordWrap(True)
        layout.addRow("", instructions)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_activate_license)
        buttons.rejected.connect(self.reject)
        layout.addRow("", buttons)

        self.setLayout(layout)
        self.license_input.setFocus()

    def validate_and_activate_license(self):
        license_key = self.license_input.text().strip()
        if not license_key:
            QMessageBox.warning(self, "Empty License Key", "Please enter a license key!")
            return

        if self.license_manager.activate_license(license_key):
            QMessageBox.information(self, "Success", "License activated successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Invalid License",
                                "Invalid license key for this device!\nPlease try again.")
            self.license_input.selectAll()
            self.license_input.setFocus()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.db_manager = DatabaseManager()

        # ✅ IMPORTANT FIX: pass DB manager into LicenseManager
        self.license_manager = LicenseManager(self.db_manager)

        # License check
        if not self.check_license():
            logging.error("License validation failed, exiting application")
            sys.exit(1)

        self.init_ui()
        self.setup_auto_refresh()
    
    def check_license(self) -> bool:
        try:
            if self.license_manager.is_licensed():
                return True

            dialog = LicenseDialog(self.license_manager)
            return dialog.exec_() == QDialog.Accepted

        except Exception as e:
            logging.error(f"Error during license check: {e}")
            QMessageBox.critical(None, "License Error",
                                 f"An error occurred during license validation:\n{str(e)}")
            return False
    
    def init_ui(self):
        self.setWindowTitle("M-Neo VMS")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("assets/logo.ico"))
        self.setStyleSheet(MAIN_STYLE)

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

        self.dashboard_widget.active_visitors_clicked.connect(self.show_active_visitors)
        self.registration_widget.visitor_registered.connect(self.refresh_all_widgets)
        self.active_visitors_widget.visitor_checked_out.connect(self.refresh_all_widgets)

        self.statusBar().showMessage("M-Neon VMS - Ready - Licensed Application")
    
    def show_active_visitors(self):
        self.tabs.setCurrentIndex(2)

    def refresh_all_widgets(self):
        self.dashboard_widget.refresh_data()
        self.active_visitors_widget.refresh_data()
        self.history_widget.refresh_data()
        self.all_records_widget.refresh_data()

    def setup_auto_refresh(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all_widgets)
        self.refresh_timer.start(30000)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 'Confirm Exit', 'Are you sure you want to exit?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            logging.info("Application closing normally")
            event.accept()
        else:
            event.ignore()
