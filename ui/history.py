from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import logging
import traceback

from database import DatabaseManager
from utils.styles import BUTTON_STYLES, PRIMARY_COLOR


class HistoryWidget(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()

        header_label = QLabel("Today's History")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setStyleSheet(f"color: {PRIMARY_COLOR};")
        header_layout.addWidget(header_label)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet(BUTTON_STYLES['primary'])
        self.refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_button)

        layout.addLayout(header_layout)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 10pt; margin: 10px 0;")
        layout.addWidget(self.status_label)

        # TABLE
        self.table = QTableWidget()
        self.table.setColumnCount(16)

        self.table.setHorizontalHeaderLabels([
            "NRIC", "HP No.", "First Name", "Last Name", "Category",
            "Purpose", "Destination", "Company", "Vehicle No.", "Person Visited",
            "Remarks",
            "Visit ID",
            "Pass Number",
            "Check-in Time", "Check-out Time", "Duration"
        ])

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet("background-color: white;")
        self.table.verticalHeader().setDefaultSectionSize(45)

        header = self.table.horizontalHeader()
        # Match All Records behavior: interactive default widths, user can drag to resize
        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Interactive)

        # Set some sensible default widths (user can still resize)
        default_widths = {
            0: 120,  # NRIC
            1: 100,  # HP No.
            2: 140,  # First Name
            3: 140,  # Last Name
            4: 120,  # Category
            5: 160,  # Purpose
            6: 160,  # Destination
            7: 150,  # Company
            8: 130,  # Vehicle No.
            9: 150,  # Person Visited
            10: 220, # Remarks
            11: 140, # Visit ID
            12: 140, # Pass Number
            13: 180, # Check-in Time
            14: 180, # Check-out Time
            15: 120, # Duration
        }
        for col, width in default_widths.items():
            self.table.setColumnWidth(col, width)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def refresh_data(self):
        try:
            history = self.db_manager.get_todays_history()

            checked_out = len([h for h in history if h.get('check_out_time')])
            self.status_label.setText(
                f"Total visitors today: {len(history)} | Checked out: {checked_out}"
            )

            self.table.setRowCount(0)

            for record in history:
                row = self.table.rowCount()
                self.table.insertRow(row)

                self.table.setItem(row, 0, QTableWidgetItem(record.get('nric', '') or ''))
                self.table.setItem(row, 1, QTableWidgetItem(record.get('hp_no', '') or ''))
                self.table.setItem(row, 2, QTableWidgetItem(record.get('first_name', '') or ''))
                self.table.setItem(row, 3, QTableWidgetItem(record.get('last_name', '') or ''))
                self.table.setItem(row, 4, QTableWidgetItem(record.get('category', '') or ''))
                self.table.setItem(row, 5, QTableWidgetItem(record.get('purpose', '') or ''))
                self.table.setItem(row, 6, QTableWidgetItem(record.get('destination', '') or ''))
                self.table.setItem(row, 7, QTableWidgetItem(record.get('company', '') or ''))
                self.table.setItem(row, 8, QTableWidgetItem(record.get('vehicle_number', '') or ''))
                self.table.setItem(row, 9, QTableWidgetItem(record.get('person_visited', '') or ''))

                # REMARKS
                self.table.setItem(row, 10, QTableWidgetItem(record.get('remarks', '') or ''))

                # VISIT ID (mapped from pass_number)
                self.table.setItem(row, 11, QTableWidgetItem(record.get('pass_number', '') or ''))

                # PASS NUMBER
                self.table.setItem(row, 12, QTableWidgetItem(record.get('id_number', '') or ''))

                self.table.setItem(row, 13, QTableWidgetItem(record.get('check_in_time', '') or ''))

                checkout_time = record.get('check_out_time') or 'Still Active'
                self.table.setItem(row, 14, QTableWidgetItem(checkout_time))

                duration = record.get('duration')
                if duration and duration > 0:
                    hours = duration // 60
                    minutes = duration % 60
                    duration_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                elif record.get('check_out_time'):
                    duration_text = "0m"
                else:
                    duration_text = "Active"

                self.table.setItem(row, 15, QTableWidgetItem(duration_text))

            logging.info(f"Refreshed history table: {len(history)} records")

        except Exception:
            logging.error(traceback.format_exc())
