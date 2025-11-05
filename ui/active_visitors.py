from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QHBoxLayout, QLabel, QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from database import DatabaseManager
from utils.styles import BUTTON_STYLES, PRIMARY_COLOR

class ActiveVisitorsWidget(QWidget):
    visitor_checked_out = pyqtSignal()
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        header_label = QLabel("Active Visitors")
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
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Category", "NRIC", "HP No.", "Pass", 
            "Destination", "Check-in Time", "Person Visited", "Action"
        ])
        
        # Hide ID column
        self.table.setColumnHidden(0, True)
        
        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        
        # Adjust column widths
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Category
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # NRIC
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # HP No.
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Pass
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Destination
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Check-in Time
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # Person Visited
        header.setSectionResizeMode(9, QHeaderView.Fixed)  # Action - Fixed width for button visibility
        self.table.setColumnWidth(9, 120)  # Set fixed width for Action column
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
        # Initial data load
        self.refresh_data()
    
    def refresh_data(self):
        visitors = self.db_manager.get_active_visitors()
        
        # Update status label
        self.status_label.setText(f"Total active visitors: {len(visitors)}")
        
        # Clear table
        self.table.setRowCount(0)
        
        # Populate table
        for visitor in visitors:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Add data (with backward compatibility)
            self.table.setItem(row, 0, QTableWidgetItem(str(visitor.get('id', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(visitor.get('name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(visitor.get('category', '')))
            self.table.setItem(row, 3, QTableWidgetItem(visitor.get('nric', '') or ''))
            self.table.setItem(row, 4, QTableWidgetItem(visitor.get('hp_no', '') or ''))
            self.table.setItem(row, 5, QTableWidgetItem(visitor.get('pass_number', '') or ''))
            self.table.setItem(row, 6, QTableWidgetItem(visitor.get('destination', '') or ''))
            self.table.setItem(row, 7, QTableWidgetItem(visitor.get('check_in_time', '')))
            self.table.setItem(row, 8, QTableWidgetItem(visitor.get('person_visited', '')))
            
            # Add checkout button with proper sizing for visibility
            checkout_btn = QPushButton("Check Out")
            checkout_btn.setStyleSheet(BUTTON_STYLES['warning'] + """
                QPushButton {
                    padding: 8px 16px;
                    min-width: 100px;
                    min-height: 30px;
                    white-space: nowrap;
                    font-size: 9pt;
                }
            """)
            checkout_btn.clicked.connect(lambda checked, v_id=visitor.get('id'): self.checkout_visitor(v_id))
            self.table.setCellWidget(row, 9, checkout_btn)
    
    def checkout_visitor(self, visitor_id: int):
        # Confirm checkout
        reply = QMessageBox.question(self, 'Confirm Checkout', 
                                   'Are you sure you want to check out this visitor?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success = self.db_manager.checkout_visitor(visitor_id)
            
            if success:
                QMessageBox.information(self, "Success", "Visitor checked out successfully!")
                self.refresh_data()
                self.visitor_checked_out.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to check out visitor. Please try again.")