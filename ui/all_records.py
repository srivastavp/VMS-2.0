from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QHBoxLayout, QLabel, QDateEdit, QMessageBox,
                            QHeaderView, QGroupBox, QFormLayout, QFileDialog, QLineEdit, QComboBox)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
from database import DatabaseManager
from utils.styles import BUTTON_STYLES, PRIMARY_COLOR
import pandas as pd
from datetime import datetime, date
import logging
import traceback
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
        header_label.setStyleSheet(f"color: {PRIMARY_COLOR}; margin-bottom: 10px;")
        layout.addWidget(header_label)
        
        # Filters
        filter_group = QGroupBox("Filter Options")
        filter_group.setStyleSheet("background-color: white;")
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
        
        # Organization (Company) filter
        self.organization_filter = QLineEdit()
        self.organization_filter.setPlaceholderText("Enter company/organization name")
        self.organization_filter.setStyleSheet("font-size: 10pt; padding: 6px;")
        filter_layout.addRow("Organization:", self.organization_filter)
        
        # HP No filter
        self.hp_no_filter = QLineEdit()
        self.hp_no_filter.setPlaceholderText("Enter HP number")
        self.hp_no_filter.setStyleSheet("font-size: 10pt; padding: 6px;")
        filter_layout.addRow("HP No.:", self.hp_no_filter)
        
        # Person Visited filter
        self.person_visited_filter = QLineEdit()
        self.person_visited_filter.setPlaceholderText("Enter person visited name")
        self.person_visited_filter.setStyleSheet("font-size: 10pt; padding: 6px;")
        filter_layout.addRow("Person Visited:", self.person_visited_filter)
        
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
        
        # Table with all columns
        self.table = QTableWidget()
        self.table.setColumnCount(15)
        self.table.setHorizontalHeaderLabels([
            "ID", "NRIC", "HP No.", "First Name", "Last Name", "Category", "Purpose",
            "Destination", "Company", "Vehicle No.", "Person Visited", "Remarks",
            "Check-in Time", "Check-out Time", "Duration"
        ])
        
        # Hide ID column
        self.table.setColumnHidden(0, True)
        
        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet("background-color: white;")
        
        # Set row height
        self.table.verticalHeader().setDefaultSectionSize(45)
        
        # Adjust column widths
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # NRIC
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # HP No
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # First Name
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Last Name
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Category
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Purpose
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # Destination
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Company
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Vehicle No
        header.setSectionResizeMode(10, QHeaderView.Stretch)  # Person Visited
        header.setSectionResizeMode(11, QHeaderView.ResizeToContents)  # Remarks
        header.setSectionResizeMode(12, QHeaderView.ResizeToContents)  # Check-in Time
        header.setSectionResizeMode(13, QHeaderView.ResizeToContents)  # Check-out Time
        header.setSectionResizeMode(14, QHeaderView.ResizeToContents)  # Duration
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
        # Initial data load
        self.refresh_data()
    
    def apply_filter(self):
        """Apply filters with date range and optional text filters"""
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        
        if start_date > end_date:
            QMessageBox.warning(self, "Invalid Date Range", "Start date cannot be after end date!")
            return
        
        # Get filter values
        organization = self.organization_filter.text().strip()
        hp_no = self.hp_no_filter.text().strip()
        person_visited = self.person_visited_filter.text().strip()
        
        self.refresh_data(start_date, end_date, organization, hp_no, person_visited)
    
    def clear_filter(self):
        """Clear all filters and reset to default view"""
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())
        self.organization_filter.clear()
        self.hp_no_filter.clear()
        self.person_visited_filter.clear()
        self.refresh_data()
    
    def refresh_data(self, start_date=None, end_date=None, organization=None, hp_no=None, person_visited=None):
        """Refresh records with advanced filtering"""
        try:
            # Get all records within date range
            records = self.db_manager.get_all_records(start_date, end_date)
            
            # Apply additional filters
            if organization:
                records = [r for r in records if r.get('company') and organization.lower() in r.get('company', '').lower()]
            
            if hp_no:
                records = [r for r in records if r.get('hp_no') and hp_no.lower() in r.get('hp_no', '').lower()]
            
            if person_visited:
                records = [r for r in records if r.get('person_visited') and person_visited.lower() in r.get('person_visited', '').lower()]
            
            # Update status label
            filter_info = []
            if start_date and end_date:
                filter_info.append(f"{start_date} to {end_date}")
            if organization:
                filter_info.append(f"Organization: {organization}")
            if hp_no:
                filter_info.append(f"HP No: {hp_no}")
            if person_visited:
                filter_info.append(f"Person Visited: {person_visited}")
            
            if filter_info:
                self.status_label.setText(f"Showing {len(records)} records | Filters: {', '.join(filter_info)}")
            else:
                self.status_label.setText(f"Showing all {len(records)} records")
            
            # Clear table
            self.table.setRowCount(0)
            
            # Populate table
            for record in records:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Add all data columns
                self.table.setItem(row, 0, QTableWidgetItem(str(record.get('id', ''))))
                self.table.setItem(row, 1, QTableWidgetItem(record.get('nric', '') or ''))
                self.table.setItem(row, 2, QTableWidgetItem(record.get('hp_no', '') or ''))
                self.table.setItem(row, 3, QTableWidgetItem(record.get('first_name', '') or ''))
                self.table.setItem(row, 4, QTableWidgetItem(record.get('last_name', '') or ''))
                self.table.setItem(row, 5, QTableWidgetItem(record.get('category', '') or ''))
                self.table.setItem(row, 6, QTableWidgetItem(record.get('purpose', '') or ''))
                self.table.setItem(row, 7, QTableWidgetItem(record.get('destination', '') or ''))
                self.table.setItem(row, 8, QTableWidgetItem(record.get('company', '') or ''))
                self.table.setItem(row, 9, QTableWidgetItem(record.get('vehicle_number', '') or ''))
                self.table.setItem(row, 10, QTableWidgetItem(record.get('person_visited', '') or ''))
                self.table.setItem(row, 11, QTableWidgetItem(record.get('remarks', '') or ''))
                self.table.setItem(row, 12, QTableWidgetItem(record.get('check_in_time', '')))
                
                # Check-out time
                checkout_time = record.get('check_out_time', '') if record.get('check_out_time') else 'Still Active'
                self.table.setItem(row, 13, QTableWidgetItem(checkout_time))
                
                # Duration
                duration = record.get('duration')
                if duration and duration > 0:
                    hours = duration // 60
                    minutes = duration % 60
                    duration_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                elif record.get('check_out_time'):
                    duration_text = "0m"
                else:
                    duration_text = 'Active'
                
                self.table.setItem(row, 14, QTableWidgetItem(duration_text))
            
            logging.info(f"Refreshed all records table: {len(records)} records")
        except Exception as e:
            logging.error(f"Error refreshing all records: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", "Failed to refresh records. Please try again.")
    
    def export_to_excel(self):
        """Export current table view to Excel"""
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
            logging.info(f"Exported {len(data)} records to {file_path}")
            
        except Exception as e:
            logging.error(f"Export error: {traceback.format_exc()}")
            QMessageBox.critical(self, "Export Error", f"Failed to export records:\n{str(e)}")
