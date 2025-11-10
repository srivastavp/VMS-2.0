from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLabel, QMessageBox, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize     # <-- QSize belongs here
from PyQt5.QtGui import QFont, QIcon              # <-- Removed QSize from here
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
        self.refresh_button.setStyleSheet(f"""
            QPushButton {{
                background: {PRIMARY_COLOR};
                color: white;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {PRIMARY_COLOR}CC;
            }}
            QPushButton:pressed {{
                background: {PRIMARY_COLOR}AA;
            }}
        """)
        self.refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666; font-size: 10pt; margin: 10px 0;")
        layout.addWidget(self.status_label)
        
        # Table with all columns
        self.table = QTableWidget()
        self.table.setColumnCount(15)
        self.table.setHorizontalHeaderLabels([
            "ID", "NRIC", "HP No.", "First Name", "Last Name", "Category",
            "Purpose", "Destination", "Company", "Vehicle No.", "Person Visited",
            "Remarks", "Check-in Time", "Pass No.", "Action"
        ])
        
        # Hide ID column
        self.table.setColumnHidden(0, True)
        
        # Table aesthetics
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet("background-color: white;")
        
        # Minimum row height for icon button comfort
        self.table.verticalHeader().setDefaultSectionSize(58)
        self.table.verticalHeader().setMinimumSectionSize(58)
        
        # Column sizing logic
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        header.setSectionResizeMode(10, QHeaderView.Stretch)
        self.table.setColumnWidth(13, 140)  # Action column stays consistent
        
        layout.addWidget(self.table)
        self.setLayout(layout)
        
        self.refresh_data()
    
    def refresh_data(self):
        try:
            visitors = self.db_manager.get_active_visitors()
            self.status_label.setText(f"Total active visitors: {len(visitors)}")
            self.table.setRowCount(0)
            
            for visitor in visitors:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setRowHeight(row, 58)

                # Fill columns
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
                self.table.setItem(row, 12, QTableWidgetItem(visitor.get('pass_number', '') or ''))
                self.table.setItem(row, 13, QTableWidgetItem(visitor.get('check_in_time', '')))

                # ✅ New modern Check Out button (auto-resize + icon)
                checkout_btn = QPushButton("   Check Out")
                checkout_btn.setIcon(QIcon("assets/icons/logout.png"))  # ensure icon file exists
                checkout_btn.setIconSize(QSize(18, 18))
                
                checkout_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {PRIMARY_COLOR};
                        color: white;
                        border-radius: 6px;
                        padding: 8px 14px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background: {PRIMARY_COLOR}CC;
                    }}
                    QPushButton:pressed {{
                        background: {PRIMARY_COLOR}AA;
                    }}
                """)
                checkout_btn.setMinimumHeight(38)
                checkout_btn.setCursor(Qt.PointingHandCursor)

                checkout_btn.clicked.connect(lambda checked, v_id=visitor.get('id'): self.checkout_visitor(v_id))

                container = QWidget()
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(4, 4, 4, 4)
                container_layout.setAlignment(Qt.AlignCenter)
                container_layout.addWidget(checkout_btn)
                self.table.setCellWidget(row, 13, container)
            
            logging.info(f"Refreshed active visitors: {len(visitors)}")
        except Exception:
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", "Failed to refresh visitor list.")
    
    def checkout_visitor(self, visitor_id: int):
        reply = QMessageBox.question(self, 'Confirm Checkout',
                                     'Are you sure you want to check out this visitor?',
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        try:
            success = self.db_manager.checkout_visitor(visitor_id)
            if success:
                QMessageBox.information(self, "Success", "Visitor checked out successfully!")
                self.refresh_data()
                self.visitor_checked_out.emit()
            else:
                QMessageBox.critical(self, "Error", "Checkout failed.")
        except Exception:
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", "An error occurred during checkout.")
