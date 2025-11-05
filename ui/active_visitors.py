from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QHBoxLayout, QLabel, QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import logging
import traceback
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
        
        # Table with all columns
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "ID", "NRIC", "HP No.", "First Name", "Last Name", "Category",
            "Purpose", "Destination", "Company", "Vehicle No.", "Person Visited",
            "Remarks", "Check-in Time", "Action"
        ])
        
        # Hide ID column
        self.table.setColumnHidden(0, True)
        
        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet("background-color: white;")
        
        # Set minimum row height to prevent button overflow
        self.table.verticalHeader().setDefaultSectionSize(55)
        self.table.verticalHeader().setMinimumSectionSize(55)
        
        # Adjust column widths
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
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
        header.setSectionResizeMode(13, QHeaderView.Fixed)  # Action
        self.table.setColumnWidth(13, 130)  # Set fixed width for Action column
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
        # Initial data load
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh active visitors table with proper error handling"""
        try:
            visitors = self.db_manager.get_active_visitors()
            
            # Update status label
            self.status_label.setText(f"Total active visitors: {len(visitors)}")
            
            # Clear table
            self.table.setRowCount(0)
            
            # Populate table
            for visitor in visitors:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Set row height explicitly
                self.table.setRowHeight(row, 55)
                
                # Add all data columns
                self.table.setItem(row, 0, QTableWidgetItem(str(visitor.get('id', ''))))
                self.table.setItem(row, 1, QTableWidgetItem(visitor.get('nric', '') or ''))
                self.table.setItem(row, 2, QTableWidgetItem(visitor.get('hp_no', '') or ''))
                self.table.setItem(row, 3, QTableWidgetItem(visitor.get('first_name', '') or ''))
                self.table.setItem(row, 4, QTableWidgetItem(visitor.get('last_name', '') or ''))
                self.table.setItem(row, 5, QTableWidgetItem(visitor.get('category', '')))
                self.table.setItem(row, 6, QTableWidgetItem(visitor.get('purpose', '') or ''))
                self.table.setItem(row, 7, QTableWidgetItem(visitor.get('destination', '') or ''))
                self.table.setItem(row, 8, QTableWidgetItem(visitor.get('company', '') or ''))
                self.table.setItem(row, 9, QTableWidgetItem(visitor.get('vehicle_number', '') or ''))
                self.table.setItem(row, 10, QTableWidgetItem(visitor.get('person_visited', '') or ''))
                self.table.setItem(row, 11, QTableWidgetItem(visitor.get('remarks', '') or ''))
                self.table.setItem(row, 12, QTableWidgetItem(visitor.get('check_in_time', '')))
                
                # Add checkout button with proper sizing to prevent overflow
                checkout_btn = QPushButton("Check Out")
                checkout_btn.setStyleSheet(BUTTON_STYLES['warning'])
                checkout_btn.setFixedSize(110, 40)  # Fixed size to prevent overflow
                checkout_btn.clicked.connect(lambda checked, v_id=visitor.get('id'): self.checkout_visitor(v_id))
                
                # Center button in cell
                button_widget = QWidget()
                button_widget.setStyleSheet("background-color: transparent;")
                button_layout = QHBoxLayout(button_widget)
                button_layout.addWidget(checkout_btn)
                button_layout.setAlignment(Qt.AlignCenter)
                button_layout.setContentsMargins(5, 5, 5, 5)
                self.table.setCellWidget(row, 13, button_widget)
                
            logging.info(f"Refreshed active visitors table: {len(visitors)} visitors")
        except Exception as e:
            logging.error(f"Error refreshing active visitors: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", "Failed to refresh visitor list. Please try again.")
    
    def checkout_visitor(self, visitor_id: int):
        """Checkout visitor with duration display and robust error handling"""
        # Confirm checkout
        reply = QMessageBox.question(self, 'Confirm Checkout', 
                                   'Are you sure you want to check out this visitor?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                logging.info(f"Checking out visitor ID: {visitor_id}")
                success = self.db_manager.checkout_visitor(visitor_id)
                
                if success:
                    # Get visitor info to show duration
                    from datetime import datetime
                    try:
                        conn = self.db_manager.get_connection()
                        cursor = conn.cursor()
                        cursor.execute('SELECT duration, check_out_time FROM visitors WHERE id = ?', (visitor_id,))
                        result = cursor.fetchone()
                        conn.close()
                        
                        if result and result[0]:
                            duration_minutes = result[0]
                            checkout_time = result[1]
                            hours = duration_minutes // 60
                            minutes = duration_minutes % 60
                            duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                            
                            msg = QMessageBox(self)
                            msg.setIcon(QMessageBox.Information)
                            msg.setWindowTitle("Success")
                            msg.setText("✓ Visitor checked out successfully!")
                            msg.setInformativeText(f"Duration: {duration_str}\nCheck-out Time: {checkout_time}")
                            msg.setStandardButtons(QMessageBox.Ok)
                            msg.exec_()
                            
                            logging.info(f"Visitor {visitor_id} checked out - Duration: {duration_str}")
                        else:
                            QMessageBox.information(self, "Success", "Visitor checked out successfully!")
                    except Exception as e:
                        logging.warning(f"Could not retrieve duration info: {e}")
                        QMessageBox.information(self, "Success", "Visitor checked out successfully!")
                    
                    self.refresh_data()
                    self.visitor_checked_out.emit()
                else:
                    logging.error(f"Failed to checkout visitor {visitor_id} - DB returned False")
                    QMessageBox.critical(self, "Error", "Failed to check out visitor. Please try again.")
            except Exception as e:
                logging.error(f"Error checking out visitor: {traceback.format_exc()}")
                QMessageBox.critical(self, "Error", f"An error occurred during checkout:\n{str(e)}")
