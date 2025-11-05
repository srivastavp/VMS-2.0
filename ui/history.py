from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QHBoxLayout, QLabel, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
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
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet(BUTTON_STYLES['primary'])
        self.refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 10pt; margin: 10px 0;")
        layout.addWidget(self.status_label)
        
        # Table with all columns
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "NRIC", "HP No.", "First Name", "Last Name", "Category", "Purpose",
            "Destination", "Company", "Vehicle No.", "Person Visited", "Remarks",
            "Check-in Time", "Check-out Time", "Duration"
        ])
        
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
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # NRIC
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # HP No
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # First Name
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Last Name
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Category
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Purpose
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Destination
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Company
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Vehicle No
        header.setSectionResizeMode(9, QHeaderView.Stretch)  # Person Visited
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents)  # Remarks
        header.setSectionResizeMode(11, QHeaderView.ResizeToContents)  # Check-in Time
        header.setSectionResizeMode(12, QHeaderView.ResizeToContents)  # Check-out Time
        header.setSectionResizeMode(13, QHeaderView.ResizeToContents)  # Duration
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
        # Initial data load
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh today's history with proper error handling"""
        try:
            history = self.db_manager.get_todays_history()
            
            # Update status label
            checked_out = len([h for h in history if h.get('check_out_time')])
            self.status_label.setText(f"Total visitors today: {len(history)} | Checked out: {checked_out}")
            
            # Clear table
            self.table.setRowCount(0)
            
            # Populate table
            for record in history:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Add all data columns
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
                self.table.setItem(row, 10, QTableWidgetItem(record.get('remarks', '') or ''))
                self.table.setItem(row, 11, QTableWidgetItem(record.get('check_in_time', '')))
                
                # Check-out time - show "Still Active" if not checked out
                checkout_time = record.get('check_out_time', '') if record.get('check_out_time') else 'Still Active'
                self.table.setItem(row, 12, QTableWidgetItem(checkout_time))
                
                # Duration - properly formatted or "Active" if still checked in
                duration = record.get('duration')
                if duration and duration > 0:
                    hours = duration // 60
                    minutes = duration % 60
                    duration_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                elif record.get('check_out_time'):
                    # Checked out but duration is 0 or None
                    duration_text = "0m"
                else:
                    # Still active
                    duration_text = 'Active'
                
                self.table.setItem(row, 13, QTableWidgetItem(duration_text))
                
                # Style row based on status
                if record.get('check_out_time'):
                    for col in range(14):
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(Qt.white)
                else:
                    for col in range(14):
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(Qt.lightGray)
            
            logging.info(f"Refreshed history table: {len(history)} records")
        except Exception as e:
            logging.error(f"Error refreshing history: {traceback.format_exc()}")
