from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QPushButton, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib.patches import Circle
from datetime import datetime
from typing import List, Tuple, Optional, Dict

# Keep your app constants in utils.styles (as before). Example placeholders:
# from utils.styles import DASHBOARD_CARD_STYLE, BUTTON_STYLES, PRIMARY_COLOR

DASHBOARD_CARD_STYLE = """
QFrame { 
    background: #fff; 
    border: 1px solid #e0e0e0; 
    border-radius: 8px; 
    padding: 12px;
}
"""
PRIMARY_COLOR = "#6A1B9A"  # example


class ClickableCard(QFrame):
    """A small reusable card widget which emits clicked() when pressed.
    Subclassing avoids assigning mousePressEvent dynamically (cleaner).
    """

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Allow hover styling via stylesheet if needed
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class DashboardWidget(QWidget):
    active_visitors_clicked = pyqtSignal()

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._init_ui()

    def _init_ui(self):
        # Use a scroll area so the window can be small without cutting off content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        header_label = QLabel("Dashboard")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_label.setStyleSheet(f"color: {PRIMARY_COLOR}; margin: 4px;")
        main_layout.addWidget(header_label)

        # Metrics cards area: use expanding size policies so they distribute space
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)

        self.checkins_card = self._create_metric_card("Today's Check-ins", "0", clickable=True)
        self.checkins_card.clicked.connect(self.on_checkins_clicked)
        metrics_layout.addWidget(self.checkins_card)

        self.active_card = self._create_metric_card("Active Visitors", "0")
        metrics_layout.addWidget(self.active_card)

        self.duration_card = self._create_metric_card("Avg Duration", "0 min")
        metrics_layout.addWidget(self.duration_card)

        main_layout.addLayout(metrics_layout)

        # Charts container - split into two halves
        charts_container = QHBoxLayout()
        charts_container.setSpacing(12)

        # Left chart: Daily Check-ins Bar Chart
        bar_chart_frame = QFrame()
        bar_chart_frame.setStyleSheet(DASHBOARD_CARD_STYLE)
        bar_chart_layout = QVBoxLayout(bar_chart_frame)
        bar_chart_layout.setContentsMargins(8, 8, 8, 8)

        bar_chart_title = QLabel("Daily Check-ins This Month")
        bar_chart_title.setFont(QFont("Arial", 12, QFont.Bold))
        bar_chart_title.setAlignment(Qt.AlignCenter)
        bar_chart_layout.addWidget(bar_chart_title)

        # Bar chart matplotlib canvas
        self.bar_figure = Figure(figsize=(4, 3), dpi=100)
        self.bar_canvas = FigureCanvas(self.bar_figure)
        self.bar_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bar_canvas.updateGeometry()
        bar_chart_layout.addWidget(self.bar_canvas)

        charts_container.addWidget(bar_chart_frame)

        # Right chart: Category Donut Chart
        donut_chart_frame = QFrame()
        donut_chart_frame.setStyleSheet(DASHBOARD_CARD_STYLE)
        donut_chart_layout = QVBoxLayout(donut_chart_frame)
        donut_chart_layout.setContentsMargins(8, 8, 8, 8)

        donut_chart_title = QLabel("Visitors by Category")
        donut_chart_title.setFont(QFont("Arial", 12, QFont.Bold))
        donut_chart_title.setAlignment(Qt.AlignCenter)
        donut_chart_layout.addWidget(donut_chart_title)

        # Donut chart matplotlib canvas
        self.donut_figure = Figure(figsize=(4, 3), dpi=100)
        self.donut_canvas = FigureCanvas(self.donut_figure)
        self.donut_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.donut_canvas.updateGeometry()
        donut_chart_layout.addWidget(self.donut_canvas)

        charts_container.addWidget(donut_chart_frame)

        main_layout.addLayout(charts_container)

        # Keep container inside scroll area
        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(scroll)
        self.setLayout(outer_layout)

        # Initial load
        self.refresh_data()

    def _create_metric_card(self, title: str, value: str, clickable: bool = False) -> QFrame:
        card = ClickableCard() if clickable else QFrame()
        card.setStyleSheet(DASHBOARD_CARD_STYLE)

        # Make cards expand horizontally but keep a reasonable min width
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        card.setMinimumWidth(160)
        card.setMaximumHeight(140)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        title_label.setStyleSheet("color: #666; margin-bottom: 6px;")

        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setFont(QFont("Arial", 22, QFont.Bold))
        value_label.setStyleSheet(f"color: {PRIMARY_COLOR};")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        # store for updates
        card.value_label = value_label
        return card

    def on_checkins_clicked(self):
        # Emit the same external signal; keep naming consistent
        self.active_visitors_clicked.emit()

    def refresh_data(self):
        """Refresh data and immediately redraw UI. Defensive: handle None/empty returns.
        """
        try:
            todays_count = self.db_manager.get_todays_checkin_count() or 0
            active_visitors = self.db_manager.get_active_visitors() or []
            avg_duration = self.db_manager.get_average_duration() or 0
        except Exception as e:
            # In production, log the exception. For now fallback to zeros which keeps UI responsive.
            todays_count = 0
            active_visitors = []
            avg_duration = 0

        self.checkins_card.value_label.setText(str(todays_count))
        self.active_card.value_label.setText(str(len(active_visitors)))

        # Duration formatting
        if avg_duration >= 60:
            hours = int(avg_duration // 60)
            minutes = int(avg_duration % 60)
            duration_text = f"{hours}h {minutes}m"
        else:
            duration_text = f"{int(avg_duration)}m"

        self.duration_card.value_label.setText(duration_text)

        # Update the charts
        self.update_bar_chart()
        self.update_donut_chart()

    def update_bar_chart(self):
        """Update the daily check-ins bar chart."""
        self.bar_figure.clear()

        try:
            daily_data: Optional[List[Tuple[date, int]]] = self.db_manager.get_daily_checkins_current_month()
        except Exception:
            daily_data = None

        ax = self.bar_figure.add_subplot(111)

        if not daily_data:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes, fontsize=10, color='gray')
            ax.set_xticks([])
            self.bar_figure.tight_layout()
            self.bar_canvas.draw()
            return

        # Expecting daily_data as list of tuples (date, count)
        days = [d.day for d, _ in daily_data]
        counts = [c for _, c in daily_data]

        ax.plot(days, counts, marker='o', linewidth=2, markersize=5)
        ax.fill_between(days, counts, alpha=0.3)

        ax.set_title('Daily Check-ins This Month', fontsize=10, fontweight='bold')
        ax.set_xlabel('Day of Month', fontsize=9)
        ax.set_ylabel('Number of Check-ins', fontsize=9)
        ax.grid(True, alpha=0.3)

        # X-axis ticks from 1 to 31 (or up to the max day seen)
        if days:
            max_day = max(days)
            ax.set_xticks(range(1, max_day + 1))

        self.bar_figure.tight_layout()
        self.bar_canvas.draw()

    def update_donut_chart(self):
        """Update the category donut chart."""
        self.donut_figure.clear()

        try:
            category_counts: Dict[str, int] = self.db_manager.get_category_counts()
        except Exception:
            category_counts = {}

        ax = self.donut_figure.add_subplot(111)

        if not category_counts:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes, fontsize=10, color='gray')
            self.donut_figure.tight_layout()
            self.donut_canvas.draw()
            return

        # Prepare data for donut chart
        categories = []
        counts = []
        colors = ['#7C5F7E', '#9d8fa0', '#f0ebf2']  # Primary color variations
        
        # Ensure we have the standard categories
        standard_categories = ['Visitor', 'Vendor', 'Drop-off']
        for cat in standard_categories:
            if cat in category_counts:
                categories.append(cat)
                counts.append(category_counts[cat])
        
        # Add any other categories that might exist
        for cat, count in category_counts.items():
            if cat not in standard_categories:
                categories.append(cat)
                counts.append(count)

        if not counts or sum(counts) == 0:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes, fontsize=10, color='gray')
            self.donut_figure.tight_layout()
            self.donut_canvas.draw()
            return

        # Calculate percentages
        total = sum(counts)
        percentages = [(c / total * 100) for c in counts]

        # Create donut chart
        wedges, texts, autotexts = ax.pie(
            counts,
            labels=categories,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors[:len(categories)],
            pctdistance=0.85,
            textprops={'fontsize': 9}
        )

        # Draw a circle in the center to make it a donut
        centre_circle = Circle((0, 0), 0.70, fc='white')
        ax.add_artist(centre_circle)

        ax.set_title('Visitors by Category', fontsize=10, fontweight='bold', pad=10)

        self.donut_figure.tight_layout()
        self.donut_canvas.draw()


# End of file

