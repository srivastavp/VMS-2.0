from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox,
    QFrame, QComboBox, QStackedWidget, QDialog, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRegularExpression
from PyQt5.QtGui import QFont, QRegularExpressionValidator
from datetime import datetime
import logging, traceback
import os
import io
import json
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
        title.setStyleSheet(f"color:{PRIMARY_COLOR}; margin-bottom:10px;")
        layout.addWidget(title)

        self.list_area = QListWidget()
        self.list_area.setUniformItemSizes(False)
        self.list_area.setSpacing(6)
        self.list_area.setStyleSheet(
            """
            QListWidget {
                background: #f7f5fb;
                border: 1px solid #e0d8ec;
                border-radius: 8px;
                padding: 6px;
            }
            QListWidget::item {
                background: white;
                border-radius: 6px;
                padding: 8px 10px;
                margin: 2px 0px;
                color: #3e3550;
                font-size: 10.5pt;
            }
            QListWidget::item:selected {
                background: #e5dcf4;
                color: #2e2640;
            }
            QListWidget::item:hover {
                background: #f0e8ff;
            }
            """
        )

        for v in visitors:
            name = f"{v.get('first_name','')} {v.get('last_name','')}".strip()
            nric = v.get('nric') or "-"
            hp_no = v.get('hp_no') or "-"
            text = f"Name: {name}\nNRIC: {nric}\nHP No: {hp_no}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, v)
            item.setSizeHint(QSize(item.sizeHint().width(), 36))
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

        # Core Fields (HP No first, then NRIC)
        self.hp = self._make_input("HP No.")
        hp_validator = QRegularExpressionValidator(QRegularExpression(r"^[0-9+\-]*$"), self)
        self.hp.setValidator(hp_validator)
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_existing)
        self.search_btn.hide()

        hp_row = QHBoxLayout()
        hp_row.addWidget(self.hp)
        hp_row.addWidget(self.search_btn)

        self.nric = self._make_input("NRIC")
        self.fn = self._make_input("First Name")
        self.ln = self._make_input("Last Name")
        self.purpose = self._make_input("Purpose")
        self.dest = self._make_input("Destination")
        self.person = self._make_input("Person To Visit")

        self.id_number = self._make_input("Pass Number (Optional)")

        self.category = self._make_input(combo=True, items=["Visitor", "Vendor", "Drop-off"])
        self.company = self._make_input("Company")
        self.vehicle = self._make_input("Vehicle No.")

        self.remarks = QTextEdit()
        self.remarks.setStyleSheet(INPUT_STYLE)

        self.hp_error = QLabel("")
        self.hp_error.setStyleSheet("color:red; font-size:9pt;")
        self.hp_error.hide()

        self.nric_error = QLabel("")
        self.nric_error.setStyleSheet("color:red; font-size:9pt;")
        self.nric_error.hide()

        left.addRow(self._make_label("HP No:"), hp_row)
        left.addRow("", self.hp_error)
        left.addRow(self._make_label("NRIC:"), self.nric)
        left.addRow("", self.nric_error)
        left.addRow(self._make_label("First Name:"), self.fn)
        left.addRow(self._make_label("Last Name:"), self.ln)
        left.addRow(self._make_label("Purpose:"), self.purpose)
        left.addRow(self._make_label("Destination:"), self.dest)
        left.addRow("Pass Number:", self.id_number)

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
        hp = self.hp.text().strip()

        if not hp:
            msg = QMessageBox(
                QMessageBox.Warning,
                "Missing",
                "Please enter HP No. to search.",
                QMessageBox.Ok,
                self
            )
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
            return

        if self.db_manager.has_active_visit(nric="", hp_no=hp):
            msg = QMessageBox(
                QMessageBox.Warning,
                "Visitor Already Inside",
                "This visitor is still active and cannot be checked-in again.",
                QMessageBox.Ok,
                self
            )
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
            return

        matches = self.db_manager.find_visitors_by_nric(nric="", hp_no=hp)
        if not matches:
            msg = QMessageBox(
                QMessageBox.Information,
                "Not Found",
                "No matching visitor found.",
                QMessageBox.Ok,
                self
            )
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
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
        text = self.nric.text().strip()
        valid = bool(text)
        self.nric_error.setVisible(not valid)
        self.nric_error.setText("NRIC is required.")
        return valid

    def validate_hp(self):
        text = self.hp.text().strip()
        valid = bool(text) and all(ch.isdigit() or ch in "+-" for ch in text)
        self.hp_error.setVisible(not valid)
        self.hp_error.setText("HP No. can contain digits.")
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
    def generate_visitor_pass_pdf(self, visit_id: str, check_in_time: datetime, organization: str = "") -> str:
        """
        Generate an ID-card-style PDF pass with QR code for a visitor.
        Card size: 5.5 x 3.4 inches (landscape).
        """
        # Collect visitor data
        first_name = self.fn.text().strip()
        last_name = self.ln.text().strip()
        full_name = f"{first_name} {last_name}".strip()
        hp_no = self.hp.text().strip()
        category = self.category.currentText()
        destination = self.dest.text().strip()

        # Config for organization/location
        cfg = load_config()
        org_name = organization or cfg.get("organization_name", "")
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
        qr_payload = json.dumps(payload_dict)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=3,
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        # Passes directory
        passes_dir = os.path.join(os.getcwd(), "passes")
        os.makedirs(passes_dir, exist_ok=True)
        pdf_path = os.path.join(passes_dir, f"{visit_id}.pdf")

        # Card size in points
        card_width = 5.5 * 72   # 396 pts
        card_height = 3.4 * 72  # 244.8 pts

        c = canvas.Canvas(pdf_path, pagesize=(card_width, card_height))

        # PRIMARY_COLOR border
        primary_rgb = tuple(int(PRIMARY_COLOR[i:i+2], 16) for i in (1, 3, 5))
        primary_color_norm = tuple(x / 255.0 for x in primary_rgb)
        c.setStrokeColor(primary_color_norm)
        c.setLineWidth(2)
        c.rect(3, 3, card_width - 6, card_height - 6, stroke=1, fill=0)

        # -------- QR at top center --------
        top_margin = 10
        qr_size = 80  # smaller QR so more room for text
        qr_x = (card_width - qr_size) / 2
        qr_y = card_height - top_margin - qr_size
        qr_img_pil = Image.open(qr_buffer)
        c.drawImage(ImageReader(qr_img_pil), qr_x, qr_y, width=qr_size, height=qr_size)

        # -------- Fields in a single line each --------
        # We place them between qr bottom and footer line, evenly spaced.
        footer_line_y = 60  # where footer separator line will be
        field_area_top = qr_y - 20
        field_area_bottom = footer_line_y + 8
        fields = [
            ("HP No.", hp_no or "-"),
            ("Name", full_name or "-"),
            ("Category", category or "-"),
            ("Destination", destination or "-"),
            ("In-Time", check_in_time.strftime("%Y-%m-%d %H:%M")),
        ]

        num_fields = len(fields)
        available_height = max(10, field_area_top - field_area_bottom)
        # Even spacing; we keep some margin above/below
        line_gap = available_height / (num_fields + 1)

        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0, 0, 0)

        for idx, (label, value) in enumerate(fields, start=1):
            y = field_area_bottom + idx * line_gap
            text = f"{label}: {value}"
            text_width = c.stringWidth(text, "Helvetica", 9)
            x = (card_width - text_width) / 2
            c.drawString(x, y, text)

        # -------- Footer (org / location / M-Neo VMS + logo) --------
        footer_y = 20
        line_y = footer_line_y
        c.setStrokeColor(primary_color_norm)
        c.setLineWidth(0.5)
        c.line(20, line_y, card_width - 20, line_y)

        footer_texts = []
        if org_name:
            footer_texts.append(org_name)
        if location:
            footer_texts.append(location)
        footer_texts.append("M-Neo VMS")

        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.4, 0.4, 0.4)

        footer_spacing = 9
        first_line_y = footer_y + footer_spacing * (len(footer_texts) - 1)
        for i, text in enumerate(footer_texts):
            y = first_line_y - i * footer_spacing
            text_width = c.stringWidth(text, "Helvetica", 7)
            x = (card_width - text_width) / 2
            c.drawString(x, y, text)

        # Logo in bottom-left, small
        app_base = Path(__file__).resolve().parents[1]
        logo_path = app_base / "assets" / "logo.png"
        if logo_path.exists():
            try:
                logo_img = Image.open(str(logo_path))
                logo_size = 22
                logo_x = 15
                logo_y = 10
                c.drawImage(ImageReader(logo_img), logo_x, logo_y, width=logo_size, height=logo_size)
            except Exception:
                pass

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
            msg = QMessageBox(
                QMessageBox.Warning,
                "Missing Required Fields",
                "Please fill:\n\n• " + "\n• ".join(missing),
                QMessageBox.Ok,
                self
            )
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
            return

        hp_val = self.hp.text().strip()
        if self.db_manager.is_hp_blacklisted(hp_val):
            msg = QMessageBox(
                QMessageBox.Warning,
                "Blacklisted",
                "This HP No. is blacklisted and cannot be registered.",
                QMessageBox.Ok,
                self
            )
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
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
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Save Failed",
                    "Visitor could not be saved. Please check the details and try again.",
                    QMessageBox.Ok,
                    self
                )
                msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                msg.exec_()
                return

            cfg = load_config()
            organization = cfg.get("organization_name", "")

            msg_box = QMessageBox(
                QMessageBox.Question,
                "Generate Pass",
                f"Visitor registered successfully.\nVisit ID: {visit_id}\n\nWould you like to generate a visitor pass PDF?",
                QMessageBox.Yes | QMessageBox.No,
                self
            )
            msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg_box.setDefaultButton(QMessageBox.Yes)
            reply = msg_box.exec_()

            if reply == QMessageBox.Yes:
                try:
                    pdf_path = self.generate_visitor_pass_pdf(visit_id, check_in_time, organization)
                    msg = QMessageBox(
                        QMessageBox.Information,
                        "Pass Generated",
                        f"Visitor pass PDF has been generated:\n{pdf_path}\n\nYou can open or print the PDF using your system tools.",
                        QMessageBox.Ok,
                        self
                    )
                    msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                    msg.exec_()
                except Exception:
                    logging.error(f"Failed to generate visitor pass PDF: {traceback.format_exc()}")
                    msg = QMessageBox(
                        QMessageBox.Critical,
                        "Pass Generation Failed",
                        "Pass generation failed. The visitor has still been registered successfully.",
                        QMessageBox.Ok,
                        self
                    )
                    msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                    msg.exec_()

            self.visitor_registered.emit()
            self.show_selection()

        except Exception:
            logging.error(traceback.format_exc())
            msg = QMessageBox(
                QMessageBox.Critical,
                "Error",
                "Registration failed.",
                QMessageBox.Ok,
                self
            )
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
