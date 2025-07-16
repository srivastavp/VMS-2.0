"""
Modern styling for the Visitor Management System
"""

MAIN_STYLE = """
QMainWindow {
    background-color: #f5f5f5;
}

QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 9pt;
}

QTabWidget::pane {
    border: 1px solid #ddd;
    background-color: white;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar::tab {
    background-color: #e0e0e0;
    border: 1px solid #ccc;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #2196F3;
    color: white;
}

QTabBar::tab:hover {
    background-color: #64B5F6;
    color: white;
}

QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #ccc;
    color: #666;
}

QLineEdit {
    border: 2px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    font-size: 9pt;
}

QLineEdit:focus {
    border-color: #2196F3;
}

QTextEdit {
    border: 2px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    font-size: 9pt;
}

QTextEdit:focus {
    border-color: #2196F3;
}

QLabel {
    color: #333;
    font-weight: bold;
}

QTableWidget {
    gridline-color: #e0e0e0;
    background-color: white;
    alternate-background-color: #f9f9f9;
}

QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #e0e0e0;
}

QTableWidget::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

QHeaderView::section {
    background-color: #2196F3;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}

QGroupBox {
    font-weight: bold;
    border: 2px solid #ddd;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: #2196F3;
}

QDateEdit {
    border: 2px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    font-size: 9pt;
}

QDateEdit:focus {
    border-color: #2196F3;
}

QComboBox {
    border: 2px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    font-size: 9pt;
}

QComboBox:focus {
    border-color: #2196F3;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #666;
    margin-top: 2px;
}

QStatusBar {
    background-color: #2196F3;
    color: white;
    font-weight: bold;
}
"""

DASHBOARD_CARD_STYLE = """
QFrame {
    background-color: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px;
}

QFrame:hover {
    border-color: #2196F3;
    box-shadow: 0 4px 8px rgba(33, 150, 243, 0.2);
}
"""

BUTTON_STYLES = {
    'primary': """
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 9pt;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QPushButton:pressed {
            background-color: #0D47A1;
        }
    """,
    'success': """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 9pt;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
    """,
    'warning': """
        QPushButton {
            background-color: #ff9800;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 9pt;
        }
        QPushButton:hover {
            background-color: #f57c00;
        }
    """,
    'danger': """
        QPushButton {
            background-color: #f44336;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 9pt;
        }
        QPushButton:hover {
            background-color: #d32f2f;
        }
    """
}