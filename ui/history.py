from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QHBoxLayout, QLabel, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from database import DatabaseManager
from utils.styles import BUTTON_STYLES

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
        header_label.setStyleSheet("color: #2196F3;")
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
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name", "Vehicle", "Organization", "Purpose", 
            "Check-in Time", "Check-out Time", "Duration"
        ])
        
        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        
        # Adjust column widths
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Vehicle
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Organization
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Purpose
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Check-in Time
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Check-out Time
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Duration
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
        # Initial data load
        self.refresh_data()
    
    def refresh_data(self):
        history = self.db_manager.get_todays_history()
        
        # Update status label
        checked_out = len([h for h in history if h['check_out_time']])
        self.status_label.setText(f"Total visitors today: {len(history)} | Checked out: {checked_out}")
        
        # Clear table
        self.table.setRowCount(0)
        
        # Populate table
        for record in history:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Add data
            self.table.setItem(row, 0, QTableWidgetItem(record['name']))
            self.table.setItem(row, 1, QTableWidgetItem(record['vehicle_number'] or ''))
            self.table.setItem(row, 2, QTableWidgetItem(record['organization'] or ''))
            self.table.setItem(row, 3, QTableWidgetItem(record['purpose']))
            self.table.setItem(row, 4, QTableWidgetItem(record['check_in_time']))
            
            # Check-out time
            checkout_time = record['check_out_time'] if record['check_out_time'] else 'Still Active'
            self.table.setItem(row, 5, QTableWidgetItem(checkout_time))
            
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
            
            self.table.setItem(row, 6, QTableWidgetItem(duration_text))
            
            # Style row based on status
            if record['check_out_time']:
                for col in range(7):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(Qt.white)
            else:
                for col in range(7):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(Qt.lightGray)