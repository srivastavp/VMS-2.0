# ui/printer_settings.py
"""
Minimal printer configuration dialog for visitor-pass printing.

Lets the user pick which installed Windows printer (e.g. the Brother
QL-800, once installed normally through its Windows driver) should be
used for visitor passes, persist that choice, and run a test print.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QPushButton, QLabel, QMessageBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QTimer

from datetime import datetime

from utils import app_config
from utils.printer_manager import PrinterManager, PrintWorker
from utils.pass_renderer import build_pass_data
from utils.styles import PRIMARY_COLOR


class PrinterSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Printer Settings")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._build_ui()
        self._load_current()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Visitor Pass Printer")
        title.setStyleSheet(f"color:{PRIMARY_COLOR}; font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        form = QFormLayout()

        self.printer_combo = QComboBox()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._populate_printers)
        printer_row = QHBoxLayout()
        printer_row.addWidget(self.printer_combo, 1)
        printer_row.addWidget(refresh_btn)
        form.addRow("Printer:", printer_row)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(10.0, 200.0)
        self.width_spin.setSuffix(" mm")
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(10.0, 200.0)
        self.height_spin.setSuffix(" mm")

        form.addRow("Label Width:", self.width_spin)
        form.addRow("Label Height:", self.height_spin)

        layout.addLayout(form)

        note = QLabel(
            "Label dimensions should match the label roll loaded in the "
            "printer. Confirm with the actual Brother QL-800 media before "
            "printing a full batch of passes."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#777; font-size: 8pt;")
        layout.addWidget(note)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        test_btn = QPushButton("Test Print")
        test_btn.clicked.connect(self._test_print)
        btn_row.addWidget(test_btn)

        # TEMPORARY diagnostic tool for verifying the print coordinate
        # system (page size/DPI/font sizing) directly on physical
        # hardware. Safe to remove once the Brother QL-800 output has
        # been confirmed correct.
        diag_btn = QPushButton("Diagnostic Print (temp)")
        diag_btn.setToolTip(
            "Prints a millimetre grid, coordinate markers, and printer/DPI "
            "info to verify the print coordinate system on real hardware."
        )
        diag_btn.clicked.connect(self._diagnostic_print)
        btn_row.addWidget(diag_btn)
        btn_row.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _populate_printers(self, select_name: str = None):
        current = select_name or self.printer_combo.currentText()
        self.printer_combo.clear()
        printers = PrinterManager.list_printers()
        if not printers:
            self.status_label.setText("No Windows printers were found. Install the Brother QL-800 driver first.")
            return
        self.printer_combo.addItems(printers)
        if current and current in printers:
            self.printer_combo.setCurrentText(current)

    def _load_current(self):
        self._populate_printers()
        configured = app_config.get_configured_printer_name()
        default_printer = PrinterManager.get_default_printer()
        target = configured or default_printer
        if target:
            idx = self.printer_combo.findText(target)
            if idx >= 0:
                self.printer_combo.setCurrentIndex(idx)

        if not configured and default_printer:
            self.status_label.setText(f"No printer configured yet — currently using Windows default: {default_printer}")

        width_mm, height_mm = app_config.get_label_size_mm()
        self.width_spin.setValue(width_mm)
        self.height_spin.setValue(height_mm)

    def _save(self):
        name = self.printer_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Missing", "Please select a printer.")
            return
        app_config.set_configured_printer_name(name)
        app_config.set_config_value(app_config.KEY_LABEL_WIDTH_MM, self.width_spin.value())
        app_config.set_config_value(app_config.KEY_LABEL_HEIGHT_MM, self.height_spin.value())
        self.accept()

    def _test_print(self):
        name = self.printer_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Missing", "Please select a printer first.")
            return

        # Apply pending label size for the test print without requiring Save first
        app_config.set_config_value(app_config.KEY_LABEL_WIDTH_MM, self.width_spin.value())
        app_config.set_config_value(app_config.KEY_LABEL_HEIGHT_MM, self.height_spin.value())

        self.status_label.setText("Printing test pass...")

        sample = build_pass_data(
            visit_id="TEST-0000",
            check_in_time=datetime.now(),
            first_name="Test",
            last_name="Print",
            hp_no="00000000",
            category="Test",
            destination="N/A",
        )

        # Run off the UI thread so the dialog (and app) stay responsive.
        self._test_worker = PrintWorker(sample, printer_name=name, parent=self)
        self._test_worker.finished_result.connect(self._on_test_print_finished)
        self._test_worker.start()

    def _on_test_print_finished(self, success: bool, message: str):
        if success:
            self.status_label.setText(f"✅ {message}")
        else:
            self.status_label.setText(f"❌ {message}")
            QMessageBox.warning(self, "Test Print Failed", message)

    def _diagnostic_print(self):
        """TEMPORARY: see PrinterManager.print_diagnostic for details."""
        name = self.printer_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Missing", "Please select a printer first.")
            return

        app_config.set_config_value(app_config.KEY_LABEL_WIDTH_MM, self.width_spin.value())
        app_config.set_config_value(app_config.KEY_LABEL_HEIGHT_MM, self.height_spin.value())

        self.status_label.setText("Printing diagnostic pattern...")
        # Windows native printing must run on the main thread (see
        # PrintWorker), so defer via QTimer instead of a QThread.
        QTimer.singleShot(0, lambda: self._run_diagnostic_print(name))

    def _run_diagnostic_print(self, name: str):
        success, message = PrinterManager.print_diagnostic(name)
        if success:
            self.status_label.setText(f"✅ {message}")
        else:
            self.status_label.setText(f"❌ {message}")
            QMessageBox.warning(self, "Diagnostic Print Failed", message)
