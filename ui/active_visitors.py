# ui/active_visitors.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QMessageBox, QHeaderView,
    QSizePolicy, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon
import logging
import traceback

from database import DatabaseManager
from utils.styles import PRIMARY_COLOR


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
        title = QLabel("Active Visitors")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {PRIMARY_COLOR};")
        header_layout.addWidget(title)
        header_layout.addStretch()

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

        layout.addLayout(header_layout)

        # ---------- STATUS ----------
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 10pt; margin: 8px 0;")
        layout.addWidget(self.status_label)

        # ---------- TABLE ----------
        self.table = QTableWidget()
        self.table.setColumnCount(16)

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
            "ID Number",
            "Check-in Time",
            "Action"
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
            13: 150,  # ID Number
            14: 200,  # Check-in Time
            15: 200   # ✅ Action - expanded so button isn't cut
        }

        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
            if col in small_cols:
                self.table.setColumnWidth(col, small_cols[col])
            elif col in min_widths:
                self.table.setColumnWidth(col, min_widths[col])

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh_data()

    # ===================================================================
    # DATA REFRESH
    # ===================================================================
    def refresh_data(self):
        try:
            visitors = self.db_manager.get_active_visitors() or []
            self.status_label.setText(f"Total active visitors: {len(visitors)}")
            self.table.setRowCount(0)

            for visitor in visitors:
                self._add_row(visitor)

        except Exception:
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", "Failed to refresh visitor list.")

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
            visitor.get('nric', ''),
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
            visitor.get('id_number', ''),    # ✅ Physical ID Card Number
            visitor.get('check_in_time', '')
        ]

        for col, value in enumerate(data):
            item = QTableWidgetItem(str(value or ""))
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row, col, item)

        # ---------- CHECKOUT BUTTON ----------
        visitor_id = visitor.get("id")

        checkout_btn = QPushButton("Check Out")
        checkout_btn.setCursor(Qt.PointingHandCursor)
        checkout_btn.setIcon(QIcon("assets/icons/logout.png"))
        checkout_btn.setIconSize(QSize(16, 16))
        checkout_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PRIMARY_COLOR};
                color: white;
                border-radius: 6px;
                padding: 10px 18px;  /* ✅ wider so text not clipped */
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {PRIMARY_COLOR}CC; }}
            QPushButton:pressed {{ background: {PRIMARY_COLOR}AA; }}
        """)

        checkout_btn.clicked.connect(
            lambda checked, v_id=visitor_id: self.checkout_visitor(v_id)
        )

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(checkout_btn)
        layout.setAlignment(Qt.AlignCenter)

        self.table.setCellWidget(row, 15, container)

    # ===================================================================
    # CHECKOUT
    # ===================================================================
    def checkout_visitor(self, visitor_id: int):
        reply = QMessageBox.question(
            self,
            "Confirm Checkout",
            "Are you sure you want to check out this visitor?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            if self.db_manager.checkout_visitor(visitor_id):
                QMessageBox.information(self, "Success", "Visitor checked out successfully!")
                self.refresh_data()
                self.visitor_checked_out.emit()
            else:
                QMessageBox.critical(self, "Error", "Checkout failed.")
        except Exception:
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", "An error occurred during checkout.")
