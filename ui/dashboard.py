from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QFrame, QGridLayout, QPushButton, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QPainter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from database import DatabaseManager
from utils.styles import DASHBOARD_CARD_STYLE, BUTTON_STYLES, PRIMARY_COLOR

class DashboardWidget(QWidget):
    active_visitors_clicked = pyqtSignal()
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("Dashboard")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setStyleSheet(f"color: {PRIMARY_COLOR}; margin: 20px;")
        layout.addWidget(header_label)
        
        # Metrics cards
        metrics_layout = QHBoxLayout()
        
        # Today's check-ins card (clickable)
        self.checkins_card = self.create_metric_card("Today's Check-ins", "0", True)
        self.checkins_card.mousePressEvent = self.on_checkins_clicked
        metrics_layout.addWidget(self.checkins_card)
        
        # Active visitors card
        self.active_card = self.create_metric_card("Active Visitors", "0", False)
        metrics_layout.addWidget(self.active_card)
        
        # Average duration card
        self.duration_card = self.create_metric_card("Avg Duration", "0 min", False)
        metrics_layout.addWidget(self.duration_card)
        
        layout.addLayout(metrics_layout)
        
        # Chart section
        chart_frame = QFrame()
        chart_frame.setStyleSheet(DASHBOARD_CARD_STYLE)
        chart_layout = QVBoxLayout(chart_frame)
        
        chart_title = QLabel("Daily Check-ins This Month")
        chart_title.setFont(QFont("Arial", 12, QFont.Bold))
        chart_title.setAlignment(Qt.AlignCenter)
        chart_layout.addWidget(chart_title)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        layout.addWidget(chart_frame)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Initial data load
        self.refresh_data()
    
    def create_metric_card(self, title: str, value: str, clickable: bool = False) -> QFrame:
        card = QFrame()
        card_style = DASHBOARD_CARD_STYLE
        
        if clickable:
            card_style += f"""
                QFrame:hover {{
                    border-color: {PRIMARY_COLOR};
                    background-color: #e8dde9;
                    cursor: pointer;
                }}
            """
        
        card.setStyleSheet(card_style)
        card.setMinimumHeight(100)
        
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        title_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setFont(QFont("Arial", 24, QFont.Bold))
        value_label.setStyleSheet(f"color: {PRIMARY_COLOR};")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        # Store value label for updates
        setattr(card, 'value_label', value_label)
        
        return card
    
    def on_checkins_clicked(self, event):
        self.active_visitors_clicked.emit()
    
    def refresh_data(self):
        # Update metrics
        todays_count = self.db_manager.get_todays_checkin_count()
        active_count = len(self.db_manager.get_active_visitors())
        avg_duration = self.db_manager.get_average_duration()
        
        # Update cards
        self.checkins_card.value_label.setText(str(todays_count))
        self.active_card.value_label.setText(str(active_count))
        
        # Format duration
        if avg_duration > 60:
            hours = int(avg_duration // 60)
            minutes = int(avg_duration % 60)
            duration_text = f"{hours}h {minutes}m"
        else:
            duration_text = f"{int(avg_duration)}m"
        
        self.duration_card.value_label.setText(duration_text)
        
        # Update chart
        self.update_chart()
    
    def update_chart(self):
        self.figure.clear()
        
        # Get data
        daily_data = self.db_manager.get_daily_checkins_current_month()
        
        if not daily_data:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12, color='gray')
            ax.set_title('Daily Check-ins This Month')
            self.canvas.draw()
            return
        
        # Prepare data for plotting
        dates = [item[0] for item in daily_data]
        counts = [item[1] for item in daily_data]
        
        # Create plot
        ax = self.figure.add_subplot(111)
        ax.plot(dates, counts, marker='o', linewidth=2, markersize=6, 
               color=PRIMARY_COLOR, markerfacecolor=PRIMARY_COLOR)
        ax.fill_between(dates, counts, alpha=0.3, color=PRIMARY_COLOR)
        
        # Styling
        ax.set_title('Daily Check-ins This Month', fontsize=12, fontweight='bold')
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Number of Check-ins', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.tick_params(axis='x', rotation=45)
        
        # Adjust layout
        self.figure.tight_layout()
        
        # Refresh canvas
        self.canvas.draw()