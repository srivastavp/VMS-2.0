"""
Modern styling for M-Neon VMS
"""

# Primary brand color
PRIMARY_COLOR = "#7C5F7E"
PRIMARY_HOVER = "#8d6f8f"
PRIMARY_PRESSED = "#6b4f6d"
PRIMARY_LIGHT = "#9d8fa0"
PRIMARY_LIGHTEST = "#f0ebf2"

MAIN_STYLE = f"""
QMainWindow {{
    background-color: #f5f5f5;
}}

QWidget {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 9pt;
}}

/* ---------------------------------
   GLOBAL BUTTON FIX FOR MESSAGEBOX
   --------------------------------- */
QMessageBox QPushButton {{
    background-color: {PRIMARY_COLOR};
    color: white;
    padding: 8px 18px;
    min-width: 80px;
    border-radius: 4px;
    font-weight: bold;
}}
QMessageBox QPushButton:hover {{
    background-color: {PRIMARY_HOVER};
}}
QMessageBox QPushButton:pressed {{
    background-color: {PRIMARY_PRESSED};
}}

/* --------------------------------- */

QTabWidget::pane {{
    border: 1px solid #ddd;
    background-color: white;
}}

QTabWidget::tab-bar {{
    alignment: left;
}}

QTabBar::tab {{
    background-color: #e0e0e0;
    border: 1px solid #ccc;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}

QTabBar::tab:selected {{
    background-color: {PRIMARY_COLOR};
    color: white;
}}

QTabBar::tab:hover {{
    background-color: {PRIMARY_LIGHT};
    color: white;
}}

QPushButton {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    font-weight: bold;
    min-width: 80px;
    white-space: nowrap;
}}

QPushButton:hover {{
    background-color: {PRIMARY_HOVER};
}}

QPushButton:pressed {{
    background-color: {PRIMARY_PRESSED};
}}

QPushButton:disabled {{
    background-color: #ccc;
    color: #666;
}}

QLineEdit {{
    border: 2px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    font-size: 9pt;
}}

QLineEdit:focus {{
    border-color: {PRIMARY_COLOR};
}}

QTextEdit {{
    border: 2px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    font-size: 9pt;
}}

QTextEdit:focus {{
    border-color: {PRIMARY_COLOR};
}}

QLabel {{
    color: #333;
    font-weight: bold;
}}

QTableWidget {{
    gridline-color: #e0e0e0;
    background-color: white;
    alternate-background-color: #f9f9f9;
}}

QTableWidget::item {{
    padding: 6px;
    border-bottom: 1px solid #e0e0e0;
}}

QTableWidget::item:selected {{
    background-color: {PRIMARY_LIGHTEST};
    color: {PRIMARY_PRESSED};
}}

QHeaderView::section {{
    background-color: {PRIMARY_COLOR};
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}}

QGroupBox {{
    font-weight: bold;
    border: 2px solid #ddd;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: {PRIMARY_COLOR};
}}

QDateEdit {{
    border: 2px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    font-size: 9pt;
}}

QDateEdit:focus {{
    border-color: {PRIMARY_COLOR};
}}

QComboBox {{
    border: 2px solid #ddd;
    border-radius: 4px;
    padding: 6px;
    font-size: 9pt;
}}

QComboBox:focus {{
    border-color: {PRIMARY_COLOR};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #666;
    margin-top: 2px;
}}

QStatusBar {{
    background-color: {PRIMARY_COLOR};
    color: white;
    font-weight: bold;
}}
"""

DASHBOARD_CARD_STYLE = f"""
QFrame {{
    background-color: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 16px;
}}

QFrame:hover {{
    border-color: {PRIMARY_COLOR};
    box-shadow: 0 4px 8px rgba(68, 27, 72, 0.2);
}}
"""

BUTTON_STYLES = {
    'primary': f"""
        QPushButton {{
            background-color: {PRIMARY_COLOR};
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11pt;
            min-width: 100px;
            min-height: 42px;
        }}
        QPushButton:hover {{
            background-color: {PRIMARY_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {PRIMARY_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: #ccc;
            color: #666;
        }}
    """,
    'success': """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11pt;
            min-width: 100px;
            min-height: 42px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:disabled {
            background-color: #ccc;
            color: #666;
        }
    """,
    'warning': """
        QPushButton {
            background-color: #ff9800;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11pt;
            min-width: 100px;
            min-height: 42px;
        }
        QPushButton:hover {
            background-color: #f57c00;
        }
        QPushButton:disabled {
            background-color: #ccc;
            color: #666;
        }
    """,
    'danger': """
        QPushButton {
            background-color: #f44336;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11pt;
            min-width: 100px;
            min-height: 42px;
        }
        QPushButton:hover {
           	background-color: #d32f2f;
        }
        QPushButton:disabled {
            background-color: #ccc;
            color: #666;
        }
    """
}
