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
        self.setFixedSize(400, 250)
        self.setModal(True)
        
        layout = QFormLayout()
        
        # Device info display
        device_info = self.license_manager.get_current_device_info()
        
        info_label = QLabel("Device Information:")
        info_label.setStyleSheet("font-weight: bold; color: #2196F3; margin-bottom: 10px;")
        layout.addRow("", info_label)
        
        mac_label = QLabel(f"MAC Address: {device_info['mac_address']}")
        mac_label.setStyleSheet("color: #666; font-size: 10pt; font-family: monospace;")
        layout.addRow("", mac_label)
        
        # Show what the correct license key should be (for testing)
        correct_key_label = QLabel(f"Correct Key: {device_info['license_key']}")
        correct_key_label.setStyleSheet("color: #4CAF50; font-size: 9pt; font-family: monospace;")
        layout.addRow("", correct_key_label)
        
        # License key input
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("Enter license key (XXXX-XXXX-XXXX-XXXX)")
        self.license_input.setStyleSheet("font-family: monospace; font-size: 10pt;")
        layout.addRow("License Key:", self.license_input)
        
        # Instructions
        instructions = QLabel("Enter the license key for this device to activate the application.")
        instructions.setStyleSheet("color: #666; font-size: 9pt; margin: 10px 0;")
        instructions.setWordWrap(True)
        layout.addRow("", instructions)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_activate_license)
        buttons.rejected.connect(self.reject)
        layout.addRow("", buttons)
        
        self.setLayout(layout)
        
        # Set focus to input field
        self.license_input.setFocus()
    
    def validate_and_activate_license(self):
        """Validate and activate the entered license key"""
        license_key = self.license_input.text().strip()
        
        if not license_key:
            QMessageBox.warning(self, "Empty License Key", "Please enter a license key!")
            return
        
        # Use LicenseManager to handle all validation and activation
        if self.license_manager.activate_license(license_key):
            QMessageBox.information(self, "Success", "License activated successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Invalid License", 
                              "Invalid license key for this device!\n\n"
                              "Please check the license key and try again.")
            self.license_input.selectAll()
            self.license_input.setFocus()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.license_manager = LicenseManager()
        
        # Set database manager for license operations
        self.license_manager.set_db_manager(self.db_manager)
        
        # Check license before initializing UI
        if not self.check_license():
            logging.error("License validation failed, exiting application")
            sys.exit(1)
        
        self.init_ui()
        self.setup_auto_refresh()
    
    def check_license(self) -> bool:
        """Check if the application is licensed - simplified to use LicenseManager"""
        try:
            # Use LicenseManager's high-level method
            if self.license_manager.is_licensed():
                return True
            
            # Show license dialog if not licensed
            dialog = LicenseDialog(self.license_manager)
            return dialog.exec_() == QDialog.Accepted
            
        except Exception as e:
            logging.error(f"Error during license check: {e}")
            QMessageBox.critical(None, "License Error", 
                               f"An error occurred during license validation:\n{str(e)}")
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
        self.statusBar().showMessage("Ready - Licensed Application")
        
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
        
        # License menu (for testing)
        license_menu = menubar.addMenu('License')
        
        # Show license info
        license_info_action = QAction('License Information', self)
        license_info_action.triggered.connect(self.show_license_info)
        license_menu.addAction(license_info_action)
        
        # Revoke license (for testing)
        revoke_license_action = QAction('Revoke License (Testing)', self)
        revoke_license_action.triggered.connect(self.revoke_license_for_testing)
        license_menu.addAction(revoke_license_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        # About action
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def show_license_info(self):
        """Show current license information"""
        try:
            device_info = self.license_manager.get_current_device_info()
            license_info = self.db_manager.get_license_info()
            
            info_text = f"""
Current Device Information:
MAC Address: {device_info['mac_address']}
Expected License Key: {device_info['license_key']}

Stored License Information:
"""
            if license_info:
                info_text += f"""License Key: {license_info['license_key']}
Device MAC: {license_info['device_mac']}
Activation Date: {license_info['activation_date']}
Status: {'Active' if license_info['is_active'] else 'Inactive'}
Valid: {'Yes' if self.license_manager.is_licensed() else 'No'}"""
            else:
                info_text += "No license information stored."
            
            QMessageBox.information(self, "License Information", info_text)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error retrieving license info:\n{str(e)}")
    
    def revoke_license_for_testing(self):
        """Revoke current license for testing purposes"""
        reply = QMessageBox.question(self, 'Revoke License', 
                                   'This will revoke the current license and require re-activation.\n'
                                   'This is for testing purposes only.\n\n'
                                   'Are you sure you want to continue?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.license_manager.revoke_license():
                QMessageBox.information(self, "Success", 
                                      "License revoked successfully!\n"
                                      "The application will now exit. "
                                      "Restart to enter a new license.")
                self.close()
            else:
                QMessageBox.critical(self, "Error", "Failed to revoke license!")
    
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
                         "Built with PyQt5 and SQLite.\n\n"
                         "Licensed Application - Hardware Bound Security")
    
    def closeEvent(self, event):
        """Handle application close event"""
        reply = QMessageBox.question(self, 'Confirm Exit', 
                                   'Are you sure you want to exit?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            logging.info("Application closing normally")
            event.accept()
        else:
            event.ignore()