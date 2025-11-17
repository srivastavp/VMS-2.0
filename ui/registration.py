from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox,
    QFrame, QComboBox, QStackedWidget, QDialog, QListWidget, QListWidgetItem,
    QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime
import logging, re, traceback

from database import DatabaseManager
from utils.styles import PRIMARY_COLOR

BG_COLOR = "#f5f5f7"
TEXT_MUTED = "#555"
BORDER = "#dcd6dd"

CARD_STYLE = f"""
QFrame.card {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
"""

INPUT_STYLE = f"""
QLineEdit, QComboBox, QTextEdit {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px;
    font-size: 11pt;
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {PRIMARY_COLOR};
}}
"""

BUTTON_PRIMARY = f"""
QPushButton {{
    background: {PRIMARY_COLOR};
    color: white;
    padding: 10px 18px;
    border-radius: 6px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: #6d4f70;
}}
"""

BUTTON_SECONDARY = f"""
QPushButton {{
    background: white;
    color: {TEXT_MUTED};
    padding: 10px 14px;
    border-radius: 6px;
    border: 1px solid {BORDER};
}}
QPushButton:hover {{
    background: #faf9fa;
}}
"""


# Visitor selection dialog
class VisitorSelectionDialog(QDialog):
    def __init__(self, visitors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Visitor")
        self.setModal(True)
        self.selected_visitor = None
        self.setMinimumSize(600, 350)

        layout = QVBoxLayout(self)

        title = QLabel("Select Previously Registered Visitor")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color:{PRIMARY_COLOR}; margin-bottom:6px;")
        layout.addWidget(title)

        list_area = QListWidget()
        for v in visitors:
            item = QListWidgetItem(f"{v.get('first_name','')} {v.get('last_name','')}  |  {v.get('nric')}  |  {v.get('hp_no')}")
            item.setData(Qt.UserRole, v)
            list_area.addItem(item)
        layout.addWidget(list_area)

        btn_row = QHBoxLayout()
        select_btn = QPushButton("Select")
        select_btn.setStyleSheet(BUTTON_PRIMARY)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(BUTTON_SECONDARY)

        btn_row.addStretch()
        btn_row.addWidget(select_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        select_btn.clicked.connect(lambda: self._select(list_area))
        cancel_btn.clicked.connect(self.reject)

    def _select(self, list_area):
        item = list_area.currentItem()
        if item:
            self.selected_visitor = item.data(Qt.UserRole)
            self.accept()


class RegistrationWidget(QWidget):
    visitor_registered = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.is_existing_visitor = False
        self.setStyleSheet(f"background: {BG_COLOR};")
        self._build_ui()

    def _make_label(self, text):
        label = QLabel(f"{text} <span style='color:red'>*</span>")
        label.setStyleSheet("font-weight: 500;")
        return label

    def _make_input(self, placeholder="", combo=False, items=None):
        if combo:
            w = QComboBox()
            w.addItems(items or [])
        else:
            w = QLineEdit()
            w.setPlaceholderText(placeholder)

        w.setMinimumHeight(40)
        w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # FIX: Prevent UI compression
        w.setStyleSheet(INPUT_STYLE)
        return w

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Visitor Registration")
        header.setFont(QFont("Segoe UI", 32, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f"color:{PRIMARY_COLOR}; margin-bottom: 30px;")
        main.addWidget(header)

        self.stacked = QStackedWidget()
        main.addWidget(self.stacked, 1)

        self.stacked.addWidget(self._select_page())
        self.stacked.addWidget(self._form_page())

    def _select_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(CARD_STYLE)
        card.setMinimumWidth(550)
        card.setMinimumHeight(260)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(60, 50, 60, 50)

        title = QLabel("Select Visitor Type")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color:{PRIMARY_COLOR}; margin-bottom: 22px;")
        cl.addWidget(title)

        new_btn = QPushButton("New Visitor")
        new_btn.setStyleSheet(BUTTON_PRIMARY)
        new_btn.setFixedHeight(60)
        new_btn.clicked.connect(lambda: self.show_form(False))

        existing_btn = QPushButton("Existing Visitor")
        existing_btn.setStyleSheet(BUTTON_SECONDARY)
        existing_btn.setFixedHeight(60)
        existing_btn.clicked.connect(lambda: self.show_form(True))

        cl.addWidget(new_btn)
        cl.addWidget(existing_btn)
        layout.addWidget(card)

        return page

    def _form_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        back = QPushButton("← Back")
        back.setStyleSheet(BUTTON_SECONDARY)
        back.clicked.connect(self.show_selection)
        layout.addWidget(back, alignment=Qt.AlignLeft)

        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(CARD_STYLE)
        card_layout = QVBoxLayout(card)

        form = QHBoxLayout()
        left = QFormLayout()
        right = QFormLayout()

        self.nric = self._make_input("NRIC")
        self.search_btn = QPushButton("Search")
        self.search_btn.setStyleSheet(BUTTON_PRIMARY)
        self.search_btn.setMinimumHeight(40)
        self.search_btn.clicked.connect(self.search_existing)
        self.search_btn.hide()

        nric_row = QHBoxLayout()
        nric_row.addWidget(self.nric)
        nric_row.addWidget(self.search_btn)

        self.hp = self._make_input("HP No.")
        self.fn = self._make_input("First Name")
        self.ln = self._make_input("Last Name")
        self.purpose = self._make_input("Purpose")
        self.dest = self._make_input("Destination")
        self.category = self._make_input(combo=True, items=["Visitor", "Vendor", "Drop-off"])
        self.company = self._make_input("Company")
        self.vehicle = self._make_input("Vehicle No.")
        self.person = self._make_input("Person To Visit")
        self.remarks = QTextEdit()
        self.remarks.setStyleSheet(INPUT_STYLE)

        self.nric_error = QLabel("")
        self.nric_error.setStyleSheet("color: red; font-size: 9pt;")
        self.nric_error.setMinimumHeight(18)  # Prevent layout shifting
        self.nric_error.hide()

        self.hp_error = QLabel("")
        self.hp_error.setStyleSheet("color: red; font-size: 9pt;")
        self.hp_error.setMinimumHeight(18)
        self.hp_error.hide()

        left.addRow(self._make_label("NRIC"), nric_row)
        left.addRow("", self.nric_error)
        left.addRow(self._make_label("HP No"), self.hp)
        left.addRow("", self.hp_error)
        left.addRow(self._make_label("First Name"), self.fn)
        left.addRow(self._make_label("Last Name"), self.ln)
        left.addRow("Category:", self.category)
        left.addRow(self._make_label("Purpose"), self.purpose)

        right.addRow(self._make_label("Destination"), self.dest)
        right.addRow("Company:", self.company)
        right.addRow("Vehicle:", self.vehicle)
        right.addRow("Visit Person:", self.person)
        right.addRow("Remarks:", self.remarks)

        form.addLayout(left, 1)
        form.addLayout(right, 1)
        card_layout.addLayout(form)

        self.nric.textChanged.connect(self.validate_nric)
        self.hp.textChanged.connect(self.validate_hp)

        actions = QHBoxLayout()
        clear = QPushButton("Clear")
        clear.setStyleSheet(BUTTON_SECONDARY)
        clear.clicked.connect(self.clear_form)

        register = QPushButton("Register / Check-In")
        register.setStyleSheet(BUTTON_PRIMARY)
        register.clicked.connect(self.register_visitor)

        actions.addStretch()
        actions.addWidget(clear)
        actions.addWidget(register)
        card_layout.addLayout(actions)

        layout.addWidget(card)
        return page

    def show_selection(self):
        self.stacked.setCurrentIndex(0)
        self.clear_form()

    def show_form(self, existing):
        self.is_existing_visitor = existing
        self.search_btn.setVisible(existing)
        self.stacked.setCurrentIndex(1)

    def search_existing(self):
        matches = self.db_manager.find_visitors_by_nric(
            nric=self.nric.text().strip(), hp_no=self.hp.text().strip()
        )

        if not matches:
            QMessageBox.information(self, "Not Found", "No matching visitor found.")
            return

        dialog = VisitorSelectionDialog(matches, self)
        if dialog.exec_():
            v = dialog.selected_visitor
            self.nric.setText(v.get("nric", ""))
            self.hp.setText(v.get("hp_no", ""))
            self.fn.setText(v.get("first_name", ""))
            self.ln.setText(v.get("last_name", ""))
            self.company.setText(v.get("company", ""))
            self.vehicle.setText(v.get("vehicle_number", ""))

    def validate_nric(self):
        text = self.nric.text().strip().upper()
        valid = bool(re.match(r"^[STFG][0-9]{7}[A-Z]$", text))
        self.nric_error.setVisible(not valid)
        self.nric_error.setText("Invalid NRIC format (Example: S1234567D)")
        return valid

    def validate_hp(self):
        text = self.hp.text().strip()
        valid = text.isdigit() and len(text) == 8
        self.hp_error.setVisible(not valid)
        self.hp_error.setText("HP No. must be 8 digits")
        return valid

    def clear_form(self):
        for f in [self.nric, self.hp, self.fn, self.ln, self.purpose,
                  self.dest, self.company, self.vehicle, self.person]:
            f.clear()
        self.category.setCurrentIndex(0)
        self.remarks.clear()
        self.nric_error.hide()
        self.hp_error.hide()

    def register_visitor(self):
        if not self.validate_nric() or not self.validate_hp():
            return

        required_fields = [
            (self.nric, "NRIC"),
            (self.hp, "HP No"),
            (self.fn, "First Name"),
            (self.ln, "Last Name"),
            (self.dest, "Destination"),
            (self.purpose, "Purpose")
        ]

        missing = [name for field, name in required_fields if not field.text().strip()]
        if missing:
            QMessageBox.warning(self, "Missing Required Fields",
                                "Please fill the following required fields:\n\n• " + "\n• ".join(missing))
            return

        try:
            pass_no = self.db_manager.generate_pass_number()
            success = self.db_manager.add_visitor(
                nric=self.nric.text().strip().upper(),
                hp_no=self.hp.text().strip(),
                first_name=self.fn.text().strip(),
                last_name=self.ln.text().strip(),
                category=self.category.currentText(),
                purpose=self.purpose.text().strip(),
                destination=self.dest.text().strip(),
                company=self.company.text().strip(),
                vehicle_number=self.vehicle.text().strip(),
                pass_number=pass_no,
                remarks=self.remarks.toPlainText().strip(),
                person_visited=self.person.text().strip(),
                organization="",
                check_in_time=datetime.now(),
            )

            if not success:
                QMessageBox.warning(self, "Validation Failed",
                                    "NRIC format must be S1234567D\nHP must be 8 digits.")
                return

            QMessageBox.information(self, "Success", f"Visitor registered.\nPass: {pass_no}")
            self.visitor_registered.emit()
            self.show_selection()

        except Exception:
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", "Registration failed.")
