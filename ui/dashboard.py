from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QPushButton, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Tuple, Optional

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

        # Chart card
        chart_frame = QFrame()
        chart_frame.setStyleSheet(DASHBOARD_CARD_STYLE)
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(8, 8, 8, 8)

        chart_title = QLabel("Daily Check-ins This Month")
        chart_title.setFont(QFont("Arial", 12, QFont.Bold))
        chart_title.setAlignment(Qt.AlignCenter)
        chart_layout.addWidget(chart_title)

        # Matplotlib canvas - make it expand horizontally
        self.figure = Figure(figsize=(8, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        chart_layout.addWidget(self.canvas)

        main_layout.addWidget(chart_frame)

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

        # Update the chart
        self.update_chart()

    def update_chart(self):
        self.figure.clear()

        try:
            daily_data: Optional[List[Tuple[str, int]]] = self.db_manager.get_daily_checkins_current_month()
        except Exception:
            daily_data = None

        ax = self.figure.add_subplot(111)

        if not daily_data:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes, fontsize=12, color='gray')
            ax.set_title('Daily Check-ins This Month')
            ax.set_xticks([])
            self.figure.tight_layout()
            self.canvas.draw()
            return

        # Expecting daily_data as list of tuples (date_string or date, count)
        dates_raw = [d for d, _ in daily_data]
        counts = [c for _, c in daily_data]

        # Normalize date values to datetime objects
        def parse_date(d):
            if isinstance(d, datetime):
                return d
            # try several common formats; adapt to what DB returns
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(d, fmt)
                except Exception:
                    continue
            # fallback: try parsing ISO
            try:
                return datetime.fromisoformat(d)
            except Exception:
                # final fallback to today — keeps plot stable
                return datetime.today()

        dates = [parse_date(d) for d in dates_raw]

        ax.plot(dates, counts, marker='o', linewidth=2, markersize=6)
        ax.fill_between(dates, counts, alpha=0.3)

        ax.set_title('Daily Check-ins This Month', fontsize=12, fontweight='bold')
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Number of Check-ins', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Better date formatting for x-axis
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
        self.figure.autofmt_xdate(rotation=45)

        self.figure.tight_layout()
        self.canvas.draw()


# End of file

