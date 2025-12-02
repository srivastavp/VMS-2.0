from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QHBoxLayout, QLabel, QDateEdit,
                            QHeaderView, QGroupBox, QFormLayout, QFileDialog, QLineEdit,
                            QDialog, QMessageBox)
from PyQt5.QtCore import Qt, QDate, QSize, QRegularExpression
from PyQt5.QtGui import QFont, QIcon, QRegularExpressionValidator
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

        # Blacklist button
        self.blacklist_button = QPushButton("Blacklist")
        self.blacklist_button.setStyleSheet(BUTTON_STYLES['danger'] if 'danger' in BUTTON_STYLES else BUTTON_STYLES['warning'])
        self.blacklist_button.clicked.connect(self.open_blacklist_dialog)

        btn_layout.addWidget(self.filter_button)
        btn_layout.addWidget(self.clear_filter_button)
        btn_layout.addWidget(self.export_button)
        btn_layout.addWidget(self.blacklist_button)

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
            "Visit ID", "Pass Number", "Check-in Time", "Check-out Time", "Duration"
        ])
        self.table.setColumnHidden(0, True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

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
            msg = QMessageBox(QMessageBox.Warning, "No Data", "No records to export!", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
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

            msg = QMessageBox(QMessageBox.Information, "Success", f"Records exported successfully to:\n{file_path}", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()

        except Exception:
            logging.error(traceback.format_exc())
            msg = QMessageBox(QMessageBox.Critical, "Export Error", "Failed to export records.", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()

    def open_blacklist_dialog(self):
        dlg = BlacklistDialog(self.db_manager, self)
        dlg.exec_()


class BlacklistDialog(QDialog):
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Blacklist")
        self.setMinimumSize(700, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)

        header = QLabel("Blacklisted HP Numbers")
        header.setFont(QFont("Arial", 14, QFont.Bold))
        header.setStyleSheet(f"color: {PRIMARY_COLOR}; margin-bottom: 8px;")
        layout.addWidget(header)

        # Add row
        add_row = QHBoxLayout()
        self.hp_input = QLineEdit()
        self.hp_input.setPlaceholderText("Enter HP No. to blacklist")
        # HP No: allow digits, '+' and '-' of any length (consistent with registration)
        hp_validator = QRegularExpressionValidator(QRegularExpression(r"^[0-9+\-]*$"), self)
        self.hp_input.setValidator(hp_validator)
        add_btn = QPushButton("Add")
        add_btn.setStyleSheet(BUTTON_STYLES['warning'])
        add_btn.clicked.connect(self.add_hp)
        add_row.addWidget(self.hp_input)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        # Table of existing blacklist
        self.table = QTableWidget()
        # HP, Name, NRIC, Created At, Action
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "HP No.", "Name", "NRIC", "Created At", "Action"
        ])
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeToContents)
        header_view.setStretchLastSection(False)

        # Make rows and the action column large enough for the pill button
        self.table.verticalHeader().setDefaultSectionSize(34)
        # Slightly wider action column so the button is not clipped horizontally
        self.table.setColumnWidth(4, 70)
        layout.addWidget(self.table)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(BUTTON_STYLES['primary'])
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

        self.refresh_table()

    def refresh_table(self):
        entries = self.db_manager.get_blacklist() or []
        self.table.setRowCount(0)
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            hp_no = entry.get("hp_no", "")
            self.table.setItem(row, 0, QTableWidgetItem(hp_no))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(entry.get("nric", "")))
            self.table.setItem(row, 3, QTableWidgetItem(str(entry.get("created_at", ""))))

            # Action cell: whitelist button
            btn = QPushButton()
            btn.setToolTip("Whitelist")
            icon = QIcon("assets/arrow.ico")
            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(14, 14))
            else:
                btn.setText("Whitelist")

            # Make the button compact and visually aligned with the theme
            btn.setFixedSize(26, 26)
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #f3edf7;
                    border-radius: 13px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #e4d8f0;
                }
                QPushButton:pressed {
                    background-color: #d6c5e4;
                }
                """
            )

            btn.clicked.connect(lambda _checked, hp=hp_no: self.whitelist_hp(hp))

            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.setAlignment(Qt.AlignCenter)
            h.addWidget(btn)
            self.table.setCellWidget(row, 4, container)

    def add_hp(self):
        hp = self.hp_input.text().strip()
        if not hp:
            msg = QMessageBox(QMessageBox.Warning, "Missing", "Please enter an HP No.", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
            return

        # If already blacklisted, inform and refresh
        if self.db_manager.is_hp_blacklisted(hp):
            msg = QMessageBox(QMessageBox.Information, "Already Blacklisted", "This HP No. is already blacklisted.", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
            self.refresh_table()
            return

        if not self.db_manager.add_to_blacklist_from_visit(hp):
            msg = QMessageBox(QMessageBox.Warning, "Not Found", "No past visit found for this HP No.", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
            return

        msg = QMessageBox(QMessageBox.Information, "Added", "HP No. has been added to blacklist.", QMessageBox.Ok, self)
        msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        msg.exec_()
        self.hp_input.clear()
        self.refresh_table()

    def whitelist_hp(self, hp_no: str):
        if not hp_no:
            return
        msg = QMessageBox(QMessageBox.Question, "Whitelist", f"Remove HP No. {hp_no} from blacklist?", QMessageBox.Yes | QMessageBox.No, self)
        msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        reply = msg.exec_()
        if reply != QMessageBox.Yes:
            return

        if not self.db_manager.remove_from_blacklist(hp_no):
            msg = QMessageBox(QMessageBox.Critical, "Error", "Failed to remove from blacklist.", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            msg.exec_()
            return

        msg = QMessageBox(QMessageBox.Information, "Whitelisted", "HP No. has been removed from blacklist.", QMessageBox.Ok, self)
        msg.setWindowFlags(msg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        msg.exec_()
        self.refresh_table()
