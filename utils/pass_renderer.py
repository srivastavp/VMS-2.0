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

    # Header — site/location name only (no brand/app name), width-limited
    # so it never runs under the QR code, shrinking the font before
    # falling back to truncation.
    header_text = data.get("location") or ""
    header_font_size = 7
    header_width_limit = qr_x - margin - 4
    if header_text:
        while c.stringWidth(header_text, "Helvetica-Bold", header_font_size) > header_width_limit and header_font_size > 5:
            header_font_size -= 1
        while c.stringWidth(header_text, "Helvetica-Bold", header_font_size) > header_width_limit and len(header_text) > 3:
            header_text = header_text[:-1]
        c.setFont("Helvetica-Bold", header_font_size)
        c.setFillColorRGB(*primary_color_norm)
        header_baseline = card_height - margin - header_font_size
        c.drawString(margin, header_baseline, header_text)
    else:
        header_baseline = card_height - margin

    # Fields — the field block always starts below BOTH the header text and
    # the QR code, so rows never get hidden/overlapped underneath the QR.
    # No footer/branding is reserved, so visitor fields get the full
    # remaining space on the card.
    fields = _pass_fields(data)
    fields_top = min(header_baseline - 4, qr_y - 2)
    fields_bottom = margin
    available_height = max(fields_top - fields_bottom, 6)
    row_height = available_height / max(1, len(fields))
    field_font_size = max(4, min(7, row_height * 0.6))

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

    # Header — site/location name only (no brand/app name), width-limited
    # so it never runs under the QR code.
    header_text = data.get("location") or ""
    header_height = height_px * 0.12 if header_text else 0
    if header_text:
        header_font_size = max(6, int(height_px * 0.09))
        # NOTE: header_font_size/field_font_size below are fractions of
        # height_px, which is in *device pixels* (from
        # printer.pageRect(QPrinter.DevicePixel)) at the printer's actual
        # resolution — not typographic points. QFont's constructor size
        # argument and setPointSize() are both interpreted as points
        # (1/72in) scaled by the paint device's DPI, which would make the
        # rendered text size scale with printer DPI instead of with the
        # physical label size, producing wildly oversized/overlapping
        # text on real (high-DPI) printers. setPixelSize() sizes the font
        # in the same device-pixel unit system used for every other
        # coordinate in this function, so it stays correctly proportioned
        # to the physical label regardless of the printer's DPI.
        header_font = QFont("Segoe UI")
        header_font.setBold(True)
        header_font.setPixelSize(header_font_size)
        painter.setFont(header_font)
        painter.setPen(QPen(primary_qcolor))
        painter.drawText(
            QRectF(margin, margin, width_px - qr_size - margin * 3, header_height),
            Qt.AlignLeft | Qt.AlignVCenter,
            header_text,
        )

    # Fields — the field block always starts below BOTH the header and the
    # QR code (whichever extends further down), so rows are never hidden
    # underneath the QR image. No footer/branding is reserved, so visitor
    # fields get the full remaining space on the label.
    top_block_bottom = margin + max(header_height, qr_size)
    field_area_top = top_block_bottom + margin * 0.5
    field_area_bottom = height_px - margin
    field_area_width = width_px - margin * 2
    fields = _pass_fields(data)
    available_height = max(field_area_bottom - field_area_top, 4)
    row_height = available_height / max(1, len(fields))
    field_font_size = max(4, min(int(height_px * 0.07), int(row_height * 0.65)))
    field_font = QFont("Segoe UI")
    field_font.setPixelSize(field_font_size)  # see note above re: pixel vs point size
    painter.setFont(field_font)
    painter.setPen(QPen(QColor(0, 0, 0)))

    for idx, (label, value) in enumerate(fields):
        y = field_area_top + idx * row_height
        painter.drawText(
            QRectF(margin, y, field_area_width, row_height),
            Qt.AlignLeft | Qt.AlignVCenter,
            f"{label}: {value}",
        )


# ------------------------------------------------------
# TEMPORARY diagnostic pattern (not part of the visitor-pass design)
# ------------------------------------------------------
def draw_diagnostic_pattern(painter, width_px: float, height_px: float, width_mm: float, height_mm: float, info: dict) -> None:
    """
    TEMPORARY DIAGNOSTIC TOOL.

    Draws a millimetre grid with coordinate markers, physical size
    reference text, and printer/DPI metadata so the print coordinate
    system (page size, DPI, device-pixel <-> physical-size mapping,
    font sizing) can be visually verified against a ruler on a real
    printed label. Intended to be run once against the actual Brother
    QL-800 to confirm the fix in draw_pass(); not shown to end users
    and safe to delete (along with PrinterManager.print_diagnostic)
    once verified.
    """
    from PyQt5.QtCore import Qt, QRectF, QLineF
    from PyQt5.QtGui import QPen, QColor, QFont

    px_per_mm_x = (width_px / width_mm) if width_mm else 1.0
    px_per_mm_y = (height_px / height_mm) if height_mm else 1.0

    # Outer label boundary
    pen = QPen(QColor(0, 0, 0))
    pen.setWidthF(max(1.0, width_px * 0.004))
    painter.setPen(pen)
    painter.drawRect(QRectF(0, 0, width_px, height_px))

    label_px = max(6, int(min(px_per_mm_x, px_per_mm_y) * 1.6))
    grid_font = QFont("Segoe UI")
    grid_font.setPixelSize(label_px)
    painter.setFont(grid_font)

    # Vertical grid lines every 1mm (minor) / 5mm (major, labelled with X in mm)
    x_mm = 0
    while x_mm <= width_mm:
        x = x_mm * px_per_mm_x
        major = (x_mm % 5 == 0)
        pen.setColor(QColor(0, 0, 0) if major else QColor(190, 190, 190))
        pen.setWidthF(1.2 if major else 0.5)
        painter.setPen(pen)
        painter.drawLine(QLineF(x, 0, x, height_px))
        if major:
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.drawText(QRectF(x + 1, 0, px_per_mm_x * 5, label_px + 2), Qt.AlignLeft, str(x_mm))
        x_mm += 1

    # Horizontal grid lines every 1mm (minor) / 5mm (major, labelled with Y in mm)
    y_mm = 0
    while y_mm <= height_mm:
        y = y_mm * px_per_mm_y
        major = (y_mm % 5 == 0)
        pen.setColor(QColor(0, 0, 0) if major else QColor(190, 190, 190))
        pen.setWidthF(1.2 if major else 0.5)
        painter.setPen(pen)
        painter.drawLine(QLineF(0, y, width_px, y))
        if major:
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.drawText(QRectF(0, y + 1, px_per_mm_x * 6, label_px + 2), Qt.AlignLeft, str(y_mm))
        y_mm += 1

    # Reference text rendered at known physical sizes (2mm / 3mm tall) so
    # the actual printed height can be checked against a ruler.
    ref_top = height_mm * 0.35 * px_per_mm_y
    for mm_height in (2, 3):
        ref_font = QFont("Segoe UI")
        ref_font.setPixelSize(max(4, int(mm_height * px_per_mm_y)))
        painter.setFont(ref_font)
        painter.setPen(QPen(QColor(0, 90, 0)))
        painter.fillRect(QRectF(width_mm * 0.35 * px_per_mm_x, ref_top, width_mm * 0.6 * px_per_mm_x, mm_height * px_per_mm_y * 1.4), QColor(255, 255, 255, 230))
        painter.drawText(
            QRectF(width_mm * 0.35 * px_per_mm_x, ref_top, width_mm * 0.6 * px_per_mm_x, mm_height * px_per_mm_y * 1.4),
            Qt.AlignLeft | Qt.AlignVCenter,
            f"{mm_height}mm text ABC123",
        )
        ref_top += mm_height * px_per_mm_y * 1.6

    # Metadata block: exactly what QPrinter/Windows reported for this job.
    meta_lines = [
        f"Printer: {info.get('printer_name')}",
        f"Configured label: {info.get('width_mm'):.1f} x {info.get('height_mm'):.1f} mm",
        f"pageRect(DevicePixel): {info.get('width_px'):.0f} x {info.get('height_px'):.0f} px",
        f"printer.resolution(): {info.get('resolution_dpi')} dpi",
        f"physicalDpi: {info.get('physical_dpi_x')} x {info.get('physical_dpi_y')}",
        f"logicalDpi: {info.get('logical_dpi_x')} x {info.get('logical_dpi_y')}",
        f"px/mm: {px_per_mm_x:.2f} x {px_per_mm_y:.2f}",
    ]
    meta_px = max(6, int(min(px_per_mm_x, px_per_mm_y) * 1.5))
    meta_font = QFont("Segoe UI")
    meta_font.setPixelSize(meta_px)
    painter.setFont(meta_font)
    meta_top = height_mm * 0.55 * px_per_mm_y
    for idx, line in enumerate(meta_lines):
        row_rect = QRectF(width_mm * 0.05 * px_per_mm_x, meta_top + idx * (meta_px + 2), width_mm * 0.9 * px_per_mm_x, meta_px + 2)
        painter.fillRect(row_rect, QColor(255, 255, 255, 230))
        painter.setPen(QPen(QColor(180, 0, 0)))
        painter.drawText(row_rect, Qt.AlignLeft | Qt.AlignVCenter, line)
