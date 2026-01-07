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
import sqlite3
from pathlib import Path
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

from database import DatabaseManager
from utils.styles import PRIMARY_COLOR
from utils.pdpa import mask_nric


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
            nric = mask_nric(v.get('nric') or "") or "-"
            hp_no = v.get('hp_no') or "-"
            text = f"Name: {name}\nNRIC: {nric}\nHP No: {hp_no}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, v)
            item.setSizeHint(QSize(item.sizeHint().width(), 36))
            self.list_area.addItem(item)

        if self.list_area.count() > 0:
            self.list_area.setCurrentRow(0)

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
        self.list_area.itemDoubleClicked.connect(lambda _item: self._select())

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
        self._selected_existing_nric_raw = None
        self._build_ui()

    # --------------------------------------------------
    def _make_label(self, text: str, required=True):
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
        card.setMinimumWidth(480)
        card.setStyleSheet(CARD_STYLE)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(50, 40, 50, 40)

        title = QLabel("Select Visitor Type")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color:{PRIMARY_COLOR}; margin-bottom:16px;")
        title.setAlignment(Qt.AlignCenter)
        cl.addWidget(title)

        new_btn = QPushButton("New Visitor")
        existing_btn = QPushButton("Existing Visitor")
        new_btn.clicked.connect(lambda: self.show_form(False))
        existing_btn.clicked.connect(lambda: self.show_form(True))

        for b in (new_btn, existing_btn):
            b.setMinimumHeight(55)

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

        # Existing Visitor: Search (NRIC / HP)
        self.search_input = self._make_input("NRIC or HP No")

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_existing)
        self.search_input.hide()
        self.search_btn.hide()

        search_row = QHBoxLayout()
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.search_btn)

        # Remaining fields
        self.nric = self._make_input("NRIC")
        self.hp = self._make_input("HP No.")
        hp_validator = QRegularExpressionValidator(QRegularExpression(r"^[0-9+\-]*$"), self)
        self.hp.setValidator(hp_validator)
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

        # Errors
        self.hp_error = QLabel("")
        self.hp_error.setStyleSheet("color:red; font-size:9pt;")
        self.hp_error.hide()

        self.nric_error = QLabel("")
        self.nric_error.setStyleSheet("color:red; font-size:9pt;")
        self.nric_error.hide()

        # Layout
        left.addRow(self._make_label("NRIC:"), self.nric)
        left.addRow("", self.nric_error)
        left.addRow(self._make_label("HP No:"), self.hp)
        left.addRow("", self.hp_error)
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

        # Keep search at top (only for Existing Visitor)
        form_outer.insertLayout(0, search_row)

        # Events
        self.hp.textChanged.connect(self.validate_hp)
        self.nric.textChanged.connect(self.validate_nric)

        # Buttons
        actions = QHBoxLayout()
        clear = QPushButton("Clear")
        reg = QPushButton("Register / Check-In")
        clear.clicked.connect(self.clear_form)
        reg.clicked.connect(self.register_visitor)

        actions.addStretch()
        actions.addWidget(clear)
        actions.addWidget(reg)

        form_outer.addLayout(actions)

        p_layout.addWidget(card)
        return page

    # --------------------------------------------------
    def show_selection(self):
        self.stacked.setCurrentIndex(0)
        self.clear_form()

    def show_form(self, existing: bool):
        self.is_existing_visitor = existing
        self.search_input.setVisible(existing)
        self.search_btn.setVisible(existing)
        self.stacked.setCurrentIndex(1)

        if existing:
            self.search_input.setFocus()

    # --------------------------------------------------
    def _find_existing_visitors_by_query(self, value: str):
        """
        Return a list of most-recent completed visit profiles matching either NRIC or HP No.
        This is a UI-level helper (no schema changes) so Existing Visitor search can match
        both fields without the user specifying which.
        """
        raw = (value or "").strip()
        if not raw:
            return []

        nric = raw.upper()
        hp_no = raw

        query = """
            SELECT
                v.nric,
                v.hp_no,
                v.first_name,
                v.last_name,
                v.company,
                v.vehicle_number,
                v.purpose,
                v.destination,
                v.person_visited,
                v.check_in_time AS last_visit
            FROM visitors v
            JOIN (
                SELECT nric, hp_no, MAX(check_in_time) AS mx
                FROM visitors
                WHERE (nric = ? OR hp_no = ?)
                  AND check_out_time IS NOT NULL
                GROUP BY nric, hp_no
            ) t
              ON v.nric = t.nric
             AND v.hp_no = t.hp_no
             AND v.check_in_time = t.mx
            ORDER BY v.check_in_time DESC
        """

        try:
            with self.db_manager.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(query, (nric, hp_no))
                rows = cur.fetchall()
            return [dict(r) for r in rows]
        except Exception:
            logging.error(traceback.format_exc())
            return []

    def _apply_selected_visitor(self, v: dict):
        raw_nric = v.get("nric", "") or ""
        self._selected_existing_nric_raw = raw_nric
        self.nric.setText(mask_nric(raw_nric))
        self.hp.setText(v.get("hp_no", ""))
        self.fn.setText(v.get("first_name", ""))
        self.ln.setText(v.get("last_name", ""))
        self.purpose.setText(v.get("purpose", ""))
        self.dest.setText(v.get("destination", ""))
        self.person.setText(v.get("person_visited", ""))
        self.company.setText(v.get("company", ""))
        self.vehicle.setText(v.get("vehicle_number", ""))

    def search_existing(self):
        value = self.search_input.text().strip()

        if not value:
            QMessageBox.warning(self, "Missing", "Please enter NRIC or HP No. to search.")
            return

        if self.db_manager.has_active_visit(nric=value.strip().upper(), hp_no=value.strip()):
            QMessageBox.warning(self, "Visitor Already Inside",
                                "This visitor is still active and cannot be checked-in again.")
            return

        matches = self._find_existing_visitors_by_query(value)
        if not matches:
            QMessageBox.information(self, "Not Found", "No visitor found.")
            return

        dialog = VisitorSelectionDialog(matches, self)
        if dialog.exec_():
            self._apply_selected_visitor(dialog.selected_visitor)

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
        for f in [
            self.nric, self.hp, self.fn, self.ln,
            self.purpose, self.dest, self.company,
            self.vehicle, self.person, self.id_number
        ]:
            f.clear()

        if hasattr(self, "search_input"):
            self.search_input.clear()

        self._selected_existing_nric_raw = None

        self.category.setCurrentIndex(0)
        self.remarks.clear()
        self.hp_error.hide()
        self.nric_error.hide()

    # ------------------------------------------------------
    # PDF PASS (3x4 inch portrait, compact QR)
    # ------------------------------------------------------
    def generate_visitor_pass_pdf(self, visit_id: str, check_in_time: datetime, organization="") -> str:
        """
        Generate a clean 3 × 4 inch portrait visitor badge PDF with a compact QR code.
        """
        # Collect form values
        first = self.fn.text().strip()
        last = self.ln.text().strip()
        full_name = f"{first} {last}".strip()

        hp_no = self.hp.text().strip()
        category = self.category.currentText()
        destination = self.dest.text().strip()

        # Load config
        cfg = load_config()
        org_name = organization or cfg.get("organization_name", "")
        location = cfg.get("location_name", "")

        # -------------------------------------------
        # SUPER LIGHTWEIGHT QR PAYLOAD
        # -------------------------------------------
        payload_str = (
            f"v|{visit_id}"
            f"|h|{hp_no}"
            f"|n|{full_name}"
            f"|c|{category}"
            f"|d|{destination}"
            f"|t|{check_in_time.isoformat()}"
        )

        # -------------------------------------------
        # QR Code (least dense possible)
        # -------------------------------------------
        qr = qrcode.QRCode(
            version=None,  # smallest QR version
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr.add_data(payload_str)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        # -------------------------------------------
        # Create passes directory on user's Desktop
        # -------------------------------------------
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        passes_dir = os.path.join(desktop_dir, "passes")
        os.makedirs(passes_dir, exist_ok=True)

        pdf_path = os.path.join(passes_dir, f"{visit_id}.pdf")

        # -------------------------------------------
        # PDF Dimensions (3" × 4" portrait)
        # -------------------------------------------
        card_w = 3 * 72      # 216 pts
        card_h = 4 * 72      # 288 pts

        c = canvas.Canvas(pdf_path, pagesize=(card_w, card_h))

        # Primary theme color
        primary_rgb = tuple(int(PRIMARY_COLOR[i:i+2], 16) for i in (1, 3, 5))
        primary_norm = tuple(v / 255 for v in primary_rgb)

        # Border
        c.setStrokeColor(primary_norm)
        c.setLineWidth(2)
        c.rect(3, 3, card_w - 6, card_h - 6)

        # -------------------------------------------
        # QR (Top Center)
        # -------------------------------------------
        qr_size = 110  # ~1.5 inches
        top_margin = 14
        qr_x = (card_w - qr_size) / 2
        qr_y = card_h - top_margin - qr_size

        qr_img_pil = Image.open(qr_buffer)
        c.drawImage(ImageReader(qr_img_pil), qr_x, qr_y, width=qr_size, height=qr_size)

        # -------------------------------------------
        # Visitor fields (label: value)
        # -------------------------------------------
        field_section_top = qr_y - 12
        footer_line_y = 70
        field_section_bottom = footer_line_y + 12

        fields = [
            ("HP No.", hp_no),
            ("Name", full_name),
            ("Category", category),
            ("Destination", destination),
            ("In-Time", check_in_time.strftime("%Y-%m-%d %H:%M")),
        ]

        available_height = field_section_top - field_section_bottom
        line_gap = available_height / (len(fields) + 1)

        c.setFont("Helvetica", 8.5)
        c.setFillColorRGB(0, 0, 0)

        for i, (label, value) in enumerate(fields, start=1):
            y = field_section_bottom + i * line_gap
            text = f"{label}: {value}"
            tw = c.stringWidth(text, "Helvetica", 8.5)
            c.drawString((card_w - tw) / 2, y, text)

        # -------------------------------------------
        # Footer
        # -------------------------------------------
        c.setStrokeColor(primary_norm)
        c.setLineWidth(0.5)
        c.line(15, footer_line_y, card_w - 15, footer_line_y)

        footer_texts = []
        if org_name:
            footer_texts.append(org_name)
        if location:
            footer_texts.append(location)
        footer_texts.append("M-Neo VMS")

        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.4, 0.4, 0.4)

        base_y = 23
        spacing = 9
        total = spacing * (len(footer_texts) - 1)
        first_y = base_y + total

        for i, text in enumerate(footer_texts):
            y = first_y - i * spacing
            tw = c.stringWidth(text, "Helvetica", 7)
            c.drawString((card_w - tw) / 2, y, text)

        # Logo (optional)
        logo_path = Path(__file__).resolve().parents[1] / "assets" / "logo.png"
        if logo_path.exists():
            try:
                logo_img = Image.open(str(logo_path))
                logo_size = 22
                c.drawImage(
                    str(logo_path),
                    10,
                    8,
                    width=logo_size,
                    height=logo_size,
                    mask='auto'
                )
            except Exception:
                pass

        c.save()
        return pdf_path

    # --------------------------------------------------
    def register_visitor(self):
        if not self.validate_nric() or not self.validate_hp():
            return

        required_fields = [
            (self.nric, "NRIC"),
            (self.hp, "HP No"),
            (self.fn, "First Name"),
            (self.ln, "Last Name"),
            (self.dest, "Destination"),
            (self.purpose, "Purpose"),
        ]

        missing = [name for field, name in required_fields if not field.text().strip()]
        if missing:
            QMessageBox.warning(
                self, "Missing Required Fields",
                "Please fill:\n\n• " + "\n• ".join(missing)
            )
            return

        # Blacklist check
        hp_val = self.hp.text().strip()
        nric_val = (self.nric.text().strip() or "").upper()
        if self.is_existing_visitor and self._selected_existing_nric_raw:
            nric_val = (self._selected_existing_nric_raw.strip() or "").upper()

        if self.db_manager.is_blacklisted(hp_no=hp_val, nric=nric_val):
            QMessageBox.warning(self, "Blacklisted",
                                "This HP No. is blacklisted and cannot be registered.")
            return

        try:
            visit_id = self.db_manager.generate_pass_number()
            check_in_time = datetime.now()

            nric_raw = (self.nric.text().strip() or "").upper()
            if self.is_existing_visitor and self._selected_existing_nric_raw:
                nric_raw = (self._selected_existing_nric_raw.strip() or "").upper()

            success = self.db_manager.add_visitor(
                nric=nric_raw,
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
                QMessageBox.warning(self, "Save Failed",
                                    "Visitor could not be saved. Please try again.")
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
