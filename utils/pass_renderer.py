"""
Visitor pass rendering.

This module is the single source of truth for what goes on a visitor pass
(the fields, their order, the QR payload) and how it is laid out. Two output
targets are supported from the same visitor-pass data:

- ``generate_pdf``  -> writes a PDF file (existing CR80 ID-card design,
  used as a fallback / for administrative or troubleshooting use).
- ``draw_pass``     -> draws directly onto a QPainter, used by
  ``PrinterManager`` to send the pass straight to a Windows printer
  (e.g. the Brother QL-800) without ever touching a PDF file.

Keeping the visual design in one place means both paths always stay in
sync when the pass design changes.
"""
from datetime import datetime
from pathlib import Path
import io
import json
import logging

import qrcode
from PIL import Image

from utils.app_config import load_config, get_desktop_dir
from utils.styles import PRIMARY_COLOR

APP_BASE = Path(__file__).resolve().parents[1]

# CR80 ID-card size (3.375 x 2.125 in) — used for the PDF fallback output.
# This is independent of the physical label size configured for direct
# printing (see utils.app_config.get_label_size_mm), per client requirement
# that PDF dimensions and printer label dimensions be configurable
# separately.
PDF_CARD_WIDTH_PT = 3.375 * 72
PDF_CARD_HEIGHT_PT = 2.125 * 72


def _primary_color_rgb_norm():
    rgb = tuple(int(PRIMARY_COLOR[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(x / 255.0 for x in rgb)


def build_pass_data(
    visit_id: str,
    check_in_time: datetime,
    first_name: str = "",
    last_name: str = "",
    hp_no: str = "",
    category: str = "",
    destination: str = "",
    company: str = "",
    vehicle_number: str = "",
    person_visited: str = "",
    purpose: str = "",
) -> dict:
    """
    Build the canonical visitor-pass data dict consumed by both the PDF
    generator and the direct-print renderer. This keeps the field set/order
    identical for both output paths and avoids duplicating field-gathering
    logic across UI modules (registration, active visitors, reprint, etc.)
    """
    cfg = load_config()
    full_name = f"{first_name} {last_name}".strip()

    return {
        "visit_id": visit_id,
        "check_in_time": check_in_time,
        "full_name": full_name or "-",
        "hp_no": hp_no or "-",
        "category": category or "-",
        "destination": destination or "-",
        "company": company or "-",
        "vehicle_number": vehicle_number or "-",
        "person_visited": person_visited or "-",
        "purpose": purpose or "-",
        "organization": cfg.get("organization_name", ""),
        "location": cfg.get("location_name", ""),
    }


def _qr_payload(data: dict) -> str:
    payload = {
        "type": "VMS_PASS",
        "visit_id": data["visit_id"],
        "hp_no": data["hp_no"],
        "name": data["full_name"],
        "category": data["category"],
        "destination": data["destination"],
        "in_time": data["check_in_time"].isoformat() if isinstance(data["check_in_time"], datetime) else str(data["check_in_time"]),
        "organization": data.get("organization", ""),
        "location": data.get("location", ""),
        "application": "M-Neo VMS",
    }
    return json.dumps(payload)


def _make_qr_image(data: dict) -> Image.Image:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=3,
    )
    qr.add_data(_qr_payload(data))
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _pass_fields(data: dict) -> list:
    check_in_time = data["check_in_time"]
    in_time_str = (
        check_in_time.strftime("%Y-%m-%d %H:%M")
        if isinstance(check_in_time, datetime)
        else str(check_in_time)
    )
    return [
        ("Name", data["full_name"]),
        ("HP No.", data["hp_no"]),
        ("Category", data["category"]),
        ("Destination", data["destination"]),
        ("Visit ID", data["visit_id"]),
        ("In-Time", in_time_str),
    ]


# ------------------------------------------------------
# PDF output (fallback / administrative use)
# ------------------------------------------------------
def generate_pdf(data: dict, output_path: str = None) -> str:
    """
    Render the visitor pass as a CR80 ID-card-sized PDF with a QR code.
    If output_path is not given, saves to the Desktop as
    VisitorPass_<visit_id>.pdf (kept for the "Save PDF" fallback action).
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    if not output_path:
        desktop_dir = get_desktop_dir()
        output_path = str(desktop_dir / f"VisitorPass_{data['visit_id']}.pdf")

    qr_img = _make_qr_image(data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    card_width, card_height = PDF_CARD_WIDTH_PT, PDF_CARD_HEIGHT_PT
    c = canvas.Canvas(output_path, pagesize=(card_width, card_height))

    primary_color_norm = _primary_color_rgb_norm()
    c.setStrokeColor(primary_color_norm)
    c.setLineWidth(1.5)
    c.rect(2, 2, card_width - 4, card_height - 4, stroke=1, fill=0)

    margin = 6

    # QR at top-right
    qr_size = 40
    qr_x = card_width - margin - qr_size
    qr_y = card_height - margin - qr_size  # bottom edge of the QR box
    c.drawImage(ImageReader(Image.open(qr_buffer)), qr_x, qr_y, width=qr_size, height=qr_size)

    # Header (org name) — width-limited so it never runs under the QR code,
    # shrinking the font before falling back to truncation.
    header_font_size = 7
    header_width_limit = qr_x - margin - 4
    header_text = data.get("organization") or "M-Neo VMS"
    while c.stringWidth(header_text, "Helvetica-Bold", header_font_size) > header_width_limit and header_font_size > 5:
        header_font_size -= 1
    while c.stringWidth(header_text, "Helvetica-Bold", header_font_size) > header_width_limit and len(header_text) > 3:
        header_text = header_text[:-1]
    c.setFont("Helvetica-Bold", header_font_size)
    c.setFillColorRGB(*primary_color_norm)
    header_baseline = card_height - margin - header_font_size
    c.drawString(margin, header_baseline, header_text)

    # Fields — the field block always starts below BOTH the header text and
    # the QR code, so rows never get hidden/overlapped underneath the QR.
    fields = _pass_fields(data)
    footer_font_size = 5
    footer_reserved = footer_font_size + 4
    fields_top = min(header_baseline - 4, qr_y - 2)
    fields_bottom = margin + footer_reserved
    available_height = max(fields_top - fields_bottom, 6)
    row_height = available_height / max(1, len(fields))
    field_font_size = max(4, min(6, row_height * 0.6))

    c.setFillColorRGB(0, 0, 0)
    text_width_limit = card_width - margin - 4
    for idx, (label, value) in enumerate(fields):
        text = f"{label}: {value}"
        while c.stringWidth(text, "Helvetica", field_font_size) > text_width_limit and len(value) > 3:
            value = value[:-1]
            text = f"{label}: {value}..."
        c.setFont("Helvetica", field_font_size)
        y = fields_top - (idx + 1) * row_height + (row_height - field_font_size) / 2
        c.drawString(margin, y, text)

    # Footer
    c.setFont("Helvetica", footer_font_size)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    footer_text = " | ".join(t for t in [data.get("location"), "M-Neo VMS"] if t)
    while c.stringWidth(footer_text, "Helvetica", footer_font_size) > text_width_limit and len(footer_text) > 3:
        footer_text = footer_text[:-1]
    c.drawString(margin, margin, footer_text)

    c.save()
    return output_path


# ------------------------------------------------------
# Direct-to-printer output (QPainter, used by PrinterManager)
# ------------------------------------------------------
def draw_pass(painter, data: dict, width_px: float, height_px: float) -> None:
    """
    Draw the visitor pass onto an already-configured QPainter, within a
    (0, 0, width_px, height_px) rectangle. Mirrors the PDF layout as
    closely as the label media allows.
    """
    from PyQt5.QtCore import Qt, QRectF
    from PyQt5.QtGui import QPen, QColor, QFont, QImage

    primary_rgb = tuple(int(PRIMARY_COLOR[i:i + 2], 16) for i in (1, 3, 5))
    primary_qcolor = QColor(*primary_rgb)

    margin = max(2.0, width_px * 0.02)

    # Border
    pen = QPen(primary_qcolor)
    pen.setWidthF(max(1.0, width_px * 0.006))
    painter.setPen(pen)
    painter.drawRect(QRectF(margin / 2, margin / 2, width_px - margin, height_px - margin))

    # QR code (top-right)
    qr_img = _make_qr_image(data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qimg = QImage.fromData(qr_buffer.getvalue())
    qr_size = min(height_px * 0.4, width_px * 0.3)
    qr_x = width_px - margin - qr_size
    qr_y = margin
    painter.drawImage(QRectF(qr_x, qr_y, qr_size, qr_size), qimg)

    # Header (organization name), width-limited so it never runs under the QR
    header_height = height_px * 0.12
    header_font_size = max(6, int(height_px * 0.09))
    header_font = QFont("Segoe UI", header_font_size, QFont.Bold)
    painter.setFont(header_font)
    painter.setPen(QPen(primary_qcolor))
    header_text = (data.get("organization") or "M-Neo VMS")
    painter.drawText(
        QRectF(margin, margin, width_px - qr_size - margin * 3, header_height),
        Qt.AlignLeft | Qt.AlignVCenter,
        header_text,
    )

    # Fields — the field block always starts below BOTH the header and the
    # QR code (whichever extends further down), so rows are never hidden
    # underneath the QR image.
    footer_height = max(height_px * 0.08, 6)
    top_block_bottom = margin + max(header_height, qr_size)
    field_area_top = top_block_bottom + margin * 0.5
    field_area_bottom = height_px - margin - footer_height
    field_area_width = width_px - margin * 2
    fields = _pass_fields(data)
    available_height = max(field_area_bottom - field_area_top, 4)
    row_height = available_height / max(1, len(fields))
    field_font_size = max(4, min(int(height_px * 0.07), int(row_height * 0.65)))
    field_font = QFont("Segoe UI", field_font_size)
    painter.setFont(field_font)
    painter.setPen(QPen(QColor(0, 0, 0)))

    for idx, (label, value) in enumerate(fields):
        y = field_area_top + idx * row_height
        painter.drawText(
            QRectF(margin, y, field_area_width, row_height),
            Qt.AlignLeft | Qt.AlignVCenter,
            f"{label}: {value}",
        )

    # Footer
    footer_font = QFont("Segoe UI", max(4, int(height_px * 0.05)))
    painter.setFont(footer_font)
    painter.setPen(QPen(QColor(100, 100, 100)))
    footer_text = " | ".join(t for t in [data.get("location"), "M-Neo VMS"] if t)
    painter.drawText(
        QRectF(margin, height_px - margin - footer_height, field_area_width, footer_height),
        Qt.AlignLeft | Qt.AlignVCenter,
        footer_text,
    )
