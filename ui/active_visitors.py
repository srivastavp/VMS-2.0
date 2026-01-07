# ui/active_visitors.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QMessageBox, QHeaderView,
    QSizePolicy, QAbstractItemView, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont
import logging
import traceback

from database import DatabaseManager
from utils.styles import PRIMARY_COLOR
from utils.pdpa import mask_nric


class ActiveVisitorsWidget(QWidget):
    visitor_checked_out = pyqtSignal()

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    # ===================================================================
    # UI INITIALIZATION
    # ===================================================================
    def init_ui(self):
        layout = QVBoxLayout(self)

        # ---------- HEADER ----------
        header_layout = QHBoxLayout()

        self.checkout_btn = QPushButton("Checkout Visitor")
        self.checkout_btn.setCursor(Qt.PointingHandCursor)
        self.checkout_btn.setEnabled(False)
        self.checkout_btn.setStyleSheet(f"""
            QPushButton {{
                background: #D4A017;
                color: #1f1f1f;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #C29113; }}
            QPushButton:pressed {{ background: #A97D10; }}
            QPushButton:disabled {{ background: #c9c3cc; color: #ffffff; }}
        """)
        self.checkout_btn.clicked.connect(self.checkout_selected)
        header_layout.addWidget(self.checkout_btn)

        header_layout.addStretch()

        # Search by HP No.
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by HP No.")
        self.search_input.setMinimumWidth(180)
        self.search_input.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #dcd6dd;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: %s;
            }
            """ % PRIMARY_COLOR
        )
        # Trigger filtering when user presses Enter or after editing
        self.search_input.returnPressed.connect(self.refresh_data)
        self.search_input.textChanged.connect(self.refresh_data)
        header_layout.addWidget(self.search_input)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PRIMARY_COLOR};
                color: white;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {PRIMARY_COLOR}CC; }}
            QPushButton:pressed {{ background: {PRIMARY_COLOR}AA; }}
        """)
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)

        header_layout.addStretch()

        # Status + centralized checkout on the right
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 10pt; margin: 8px 0;")
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # ---------- TABLE ----------
        self.table = QTableWidget()
        self.table.setColumnCount(15)

        # ✅ RE-ORDERED AS REQUESTED
        self.table.setHorizontalHeaderLabels([
            "Internal ID",
            "NRIC",
            "HP No.",
            "First Name",
            "Last Name",
            "Category",
            "Purpose",
            "Destination",
            "Company",
            "Vehicle No.",
            "Person Visited",
            "Remarks",
            "Visit ID",
            "Pass Number",
            "Check-in Time"
        ])

        # Hide internal DB ID
        self.table.setColumnHidden(0, True)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.verticalHeader().setDefaultSectionSize(60)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)  # ✅ stop squeezing Action column
        header.setHighlightSections(False)
        header.setSectionsClickable(True)

        # Column sizing (kept original intent)
        small_cols = {1: 120, 2: 110, 5: 120}

        min_widths = {
            3: 160,
            4: 160,
            6: 180,
            7: 180,
            8: 160,
            9: 150,
            10: 170,
            11: 230,
            12: 150,  # Visit ID
            13: 150,  # Pass Number
            14: 200,  # Check-in Time
        }

        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
            if col in small_cols:
                self.table.setColumnWidth(col, small_cols[col])
            elif col in min_widths:
                self.table.setColumnWidth(col, min_widths[col])

        layout.addWidget(self.table)
        self.setLayout(layout)

        # Enable / disable checkout button based on selection
        self.table.itemSelectionChanged.connect(self._update_checkout_btn_state)
        self.table.itemDoubleClicked.connect(self._clear_selection_on_double_click)

        self.refresh_data()

    def _clear_selection_on_double_click(self, item: QTableWidgetItem):
        self.table.clearSelection()
        self._update_checkout_btn_state()

    # ===================================================================
    # DATA REFRESH
    # ===================================================================
    def refresh_data(self):
        try:
            visitors = self.db_manager.get_active_visitors() or []

            # Optional filter by HP No from search box
            hp_filter = ""
            if hasattr(self, "search_input") and self.search_input.text().strip():
                hp_filter = self.search_input.text().strip()

            filtered = []
            for v in visitors:
                if hp_filter:
                    hp_val = str(v.get("hp_no", ""))
                    if hp_filter not in hp_val:
                        continue
                filtered.append(v)

            self.status_label.setText(f"Total active visitors: {len(filtered)}")
            self.table.setRowCount(0)

            for visitor in filtered:
                self._add_row(visitor)

            self.table.clearSelection()
            self._update_checkout_btn_state()

        except Exception:
            logging.error(traceback.format_exc())
            msg = QMessageBox(QMessageBox.Critical, "Error", "Failed to refresh visitor list.", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()

    # ===================================================================
    # ADD ROW
    # ===================================================================
    def _add_row(self, visitor):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 60)

        # ✅ DATA ORDER MATCHES HEADER ORDER
        data = [
            str(visitor.get('id', '')),
            mask_nric(visitor.get('nric', '') or ''),
            visitor.get('hp_no', ''),
            visitor.get('first_name', ''),
            visitor.get('last_name', ''),
            visitor.get('category', ''),
            visitor.get('purpose', ''),
            visitor.get('destination', ''),
            visitor.get('company', ''),
            visitor.get('vehicle_number', ''),
            visitor.get('person_visited', ''),
            visitor.get('remarks', ''),
            visitor.get('pass_number', ''),   # ✅ Visit ID
            visitor.get('id_number', ''),    # ✅ Pass Number
            visitor.get('check_in_time', '')
        ]

        for col, value in enumerate(data):
            item = QTableWidgetItem(str(value or ""))
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row, col, item)

    def _update_checkout_btn_state(self):
        if not hasattr(self, "checkout_btn"):
            return
        has_selection = len(self.table.selectionModel().selectedRows()) > 0
        self.checkout_btn.setEnabled(has_selection)

    def checkout_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return

        row = rows[0].row()
        id_item = self.table.item(row, 0)
        if not id_item:
            return

        try:
            visitor_id = int(id_item.text())
        except ValueError:
            return

        self.checkout_visitor(visitor_id)

    # ===================================================================
    # CHECKOUT
    # ===================================================================
    def checkout_visitor(self, visitor_id: int):
        msg = QMessageBox(QMessageBox.Question, "Confirm Checkout", "Are you sure you want to check out this visitor?", QMessageBox.Yes | QMessageBox.No, self)
        msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        reply = msg.exec_()

        if reply != QMessageBox.Yes:
            return

        try:
            if self.db_manager.checkout_visitor(visitor_id):
                msg = QMessageBox(QMessageBox.Information, "Success", "Visitor checked out successfully!", QMessageBox.Ok, self)
                msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                msg.exec_()
                self.refresh_data()
                self.visitor_checked_out.emit()
            else:
                msg = QMessageBox(QMessageBox.Critical, "Error", "Checkout failed.", QMessageBox.Ok, self)
                msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                msg.exec_()
        except Exception:
            logging.error(traceback.format_exc())
            msg = QMessageBox(QMessageBox.Critical, "Error", "An error occurred during checkout.", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
