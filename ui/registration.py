from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                            QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox,
                            QGroupBox, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime
from database import DatabaseManager
from utils.styles import BUTTON_STYLES, DASHBOARD_CARD_STYLE

class RegistrationWidget(QWidget):
    visitor_registered = pyqtSignal()
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Visitor Registration")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setStyleSheet("color: #2196F3; margin: 20px;")
        layout.addWidget(header_label)
        
        # Registration form in a card
        card_frame = QFrame()
        card_frame.setStyleSheet(DASHBOARD_CARD_STYLE)
        card_layout = QVBoxLayout(card_frame)
        
        # Form group
        form_group = QGroupBox("Visitor Information")
        form_layout = QFormLayout()
        
        # Form fields
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter visitor's full name")
        form_layout.addRow("Visitor Name*:", self.name_input)
        
        self.vehicle_input = QLineEdit()
        self.vehicle_input.setPlaceholderText("Enter vehicle number (optional)")
        form_layout.addRow("Vehicle Number:", self.vehicle_input)
        
        self.organization_input = QLineEdit()
        self.organization_input.setPlaceholderText("Enter organization name")
        form_layout.addRow("Organization:", self.organization_input)
        
        self.person_visited_input = QLineEdit()
        self.person_visited_input.setPlaceholderText("Enter name of person being visited")
        form_layout.addRow("Person Visited*:", self.person_visited_input)
        
        self.purpose_input = QTextEdit()
        self.purpose_input.setPlaceholderText("Enter purpose of visit")
        self.purpose_input.setMaximumHeight(80)
        form_layout.addRow("Purpose*:", self.purpose_input)
        
        form_group.setLayout(form_layout)
        card_layout.addWidget(form_group)
        
        # Timestamp display
        timestamp_group = QGroupBox("Check-in Information")
        timestamp_layout = QVBoxLayout()
        
        self.timestamp_label = QLabel()
        self.update_timestamp()
        timestamp_layout.addWidget(self.timestamp_label)
        
        timestamp_group.setLayout(timestamp_layout)
        card_layout.addWidget(timestamp_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.register_button = QPushButton("Register Visitor")
        self.register_button.setStyleSheet(BUTTON_STYLES['success'])
        self.register_button.clicked.connect(self.register_visitor)
        
        self.clear_button = QPushButton("Clear Form")
        self.clear_button.setStyleSheet(BUTTON_STYLES['warning'])
        self.clear_button.clicked.connect(self.clear_form)
        
        button_layout.addWidget(self.register_button)
        button_layout.addWidget(self.clear_button)
        
        card_layout.addLayout(button_layout)
        layout.addWidget(card_frame)
        
        # Add some stretch to center the form
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Set focus to first field
        self.name_input.setFocus()
    
    def update_timestamp(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.timestamp_label.setText(f"Check-in Time: {current_time}")
        self.timestamp_label.setStyleSheet("color: #666; font-size: 10pt;")
    
    def register_visitor(self):
        # Validate required fields
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Visitor name is required!")
            self.name_input.setFocus()
            return
        
        if not self.person_visited_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Person visited is required!")
            self.person_visited_input.setFocus()
            return
        
        if not self.purpose_input.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Purpose is required!")
            self.purpose_input.setFocus()
            return
        
        # Save to database
        success = self.db_manager.add_visitor(
            name=self.name_input.text().strip(),
            vehicle_number=self.vehicle_input.text().strip(),
            organization=self.organization_input.text().strip(),
            person_visited=self.person_visited_input.text().strip(),
            purpose=self.purpose_input.toPlainText().strip()
        )
        
        if success:
            QMessageBox.information(self, "Success", "Visitor registered successfully!")
            self.clear_form()
            self.visitor_registered.emit()
        else:
            QMessageBox.critical(self, "Error", "Failed to register visitor. Please try again.")
    
    def clear_form(self):
        self.name_input.clear()
        self.vehicle_input.clear()
        self.organization_input.clear()
        self.person_visited_input.clear()
        self.purpose_input.clear()
        self.update_timestamp()
        self.name_input.setFocus()