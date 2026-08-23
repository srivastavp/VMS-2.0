"""
PrinterManager: thin abstraction over the Windows printer subsystem.

Responsibilities:
  - Enumerate installed Windows printers (via Qt's QPrinterInfo, which
    talks to the native Windows spooler — no Brother SDK involved).
  - Track/select which installed printer is used for visitor passes.
  - Send visitor-pass print jobs to that printer.
  - Report clear, non-technical errors when printing fails.
  - Support a test print that doesn't touch the database.

This keeps all printer-specific code out of the UI/registration modules:
callers only deal with a visitor-pass data dict (see utils.pass_renderer)
and get back a (success, message) result.

Printing runs the risk of blocking on I/O with the spooler/driver, so the
actual print call is executed off the UI thread via PrintWorker (QThread).
"""
import logging

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtPrintSupport import QPrinter, QPrinterInfo

from utils import app_config
from utils.pass_renderer import draw_pass, build_pass_data

logger = logging.getLogger(__name__)


class PrinterError(Exception):
    """Raised for user-facing printer problems (not installed/available/etc)."""


class PrinterManager:
    """Reusable, UI-agnostic printer management for visitor passes."""

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    @staticmethod
    def list_printers() -> list:
        """Return the names of all Windows printers currently installed."""
        try:
            return [p.printerName() for p in QPrinterInfo.availablePrinters()]
        except Exception:
            logger.exception("Failed to enumerate installed printers")
            return []

    @staticmethod
    def get_default_printer() -> str:
        """Return the Windows default printer name, or '' if none."""
        try:
            info = QPrinterInfo.defaultPrinter()
            return info.printerName() if not info.isNull() else ""
        except Exception:
            logger.exception("Failed to read Windows default printer")
            return ""

    @staticmethod
    def is_printer_available(name: str) -> bool:
        if not name:
            return False
        return name in PrinterManager.list_printers()

    # ------------------------------------------------------------------
    # Configuration (persisted to data/config.json)
    # ------------------------------------------------------------------
    @staticmethod
    def get_configured_printer() -> str:
        """
        Return the printer configured for visitor passes. Falls back to
        the Windows default printer if none has been explicitly configured
        (the caller is expected to surface which printer is actually being
        used, per the "no silent A4 printer" requirement).
        """
        configured = app_config.get_configured_printer_name()
        if configured:
            return configured
        return PrinterManager.get_default_printer()

    @staticmethod
    def has_explicit_printer_configured() -> bool:
        return bool(app_config.get_configured_printer_name())

    @staticmethod
    def set_printer(name: str) -> None:
        app_config.set_configured_printer_name(name)

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_printer(printer_name: str = None) -> str:
        name = printer_name or PrinterManager.get_configured_printer()
        if not name:
            raise PrinterError(
                "Visitor pass printer is not configured.\nPlease select a printer in Printer Settings."
            )
        if not PrinterManager.is_printer_available(name):
            raise PrinterError(
                f"The selected visitor pass printer ('{name}') is unavailable.\n"
                "Please check the USB connection and printer power, or select "
                "a different printer in Printer Settings."
            )
        return name

    @staticmethod
    def _print_data(data: dict, printer_name: str) -> None:
        """Low-level: render `data` (see pass_renderer.build_pass_data) to `printer_name`."""
        width_mm, height_mm = app_config.get_label_size_mm()

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPrinterName(printer_name)
        printer.setFullPage(True)
        printer.setPageMargins(0, 0, 0, 0, QPrinter.Millimeter)
        try:
            from PyQt5.QtGui import QPageSize
            from PyQt5.QtCore import QSizeF
            printer.setPageSize(QPageSize(QSizeF(width_mm, height_mm), QPageSize.Millimeter))
        except Exception:
            # Fallback for older PyQt5 versions without QPageSize
            printer.setPaperSize(_qsizef(width_mm, height_mm), QPrinter.Millimeter)

        if not printer.isValid():
            raise PrinterError(f"Windows could not open the printer '{printer_name}'.")

        # "Print to file" virtual drivers (Microsoft Print to PDF / XPS
        # Document Writer) otherwise pop a native "Save As" dialog and
        # block waiting for user input. Real physical printers (Brother
        # QL-800 included) are unaffected by this branch.
        if printer.outputFormat() != QPrinter.NativeFormat:
            import tempfile
            import os as _os
            suffix = ".pdf" if printer.outputFormat() == QPrinter.PdfFormat else ".out"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            _os.close(fd)
            printer.setOutputFileName(tmp_path)
            logger.info("Printer '%s' is a print-to-file driver; redirecting output to %s", printer_name, tmp_path)

        from PyQt5.QtGui import QPainter
        painter = QPainter()
        if not painter.begin(printer):
            raise PrinterError(f"Failed to start a print job on '{printer_name}'.")
        try:
            rect = printer.pageRect(QPrinter.DevicePixel) if hasattr(QPrinter, "DevicePixel") else printer.pageRect()
            width_px = rect.width()
            height_px = rect.height()
            draw_pass(painter, data, width_px, height_px)
        finally:
            painter.end()

    @staticmethod
    def print_visitor_pass(data: dict, printer_name: str = None) -> tuple:
        """
        Synchronous print call. Returns (success: bool, message: str).
        Intended to be invoked from a background thread (see PrintWorker)
        so the UI is never blocked by the spooler/driver.
        """
        visit_id = data.get("visit_id", "?")
        try:
            resolved_name = PrinterManager._resolve_printer(printer_name)
            logger.info("Print requested for visit_id=%s printer=%s", visit_id, resolved_name)
            PrinterManager._print_data(data, resolved_name)
            logger.info("Print succeeded for visit_id=%s printer=%s", visit_id, resolved_name)
            return True, f"Visitor pass printed successfully on '{resolved_name}'."
        except PrinterError as e:
            logger.warning("Print failed for visit_id=%s: %s", visit_id, e)
            return False, str(e)
        except Exception as e:
            logger.exception("Unexpected print error for visit_id=%s", visit_id)
            return False, f"An unexpected printer error occurred: {e}"

    @staticmethod
    def test_print(printer_name: str = None) -> tuple:
        """
        Print a sample visitor-pass-like layout to confirm the print
        pipeline works, WITHOUT creating any database record.
        """
        from datetime import datetime
        sample = build_pass_data(
            visit_id="TEST-0000",
            check_in_time=datetime.now(),
            first_name="Test",
            last_name="Print",
            hp_no="00000000",
            category="Test",
            destination="N/A",
        )
        return PrinterManager.print_visitor_pass(sample, printer_name)


def _qsizef(w, h):
    from PyQt5.QtCore import QSizeF
    return QSizeF(w, h)


class PrintWorker(QThread):
    """
    Runs PrinterManager.print_visitor_pass off the UI thread so the app
    never appears to freeze while a print job is being spooled.
    """
    finished_result = pyqtSignal(bool, str)

    def __init__(self, data: dict, printer_name: str = None, parent=None):
        super().__init__(parent)
        self.data = data
        self.printer_name = printer_name

    def run(self):
        success, message = PrinterManager.print_visitor_pass(self.data, self.printer_name)
        self.finished_result.emit(success, message)
