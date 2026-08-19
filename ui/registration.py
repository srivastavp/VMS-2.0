from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox,
    QFrame, QComboBox, QStackedWidget, QDialog, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from datetime import datetime
import logging, re, traceback
import io
import json
import os
from pathlib import Path

import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

from database import DatabaseManager
from utils.styles import PRIMARY_COLOR


# ------------------------------------------------------
# Config Helper
# ------------------------------------------------------
def load_config() -> dict:
    """Load configuration from data/config.json"""
    app_base = Path(__file__).resolve().parents[1]
    config_path = app_base / "data" / "config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def get_desktop_dir() -> Path:
    """Best-effort resolution of the current user's Desktop directory."""
    desktop = Path.home() / "Desktop"
    try:
        desktop.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return desktop


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
    def generate_visitor_pass_pdf(self, visit_id: str, check_in_time: datetime) -> str:
        """
        Generate an ID-card-style PDF pass with a QR code for a visitor and
        save it to the current user's Desktop. Card size matches the
        standard CR80 ID card (3.375 x 2.125 in), suitable for small
        sticker/badge printers.
        """
        first_name = self.fn.text().strip()
        last_name = self.ln.text().strip()
        full_name = f"{first_name} {last_name}".strip()
        hp_no = self.hp.text().strip()
        category = self.category.currentText()
        destination = self.dest.text().strip()

        cfg = load_config()
        org_name = cfg.get("organization_name", "")
        location = cfg.get("location_name", "")

        # QR payload (JSON)
        payload_dict = {
            "type": "VMS_PASS",
            "visit_id": visit_id,
            "hp_no": hp_no,
            "name": full_name,
            "category": category,
            "destination": destination,
            "in_time": check_in_time.isoformat(),
            "organization": org_name,
            "location": location,
            "application": "M-Neo VMS"
        }

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=3,
        )
        qr.add_data(json.dumps(payload_dict))
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        desktop_dir = get_desktop_dir()
        pdf_path = os.path.join(str(desktop_dir), f"VisitorPass_{visit_id}.pdf")

        # CR80 ID card size in points (3.375 x 2.125 in)
        card_width = 3.375 * 72   # 243 pts
        card_height = 2.125 * 72  # 153 pts

        c = canvas.Canvas(pdf_path, pagesize=(card_width, card_height))

        # Border
        primary_rgb = tuple(int(PRIMARY_COLOR[i:i + 2], 16) for i in (1, 3, 5))
        primary_color_norm = tuple(x / 255.0 for x in primary_rgb)
        c.setStrokeColor(primary_color_norm)
        c.setLineWidth(1.5)
        c.rect(2, 2, card_width - 4, card_height - 4, stroke=1, fill=0)

        # -------- QR at top-right --------
        qr_size = 48
        margin = 6
        qr_x = card_width - margin - qr_size
        qr_y = card_height - margin - qr_size
        qr_img_pil = Image.open(qr_buffer)
        c.drawImage(ImageReader(qr_img_pil), qr_x, qr_y, width=qr_size, height=qr_size)

        # -------- Header (org name) --------
        c.setFont("Helvetica-Bold", 7)
        c.setFillColorRGB(*primary_color_norm)
        c.drawString(margin, card_height - margin - 7, (org_name or "M-Neo VMS")[:26])

        # -------- Fields (left column, below header, avoiding QR) --------
        fields = [
            ("Name", full_name or "-"),
            ("HP No.", hp_no or "-"),
            ("Category", category or "-"),
            ("Destination", destination or "-"),
            ("Visit ID", visit_id),
            ("In-Time", check_in_time.strftime("%Y-%m-%d %H:%M")),
        ]

        c.setFont("Helvetica", 6)
        c.setFillColorRGB(0, 0, 0)
        text_width_limit = card_width - margin - 4
        y = card_height - margin - 18
        line_gap = 12
        for label, value in fields:
            text = f"{label}: {value}"
            # Simple truncation so text doesn't overflow the card
            while c.stringWidth(text, "Helvetica", 6) > text_width_limit and len(value) > 3:
                value = value[:-1]
                text = f"{label}: {value}..."
            c.drawString(margin, y, text)
            y -= line_gap
            if y < margin:
                break

        # -------- Footer (location / M-Neo VMS) --------
        c.setFont("Helvetica", 5)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        footer_text = " | ".join(t for t in [location, "M-Neo VMS"] if t)
        c.drawString(margin, margin, footer_text[:40])

        c.save()
        return pdf_path

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
            check_in_time = datetime.now()

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
                check_in_time=check_in_time,
            )

            if not success:
                QMessageBox.warning(self, "Validation Failed",
                                    "NRIC must be S1234567D\nHP must be 8 digits.")
                return

            pass_msg = ""
            try:
                pdf_path = self.generate_visitor_pass_pdf(visit_id, check_in_time)
                pass_msg = f"\n\nVisitor pass saved to:\n{pdf_path}"
            except Exception:
                logging.error(f"Failed to generate visitor pass PDF: {traceback.format_exc()}")
                pass_msg = "\n\n(Visitor pass PDF could not be generated.)"

            QMessageBox.information(
                self,
                "Success",
                f"Visitor registered successfully.\nVisit ID: {visit_id}{pass_msg}"
            )
            self.visitor_registered.emit()
            self.show_selection()

        except Exception:
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", "Registration failed.")
