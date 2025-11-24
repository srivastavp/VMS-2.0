from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QHBoxLayout, QLabel, QDateEdit, QMessageBox,
                            QHeaderView, QGroupBox, QFormLayout, QFileDialog, QLineEdit)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
from database import DatabaseManager
from utils.styles import BUTTON_STYLES, PRIMARY_COLOR
import pandas as pd
from datetime import datetime
import logging
import traceback


class AllRecordsWidget(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.filtered_records = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        header_label = QLabel("All Records")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setStyleSheet(f"color: {PRIMARY_COLOR}; margin-bottom: 10px;")
        layout.addWidget(header_label)

        filter_group = QGroupBox("Filter Options")
        filter_layout = QFormLayout()

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())

        calendar_style = """
        QCalendarWidget QWidget {
            color: black;
            background-color: white;
        }
        QCalendarWidget QToolButton {
            color: black;
        }
        QCalendarWidget QMenu {
            background-color: white;
            color: black;
        }
        """
        self.start_date.calendarWidget().setStyleSheet(calendar_style)
        self.end_date.calendarWidget().setStyleSheet(calendar_style)

        filter_layout.addRow("Start Date:", self.start_date)
        filter_layout.addRow("End Date:", self.end_date)

        self.organization_filter = QLineEdit()
        self.hp_no_filter = QLineEdit()
        self.person_visited_filter = QLineEdit()

        filter_layout.addRow("Organization:", self.organization_filter)
        filter_layout.addRow("HP No.:", self.hp_no_filter)
        filter_layout.addRow("Person Visited:", self.person_visited_filter)

        btn_layout = QHBoxLayout()
        self.filter_button = QPushButton("Apply Filter")
        self.filter_button.setStyleSheet(BUTTON_STYLES['primary'])
        self.filter_button.clicked.connect(self.apply_filter)

        self.clear_filter_button = QPushButton("Clear Filter")
        self.clear_filter_button.setStyleSheet(BUTTON_STYLES['warning'])
        self.clear_filter_button.clicked.connect(self.clear_filter)

        self.export_button = QPushButton("Export to Excel")
        self.export_button.setStyleSheet(BUTTON_STYLES['success'])
        self.export_button.clicked.connect(self.export_to_excel)

        btn_layout.addWidget(self.filter_button)
        btn_layout.addWidget(self.clear_filter_button)
        btn_layout.addWidget(self.export_button)

        filter_layout.addRow("", btn_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(17)
        self.table.setHorizontalHeaderLabels([
            "ID", "NRIC", "HP No.", "First Name", "Last Name", "Category", "Purpose",
            "Destination", "Company", "Vehicle No.", "Person Visited", "Remarks",
            "Visit ID", "ID Number", "Check-in Time", "Check-out Time", "Duration"
        ])
        self.table.setColumnHidden(0, True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh_data()

    def apply_filter(self):
        self.refresh_data(
            self.start_date.date().toPyDate(),
            self.end_date.date().toPyDate(),
            self.organization_filter.text().strip(),
            self.hp_no_filter.text().strip(),
            self.person_visited_filter.text().strip()
        )

    def clear_filter(self):
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())
        self.organization_filter.clear()
        self.hp_no_filter.clear()
        self.person_visited_filter.clear()
        self.refresh_data()

    def refresh_data(self, start_date=None, end_date=None, organization=None, hp_no=None, person_visited=None):
        try:
            records = self.db_manager.get_all_records(start_date, end_date)

            if organization:
                records = [r for r in records if organization.lower() in (r.get('company', '').lower())]
            if hp_no:
                records = [r for r in records if hp_no in (r.get('hp_no', ''))]
            if person_visited:
                records = [r for r in records if person_visited.lower() in (r.get('person_visited', '').lower())]

            self.filtered_records = records
            self.status_label.setText(f"Showing {len(records)} records")

            self.table.setRowCount(0)

            cols = [
                'id','nric','hp_no','first_name','last_name','category','purpose',
                'destination','company','vehicle_number','person_visited','remarks',
                'pass_number','id_number','check_in_time','check_out_time','duration'
            ]

            for r in records:
                row = self.table.rowCount()
                self.table.insertRow(row)

                for col, key in enumerate(cols):
                    value = r.get(key, "")

                    # ✅ ONLY CHANGE: Proper duration formatting
                    if key == 'duration':
                        duration = r.get('duration')
                        if duration and duration > 0:
                            hours = duration // 60
                            minutes = duration % 60
                            value = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                        elif r.get('check_out_time'):
                            value = "0m"
                        else:
                            value = "Active"

                    self.table.setItem(row, col, QTableWidgetItem(str(value)))

        except Exception:
            logging.error(traceback.format_exc())

    # ✅ Export remains untouched and correct
    def export_to_excel(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "No records to export!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to Excel",
            f"visitor_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        try:
            data = []
            headers = []

            for col in range(1, self.table.columnCount()):
                header_item = self.table.horizontalHeaderItem(col)
                headers.append(header_item.text() if header_item else "")

            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(1, self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)

            df = pd.DataFrame(data, columns=headers)
            df.to_excel(file_path, index=False, engine="openpyxl")

            QMessageBox.information(self, "Success", f"Records exported successfully to:\n{file_path}")

        except Exception:
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Export Error", "Failed to export records.")
