from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QHBoxLayout, QLabel, QDateEdit, QMessageBox,
                            QHeaderView, QGroupBox, QFormLayout, QFileDialog)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
from database import DatabaseManager
from utils.styles import BUTTON_STYLES
import pandas as pd
from datetime import datetime, date
import os

class AllRecordsWidget(QWidget):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("All Records")
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setStyleSheet("color: #2196F3; margin-bottom: 10px;")
        layout.addWidget(header_label)
        
        # Filters
        filter_group = QGroupBox("Filter Options")
        filter_layout = QFormLayout()
        
        # Date range filters
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        filter_layout.addRow("Start Date:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        filter_layout.addRow("End Date:", self.end_date)
        
        # Filter buttons
        button_layout = QHBoxLayout()
        
        self.filter_button = QPushButton("Apply Filter")
        self.filter_button.setStyleSheet(BUTTON_STYLES['primary'])
        self.filter_button.clicked.connect(self.apply_filter)
        button_layout.addWidget(self.filter_button)
        
        self.clear_filter_button = QPushButton("Clear Filter")
        self.clear_filter_button.setStyleSheet(BUTTON_STYLES['warning'])
        self.clear_filter_button.clicked.connect(self.clear_filter)
        button_layout.addWidget(self.clear_filter_button)
        
        self.export_button = QPushButton("Export to Excel")
        self.export_button.setStyleSheet(BUTTON_STYLES['success'])
        self.export_button.clicked.connect(self.export_to_excel)
        button_layout.addWidget(self.export_button)
        
        filter_layout.addRow("", button_layout)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 10pt; margin: 10px 0;")
        layout.addWidget(self.status_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Vehicle", "Organization", "Person Visited",
            "Purpose", "Check-in Time", "Check-out Time", "Duration"
        ])
        
        # Hide ID column
        self.table.setColumnHidden(0, True)
        
        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        
        # Adjust column widths
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Vehicle
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Organization
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Person Visited
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Purpose
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Check-in Time
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Check-out Time
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Duration
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
        # Initial data load
        self.refresh_data()
    
    def apply_filter(self):
        start_date = self.start_date.date().toPython()
        end_date = self.end_date.date().toPython()
        
        if start_date > end_date:
            QMessageBox.warning(self, "Invalid Date Range", "Start date cannot be after end date!")
            return
        
        self.refresh_data(start_date, end_date)
    
    def clear_filter(self):
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())
        self.refresh_data()
    
    def refresh_data(self, start_date=None, end_date=None):
        records = self.db_manager.get_all_records(start_date, end_date)
        
        # Update status label
        if start_date and end_date:
            self.status_label.setText(f"Showing {len(records)} records from {start_date} to {end_date}")
        else:
            self.status_label.setText(f"Showing all {len(records)} records")
        
        # Clear table
        self.table.setRowCount(0)
        
        # Populate table
        for record in records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Add data
            self.table.setItem(row, 0, QTableWidgetItem(str(record['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(record['name']))
            self.table.setItem(row, 2, QTableWidgetItem(record['vehicle_number'] or ''))
            self.table.setItem(row, 3, QTableWidgetItem(record['organization'] or ''))
            self.table.setItem(row, 4, QTableWidgetItem(record['person_visited']))
            self.table.setItem(row, 5, QTableWidgetItem(record['purpose']))
            self.table.setItem(row, 6, QTableWidgetItem(record['check_in_time']))
            
            # Check-out time
            checkout_time = record['check_out_time'] if record['check_out_time'] else 'Still Active'
            self.table.setItem(row, 7, QTableWidgetItem(checkout_time))
            
            # Duration
            if record['duration']:
                duration = record['duration']
                if duration > 60:
                    hours = duration // 60
                    minutes = duration % 60
                    duration_text = f"{hours}h {minutes}m"
                else:
                    duration_text = f"{duration}m"
            else:
                duration_text = 'Active'
            
            self.table.setItem(row, 8, QTableWidgetItem(duration_text))
    
    def export_to_excel(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "No Data", "No records to export!")
            return
        
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export to Excel", 
            f"visitor_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            # Prepare data for export
            data = []
            headers = []
            
            # Get headers (excluding ID)
            for col in range(1, self.table.columnCount()):
                headers.append(self.table.horizontalHeaderItem(col).text())
            
            # Get data
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(1, self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else '')
                data.append(row_data)
            
            # Create DataFrame and export
            df = pd.DataFrame(data, columns=headers)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            QMessageBox.information(self, "Success", f"Records exported successfully to:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export records:\n{str(e)}")