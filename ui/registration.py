from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox,
    QFrame, QComboBox, QStackedWidget, QDialog, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime
import logging, re, traceback

from database import DatabaseManager
from utils.styles import PRIMARY_COLOR


# ------------------------------------------------------
# Outer Tile + Card Styles
# ------------------------------------------------------
TILE_STYLE = """
QFrame#TileFrame {
    background: #f2f1f4;
    border-radius: 14px;
    border: 1px solid #e3e0e8;
}
"""

CARD_STYLE = """
QFrame#CardFrame {
    background: white;
    border-radius: 10px;
    border: 1px solid #dcd6dd;
}
"""

INPUT_STYLE = f"""
QLineEdit, QComboBox, QTextEdit {{
    background: white;
    border: 1px solid #dcd6dd;
    border-radius: 6px;
    padding: 8px;
    font-size: 11pt;
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {PRIMARY_COLOR};
}}
"""


# ------------------------------------------------------
# Visitor selection dialog
# ------------------------------------------------------
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

        self.list_area = QListWidget()
        for v in visitors:
            item = QListWidgetItem(
                f"{v.get('first_name','')} {v.get('last_name','')}  |  {v.get('nric')}  |  {v.get('hp_no')}"
            )
            item.setData(Qt.UserRole, v)
            self.list_area.addItem(item)
        layout.addWidget(self.list_area)

        btn_row = QHBoxLayout()
        select_btn = QPushButton("Select")
        cancel_btn = QPushButton("Cancel")
        btn_row.addStretch()
        btn_row.addWidget(select_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        select_btn.clicked.connect(self._select)
        cancel_btn.clicked.connect(self.reject)

    def _select(self):
        item = self.list_area.currentItem()
        if item:
            self.selected_visitor = item.data(Qt.UserRole)
            self.accept()


# ------------------------------------------------------
# Registration Widget
# ------------------------------------------------------
class RegistrationWidget(QWidget):
    visitor_registered = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.is_existing_visitor = False
        self._build_ui()

    # --------------------------------------------------
    def _make_label(self, text, required=True):
        if required:
            return QLabel(f"{text} <span style='color:red'>*</span>")
        return QLabel(text)

    def _make_input(self, placeholder="", combo=False, items=None):
        if combo:
            w = QComboBox()
            w.addItems(items or [])
        else:
            w = QLineEdit()
            w.setPlaceholderText(placeholder)
        w.setMinimumHeight(38)
        w.setStyleSheet(INPUT_STYLE)
        return w

    # --------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        tile = QFrame()
        tile.setObjectName("TileFrame")
        tile.setStyleSheet(TILE_STYLE)
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(30, 30, 30, 30)
        outer.addWidget(tile)

        header = QLabel("Visitor Registration")
        header.setFont(QFont("Segoe UI", 26, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f"color:{PRIMARY_COLOR}; margin-bottom: 20px;")
        tile_layout.addWidget(header)

        self.stacked = QStackedWidget()
        tile_layout.addWidget(self.stacked)

        self.stacked.addWidget(self._select_page())
        self.stacked.addWidget(self._form_page())

    # --------------------------------------------------
    def _select_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("CardFrame")
        card.setStyleSheet(CARD_STYLE)
        card.setMinimumWidth(480)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(50, 40, 50, 40)

        title = QLabel("Select Visitor Type")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color:{PRIMARY_COLOR}; margin-bottom:16px;")
        cl.addWidget(title)

        new_btn = QPushButton("New Visitor")
        existing_btn = QPushButton("Existing Visitor")
        new_btn.clicked.connect(lambda: self.show_form(False))
        existing_btn.clicked.connect(lambda: self.show_form(True))
        new_btn.setMinimumHeight(55)
        existing_btn.setMinimumHeight(55)

        cl.addWidget(new_btn)
        cl.addWidget(existing_btn)
        layout.addWidget(card)
        return page

    # --------------------------------------------------
    def _form_page(self):
        page = QWidget()
        p_layout = QVBoxLayout(page)

        back = QPushButton("← Back")
        back.clicked.connect(self.show_selection)
        back.setFixedWidth(120)
        p_layout.addWidget(back, alignment=Qt.AlignLeft)

        card = QFrame()
        card.setObjectName("CardFrame")
        card.setStyleSheet(CARD_STYLE)
        form_outer = QVBoxLayout(card)

        form = QHBoxLayout()
        left = QFormLayout()
        right = QFormLayout()

        # Core Fields
        self.nric = self._make_input("NRIC")
        self.search_btn = QPushButton("Search")
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
        self.person = self._make_input("Person To Visit")

        # NEW FIELD: Physical ID Number (optional)
        self.id_number = self._make_input("Physical ID Number (Optional)")

        self.category = self._make_input(combo=True, items=["Visitor", "Vendor", "Drop-off"])
        self.company = self._make_input("Company")
        self.vehicle = self._make_input("Vehicle No.")

        self.remarks = QTextEdit()
        self.remarks.setStyleSheet(INPUT_STYLE)

        self.nric_error = QLabel("")
        self.nric_error.setStyleSheet("color:red; font-size:9pt;")
        self.nric_error.hide()

        self.hp_error = QLabel("")
        self.hp_error.setStyleSheet("color:red; font-size:9pt;")
        self.hp_error.hide()

        left.addRow(self._make_label("NRIC:"), nric_row)
        left.addRow("", self.nric_error)
        left.addRow(self._make_label("HP No:"), self.hp)
        left.addRow("", self.hp_error)
        left.addRow(self._make_label("First Name:"), self.fn)
        left.addRow(self._make_label("Last Name:"), self.ln)
        left.addRow(self._make_label("Purpose:"), self.purpose)
        left.addRow(self._make_label("Destination:"), self.dest)
        left.addRow("ID Number:", self.id_number)

        right.addRow("Category:", self.category)
        right.addRow("Company:", self.company)
        right.addRow("Vehicle:", self.vehicle)
        right.addRow("Visit Person:", self.person)
        right.addRow("Remarks:", self.remarks)

        form.addLayout(left, 1)
        form.addLayout(right, 1)
        form_outer.addLayout(form)

        self.nric.textChanged.connect(self.validate_nric)
        self.hp.textChanged.connect(self.validate_hp)

        actions = QHBoxLayout()
        clear = QPushButton("Clear")
        register = QPushButton("Register / Check-In")
        clear.clicked.connect(self.clear_form)
        register.clicked.connect(self.register_visitor)

        actions.addStretch()
        actions.addWidget(clear)
        actions.addWidget(register)
        form_outer.addLayout(actions)

        p_layout.addWidget(card)
        return page

    # --------------------------------------------------
    def show_selection(self):
        self.stacked.setCurrentIndex(0)
        self.clear_form()

    def show_form(self, existing):
        self.is_existing_visitor = existing
        self.search_btn.setVisible(existing)
        self.stacked.setCurrentIndex(1)

    # --------------------------------------------------
    def search_existing(self):
        nric = self.nric.text().strip().upper()
        hp = self.hp.text().strip()

        if self.db_manager.has_active_visit(nric=nric, hp_no=hp):
            QMessageBox.warning(self,
                                "Visitor Already Inside",
                                "This visitor is still active and cannot be checked-in again.")
            return

        matches = self.db_manager.find_visitors_by_nric(nric=nric, hp_no=hp)
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
            self.purpose.setText(v.get("purpose", ""))
            self.dest.setText(v.get("destination", ""))
            self.person.setText(v.get("person_visited", ""))
            self.company.setText(v.get("company", ""))
            self.vehicle.setText(v.get("vehicle_number", ""))

    # --------------------------------------------------
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

    # --------------------------------------------------
    def clear_form(self):
        for f in [self.nric, self.hp, self.fn, self.ln,
                  self.purpose, self.dest, self.company,
                  self.vehicle, self.person, self.id_number]:
            f.clear()

        self.category.setCurrentIndex(0)
        self.remarks.clear()
        self.nric_error.hide()
        self.hp_error.hide()

    # --------------------------------------------------
    def register_visitor(self):
        if not self.validate_nric() or not self.validate_hp():
            return

        required = [
            (self.nric, "NRIC"),
            (self.hp, "HP No"),
            (self.fn, "First Name"),
            (self.ln, "Last Name"),
            (self.dest, "Destination"),
            (self.purpose, "Purpose")
        ]

        missing = [name for field, name in required if not field.text().strip()]
        if missing:
            QMessageBox.warning(self, "Missing Required Fields",
                                "Please fill:\n\n• " + "\n• ".join(missing))
            return

        try:
            visit_id = self.db_manager.generate_pass_number()

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
                pass_number=visit_id,
                id_number=self.id_number.text().strip() or None,
                remarks=self.remarks.toPlainText().strip(),
                person_visited=self.person.text().strip(),
                organization="",
                check_in_time=datetime.now(),
            )

            if not success:
                QMessageBox.warning(self, "Validation Failed",
                                    "NRIC must be S1234567D\nHP must be 8 digits.")
                return

            QMessageBox.information(
                self,
                "Success",
                f"Visitor registered successfully.\nVisit ID: {visit_id}"
            )
            self.visitor_registered.emit()
            self.show_selection()

        except Exception:
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", "Registration failed.")
