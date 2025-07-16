from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QVBoxLayout, QWidget,
                            QStatusBar, QMenuBar, QAction, QMessageBox, QDialog,
                            QDialogButtonBox, QFormLayout, QLineEdit, QLabel)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
from database import DatabaseManager
from utils.license import LicenseManager
from utils.styles import MAIN_STYLE, BUTTON_STYLES
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
        self.setFixedSize(400, 200)
        self.setModal(True)
        
        layout = QFormLayout()
        
        # MAC address display
        mac_address = self.license_manager.get_device_mac()
        mac_label = QLabel(f"Device MAC: {mac_address}")
        mac_label.setStyleSheet("color: #666; font-size: 10pt;")
        layout.addRow("", mac_label)
        
        # License key input
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("Enter license key (XXXX-XXXX-XXXX-XXXX)")
        layout.addRow("License Key:", self.license_input)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_license)
        buttons.rejected.connect(self.reject)
        layout.addRow("", buttons)
        
        self.setLayout(layout)
    
    def validate_license(self):
        license_key = self.license_input.text().strip()
        mac_address = self.license_manager.get_device_mac()
        
        if self.license_manager.validate_license(license_key, mac_address):
            self.accept()
        else:
            QMessageBox.warning(self, "Invalid License", "Invalid license key for this device!")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.license_manager = LicenseManager()
        
        # Check license before initializing UI
        if not self.check_license():
            sys.exit(1)
        
        self.init_ui()
        self.setup_auto_refresh()
    
    def check_license(self) -> bool:
        """Check if the application is licensed"""
        license_info = self.db_manager.get_license_info()
        current_mac = self.license_manager.get_device_mac()
        
        if license_info and self.license_manager.validate_license(
            license_info['license_key'], current_mac):
            return True
        
        # Show license dialog
        dialog = LicenseDialog(self.license_manager)
        if dialog.exec_() == QDialog.Accepted:
            license_key = dialog.license_input.text().strip()
            self.db_manager.save_license(license_key, current_mac)
            return True
        
        return False
    
    def init_ui(self):
        self.setWindowTitle("Visitor Management System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Apply main style
        self.setStyleSheet(MAIN_STYLE)
        
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create widgets
        self.dashboard_widget = DashboardWidget(self.db_manager)
        self.registration_widget = RegistrationWidget(self.db_manager)
        self.active_visitors_widget = ActiveVisitorsWidget(self.db_manager)
        self.history_widget = HistoryWidget(self.db_manager)
        self.all_records_widget = AllRecordsWidget(self.db_manager)
        
        # Add tabs
        self.tabs.addTab(self.dashboard_widget, "Dashboard")
        self.tabs.addTab(self.registration_widget, "Registration")
        self.tabs.addTab(self.active_visitors_widget, "Active Visitors")
        self.tabs.addTab(self.history_widget, "Today's History")
        self.tabs.addTab(self.all_records_widget, "All Records")
        
        layout.addWidget(self.tabs)
        
        # Connect signals
        self.dashboard_widget.active_visitors_clicked.connect(self.show_active_visitors)
        self.registration_widget.visitor_registered.connect(self.refresh_all_widgets)
        self.active_visitors_widget.visitor_checked_out.connect(self.refresh_all_widgets)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Menu bar
        self.create_menu_bar()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # Export action
        export_action = QAction('Export All Records', self)
        export_action.triggered.connect(self.export_all_records)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        # About action
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def show_active_visitors(self):
        """Navigate to active visitors tab"""
        self.tabs.setCurrentIndex(2)  # Active visitors tab
    
    def refresh_all_widgets(self):
        """Refresh all widgets with latest data"""
        self.dashboard_widget.refresh_data()
        self.active_visitors_widget.refresh_data()
        self.history_widget.refresh_data()
        self.all_records_widget.refresh_data()
    
    def setup_auto_refresh(self):
        """Setup automatic refresh timer"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all_widgets)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def export_all_records(self):
        """Export all records to Excel"""
        self.all_records_widget.export_to_excel()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", 
                         "Visitor Management System v1.0\n\n"
                         "A modern desktop application for managing visitor records.\n"
                         "Built with PyQt5 and SQLite.")
    
    def closeEvent(self, event):
        """Handle application close event"""
        reply = QMessageBox.question(self, 'Confirm Exit', 
                                   'Are you sure you want to exit?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()