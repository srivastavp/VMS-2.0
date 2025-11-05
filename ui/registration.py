from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox,
    QGroupBox, QFrame, QComboBox, QStackedWidget, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime
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
        layout.setSpacing(24)
        layout.setContentsMargins(24, 24, 24, 24)

        header_label = QLabel("Visitor Registration")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setFont(QFont("Arial", 18, QFont.Bold))
        header_label.setStyleSheet(f"color: {PRIMARY_COLOR}; margin: 20px 0px;")
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
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

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
        two_column_layout.setSpacing(40)
        two_column_layout.setContentsMargins(0, 0, 0, 0)

        left_column = QFormLayout()
        right_column = QFormLayout()
        for c in (left_column, right_column):
            c.setSpacing(18)
            c.setContentsMargins(12, 12, 12, 12)
            c.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

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
            else:
                field = QLineEdit()
                field.setPlaceholderText(placeholder)
            field.setMinimumHeight(42)
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
        self.remarks_input.setMaximumHeight(120)
        self.remarks_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        left_column.addRow("NRIC*:", self.nric_input)
        left_column.addRow("HP No.*:", self.hp_no_input)
        left_column.addRow("First Name*:", self.first_name_input)
        left_column.addRow("Last Name*:", self.last_name_input)
        left_column.addRow("Category*:", self.category_input)
        left_column.addRow("Purpose*:", self.purpose_input)

        right_column.addRow("Destination*:", self.destination_input)
        right_column.addRow("Company:", self.company_input)
        right_column.addRow("Vehicle No.:", self.vehicle_input)
        right_column.addRow("Person Visited*:", self.person_visited_input)
        right_column.addRow("Remarks:", self.remarks_input)

        two_column_layout.addWidget(left_widget, 2)   # ✅ evenly stretches columns
        two_column_layout.addWidget(right_widget, 2)
        form_group.setLayout(two_column_layout)
        card_layout.addWidget(form_group)

        # --- BUTTONS ---
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)
        button_layout.setContentsMargins(0, 8, 0, 0)

        self.clear_button = QPushButton("Clear Form")
        self.clear_button.setStyleSheet(BUTTON_STYLES['warning'])
        self.clear_button.setFixedHeight(38)
        self.clear_button.setFixedWidth(140)
        self.clear_button.clicked.connect(self.clear_form)

        self.register_button = QPushButton("Check In / Register")
        self.register_button.setStyleSheet(BUTTON_STYLES['primary'])
        self.register_button.setFixedHeight(38)
        self.register_button.setFixedWidth(180)
        self.register_button.clicked.connect(self.register_visitor)

        button_layout.addStretch()
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.register_button)
        card_layout.addLayout(button_layout)

        self.pass_label = QLabel("Pass Number: (Will be generated upon registration)")
        self.pass_label.setStyleSheet("color: #666; font-size: 11pt; font-weight: bold; padding-top: 8px;")
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
                "Please enter the visitor's NRIC or HP No. to autofill their information."
            )
        self.nric_input.setFocus()

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
        print("Register button clicked - visitor registration not yet implemented")
