from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox,
    QGroupBox, QFrame, QComboBox, QStackedWidget, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime
import logging
import traceback
from database import DatabaseManager
from utils.styles import BUTTON_STYLES, DASHBOARD_CARD_STYLE, PRIMARY_COLOR


class RegistrationWidget(QWidget):
    visitor_registered = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.is_existing_visitor = False
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        header_label = QLabel("Visitor Registration")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setFont(QFont("Arial", 20, QFont.Bold))
        header_label.setStyleSheet(f"color: {PRIMARY_COLOR}; margin: 10px 0px;")
        layout.addWidget(header_label)

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.selection_widget = self.create_selection_widget()
        self.form_widget = self.create_form_widget()
        self.stacked_widget.addWidget(self.selection_widget)
        self.stacked_widget.addWidget(self.form_widget)

        layout.addWidget(self.stacked_widget)
        layout.setStretchFactor(self.stacked_widget, 1)  # ✅ ensures it grows properly
        layout.addStretch()
        self.setLayout(layout)

    def create_selection_widget(self):
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setSpacing(30)
        layout.setContentsMargins(40, 40, 40, 40)

        card_frame = QFrame()
        card_frame.setStyleSheet(DASHBOARD_CARD_STYLE)
        card_frame.setMinimumWidth(400)
        card_frame.setMaximumWidth(500)
        card_layout = QVBoxLayout(card_frame)
        card_layout.setSpacing(30)
        card_layout.setContentsMargins(40, 40, 40, 40)

        title_label = QLabel("Select Visitor Type")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet(f"color: {PRIMARY_COLOR}; margin-bottom: 20px;")
        card_layout.addWidget(title_label)

        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)

        new_visitor_btn = QPushButton("New Visitor")
        new_visitor_btn.setStyleSheet(BUTTON_STYLES['primary'])
        new_visitor_btn.setMinimumHeight(45)
        new_visitor_btn.clicked.connect(lambda: self.show_form(is_existing=False))
        button_layout.addWidget(new_visitor_btn)

        existing_visitor_btn = QPushButton("Existing Visitor")
        existing_visitor_btn.setStyleSheet(BUTTON_STYLES['success'])
        existing_visitor_btn.setMinimumHeight(45)
        existing_visitor_btn.clicked.connect(lambda: self.show_form(is_existing=True))
        button_layout.addWidget(existing_visitor_btn)

        card_layout.addLayout(button_layout)
        layout.addWidget(card_frame, alignment=Qt.AlignCenter)
        widget.setLayout(layout)
        return widget

    def create_form_widget(self):
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 12, 20, 12)

        back_button = QPushButton("← Back to Selection")
        back_button.setStyleSheet(BUTTON_STYLES['warning'])
        back_button.setFixedHeight(36)
        back_button.setMaximumWidth(220)
        back_button.clicked.connect(self.show_selection)
        layout.addWidget(back_button)

        # --- MAIN CARD ---
        card_frame = QFrame()
        card_frame.setStyleSheet(DASHBOARD_CARD_STYLE)
        card_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card_frame)
        card_layout.setSpacing(24)
        card_layout.setContentsMargins(32, 32, 32, 32)

        form_group = QGroupBox("Visitor Information")
        form_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                margin-top: 15px;
                padding-top: 20px;
            }
        """)
        form_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- FORM LAYOUT ---
        two_column_layout = QHBoxLayout()
        two_column_layout.setSpacing(32)
        two_column_layout.setContentsMargins(0, 0, 0, 0)

        left_column = QFormLayout()
        right_column = QFormLayout()
        for c in (left_column, right_column):
            c.setSpacing(14)
            c.setContentsMargins(8, 8, 8, 8)
            c.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            c.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        left_widget = QWidget()
        left_widget.setLayout(left_column)
        left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right_widget = QWidget()
        right_widget.setLayout(right_column)
        right_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        def create_input(placeholder="", combo=False, items=None):
            if combo:
                field = QComboBox()
                field.addItems(items or [])
                field.setStyleSheet("font-size: 11pt; padding: 8px;")
            else:
                field = QLineEdit()
                field.setPlaceholderText(placeholder)
                field.setStyleSheet("font-size: 11pt; padding: 8px;")
            field.setMinimumHeight(48)
            field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            return field

        self.nric_input = create_input("Enter NRIC (Required)")
        self.hp_no_input = create_input("Enter phone number (Required)")
        self.first_name_input = create_input("Enter first name")
        self.last_name_input = create_input("Enter last name")
        self.category_input = create_input(combo=True, items=["Visitor", "Vendor", "Drop-off"])
        self.purpose_input = create_input("Enter purpose of visit")
        self.destination_input = create_input("Enter destination/location")
        self.company_input = create_input("Enter company name (optional)")
        self.vehicle_input = create_input("Enter vehicle number (optional)")
        self.person_visited_input = create_input("Enter name of person being visited")

        self.remarks_input = QTextEdit()
        self.remarks_input.setPlaceholderText("Enter any additional remarks (optional)")
        self.remarks_input.setMaximumHeight(100)
        self.remarks_input.setStyleSheet("font-size: 11pt; padding: 8px;")
        self.remarks_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Connect NRIC and HP No fields for existing visitor lookup
        self.nric_input.editingFinished.connect(self.lookup_existing_visitor)
        self.hp_no_input.editingFinished.connect(self.lookup_existing_visitor)

        # Create labels with larger font
        def create_label(text):
            label = QLabel(text)
            label.setStyleSheet("font-size: 11pt; font-weight: bold;")
            return label
        
        left_column.addRow(create_label("NRIC*:"), self.nric_input)
        left_column.addRow(create_label("HP No.*:"), self.hp_no_input)
        left_column.addRow(create_label("First Name*:"), self.first_name_input)
        left_column.addRow(create_label("Last Name*:"), self.last_name_input)
        left_column.addRow(create_label("Category*:"), self.category_input)
        left_column.addRow(create_label("Purpose*:"), self.purpose_input)

        right_column.addRow(create_label("Destination*:"), self.destination_input)
        right_column.addRow(create_label("Company:"), self.company_input)
        right_column.addRow(create_label("Vehicle No.:"), self.vehicle_input)
        right_column.addRow(create_label("Person Visited*:"), self.person_visited_input)
        right_column.addRow(create_label("Remarks:"), self.remarks_input)

        two_column_layout.addWidget(left_widget, 2)   # ✅ evenly stretches columns
        two_column_layout.addWidget(right_widget, 2)
        form_group.setLayout(two_column_layout)
        card_layout.addWidget(form_group)

        # --- BUTTONS ---
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)
        button_layout.setContentsMargins(0, 12, 0, 0)

        self.clear_button = QPushButton("Clear Form")
        self.clear_button.setStyleSheet(BUTTON_STYLES['warning'])
        self.clear_button.setMinimumSize(140, 45)
        self.clear_button.clicked.connect(self.clear_form)

        self.register_button = QPushButton("Check In / Register")
        self.register_button.setStyleSheet(BUTTON_STYLES['primary'])
        self.register_button.setMinimumSize(180, 45)
        self.register_button.clicked.connect(self.register_visitor)

        button_layout.addStretch()
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.register_button)
        card_layout.addLayout(button_layout)

        self.pass_label = QLabel("Pass Number: (Will be generated upon registration)")
        self.pass_label.setStyleSheet("color: #666; font-size: 12pt; font-weight: bold; padding-top: 8px;")
        card_layout.addWidget(self.pass_label)

        # ✅ Add scroll area to prevent cutoff
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card_frame)

        layout.addWidget(scroll, 1)
        widget.setLayout(layout)
        return widget

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for child in self.findChildren(QWidget):
            child.updateGeometry()
        self.updateGeometry()

    def show_selection(self):
        self.stacked_widget.setCurrentIndex(0)
        self.clear_form()

    def show_form(self, is_existing: bool = False):
        self.is_existing_visitor = is_existing
        self.stacked_widget.setCurrentIndex(1)
        if is_existing:
            QMessageBox.information(
                self, "Existing Visitor",
                "Please enter the visitor's First Name + Last Name (or NRIC/HP No.) to autofill their information.\n\nPurpose and Destination must be entered fresh for each visit."
            )
        self.nric_input.setFocus()
    
    def lookup_existing_visitor(self):
        """Lookup existing visitor by First Name + Last Name, NRIC, or HP No and prefill form"""
        if not self.is_existing_visitor:
            return
        
        try:
            first_name = self.first_name_input.text().strip()
            last_name = self.last_name_input.text().strip()
            nric = self.nric_input.text().strip()
            hp_no = self.hp_no_input.text().strip()
            
            # Priority: First Name + Last Name, then NRIC, then HP No
            if not (first_name and last_name) and not nric and not hp_no:
                return
            
            visitor = None
            
            # Try name-based lookup first
            if first_name and last_name:
                visitor = self.db_manager.find_existing_visitor_by_name(first_name, last_name)
            
            # Fallback to NRIC/HP lookup
            if not visitor and (nric or hp_no):
                visitor = self.db_manager.find_existing_visitor(nric=nric if nric else None, hp_no=hp_no if hp_no else None)
            
            if visitor:
                # Prefill known fields
                if visitor.get('nric'):
                    self.nric_input.setText(visitor['nric'])
                if visitor.get('hp_no'):
                    self.hp_no_input.setText(visitor['hp_no'])
                if visitor.get('first_name'):
                    self.first_name_input.setText(visitor['first_name'])
                if visitor.get('last_name'):
                    self.last_name_input.setText(visitor['last_name'])
                if visitor.get('category'):
                    index = self.category_input.findText(visitor['category'])
                    if index >= 0:
                        self.category_input.setCurrentIndex(index)
                if visitor.get('company'):
                    self.company_input.setText(visitor['company'])
                if visitor.get('vehicle_number'):
                    self.vehicle_input.setText(visitor['vehicle_number'])
                
                # Clear purpose and destination (must be fresh each visit)
                self.purpose_input.clear()
                self.destination_input.clear()
                self.person_visited_input.clear()
                
                QMessageBox.information(self, "Visitor Found", "Existing visitor information loaded.\n\nPlease enter Purpose, Destination, and Person Visited for this visit.")
            elif first_name or last_name or nric or hp_no:
                # Only show if user actually entered something
                QMessageBox.warning(self, "Not Found", "No matching visitor found.\n\nPlease fill in all details.")
        except Exception as e:
            logging.error(f"Error looking up existing visitor: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", "Failed to lookup existing visitor. Please try again.")

    def clear_form(self):
        for field in [
            self.nric_input, self.hp_no_input, self.first_name_input,
            self.last_name_input, self.purpose_input, self.destination_input,
            self.company_input, self.vehicle_input, self.person_visited_input
        ]:
            field.clear()
        self.category_input.setCurrentIndex(0)
        self.remarks_input.clear()
        self.pass_label.setText("Pass Number: (Will be generated upon registration)")
        self.pass_label.setStyleSheet("color: #666; font-size: 11pt; font-weight: bold; padding-top: 8px;")

    def register_visitor(self):
        """Register visitor with full validation, error handling, and auto-redirect"""
        # Validate required fields
        missing = []
        if not self.nric_input.text().strip(): missing.append("NRIC")
        if not self.hp_no_input.text().strip(): missing.append("HP No.")
        if not self.first_name_input.text().strip(): missing.append("First name")
        if not self.last_name_input.text().strip(): missing.append("Last name")
        if not self.purpose_input.text().strip(): missing.append("Purpose")
        if not self.destination_input.text().strip(): missing.append("Destination")
        if not self.person_visited_input.text().strip(): missing.append("Person visited")
        
        if missing:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Validation Error")
            msg.setText("Please fill all required fields:")
            msg.setInformativeText("\n".join([f"• {field}" for field in missing]))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            
            # Focus first missing field
            first = missing[0]
            mapping = {
                "NRIC": self.nric_input, 
                "HP No.": self.hp_no_input,
                "First name": self.first_name_input, 
                "Last name": self.last_name_input,
                "Purpose": self.purpose_input, 
                "Destination": self.destination_input,
                "Person visited": self.person_visited_input
            }
            mapping[first].setFocus()
            return

        # Disable button to prevent double click
        self.register_button.setEnabled(False)
        try:
            pass_number = self.db_manager.generate_pass_number()
            check_in_time = datetime.now()
            
            logging.info(f"Registering visitor: {self.first_name_input.text()} {self.last_name_input.text()} - Pass: {pass_number}")
            
            success = self.db_manager.add_visitor(
                nric=self.nric_input.text().strip(),
                hp_no=self.hp_no_input.text().strip(),
                first_name=self.first_name_input.text().strip(),
                last_name=self.last_name_input.text().strip(),
                category=self.category_input.currentText(),
                purpose=self.purpose_input.text().strip(),
                destination=self.destination_input.text().strip(),
                company=self.company_input.text().strip(),
                vehicle_number=self.vehicle_input.text().strip(),
                pass_number=pass_number,
                remarks=self.remarks_input.toPlainText().strip(),
                person_visited=self.person_visited_input.text().strip(),
                check_in_time=check_in_time
            )
            
            if success:
                logging.info(f"Visitor registered successfully: {pass_number}")
                
                # Show success message
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("Success")
                msg.setText("✓ Visitor registered successfully!")
                msg.setInformativeText(f"Pass Number: {pass_number}\nCheck-in Time: {check_in_time.strftime('%Y-%m-%d %H:%M:%S')}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                
                # Emit signal for dashboard refresh
                self.visitor_registered.emit()
                
                # Auto-redirect to selection page
                self.clear_form()
                self.show_selection()
            else:
                logging.error("Failed to register visitor - DB returned False")
                QMessageBox.critical(self, "Error", "Failed to register visitor. Please try again.")
        except Exception as e:
            logging.error(f"Error registering visitor: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"An error occurred while registering the visitor:\n{str(e)}")
        finally:
            # Small debounce: re-enable after short delay
            QTimer.singleShot(500, lambda: self.register_button.setEnabled(True))
