# ui/main_window.py

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QLabel,
    QPushButton, QHBoxLayout, QToolBar, QAction, QApplication, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QInputDialog, QComboBox, QToolButton, QMenu, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from pathlib import Path
import json
from datetime import datetime
import sys
import logging

from utils.license import LicenseManager
from database import DatabaseManager
from utils.styles import MAIN_STYLE

from ui.registration import RegistrationWidget
from ui.dashboard import DashboardWidget
from ui.active_visitors import ActiveVisitorsWidget
from ui.history import HistoryWidget
from ui.all_records import AllRecordsWidget


# -------------------------
# Paths & Config
# -------------------------
APP_BASE = Path(__file__).resolve().parents[1]
DATA_DIR = APP_BASE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = DATA_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except:
            return {}
    return {}


def save_config(data: dict):
    try:
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except:
        logging.exception("Failed to save config")


# -------------------------
# Shared Popup Style (A1-C)
# -------------------------
POPUP_BG = """
background-color: #ffffff;
border-radius: 14px;
"""

HEADER_STYLE = """
background: qlineargradient(
    x1:0, y1:0, x2:1, y2:0,
    stop:0 #7C5F7E, stop:1 #9d8fa0
);
color: white;
padding: 18px;
font-size: 18px;
font-weight: bold;
border-top-left-radius: 14px;
border-top-right-radius: 14px;
"""

INPUT_STYLE = """
QLineEdit {
    border: 2px solid #d8cfe0;
    border-radius: 6px;
    padding: 8px;
    font-size: 11pt;
}
QLineEdit:focus {
    border-color: #7C5F7E;
}
"""

BTN_PRIMARY = """
QPushButton {
    background-color: #7C5F7E;
    color: white;
    padding: 10px 24px;
    border-radius: 6px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #8d6f8f;
}
"""

BTN_SECONDARY = """
QPushButton {
    background-color: #f3edf7;
    color: #4a3b4d;
    padding: 10px 24px;
    border-radius: 6px;
}
"""


# ==============================================================
# License Dialog — supports "activate" and "login"
# ==============================================================
class LicenseDialog(QDialog):
    def __init__(self, license_manager: LicenseManager, mode: str = "activate", parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.mode = mode  # activate | login
        self.setModal(True)
        self.setFixedSize(520, 380)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._build_ui()

    def _build_ui(self):
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)

        # Header
        title = "License Activation" if self.mode == "activate" else "Log In"
        header = QLabel(title)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(HEADER_STYLE)
        wrapper.addWidget(header)

        # Body Frame
        body = QFrame()
        body.setStyleSheet(POPUP_BG)
        layout = QFormLayout(body)
        layout.setContentsMargins(30, 30, 30, 30)
        wrapper.addWidget(body)

        # MAC
        device_info = self.license_manager.get_current_device_info()
        mac = device_info.get("mac_address", "")

        mac_row = QHBoxLayout()
        self.mac_display = QLineEdit(mac)
        self.mac_display.setReadOnly(True)
        self.mac_display.setStyleSheet(INPUT_STYLE)
        mac_row.addWidget(self.mac_display)

        copy_btn = QPushButton("Copy")
        copy_btn.setStyleSheet(BTN_SECONDARY)
        copy_btn.clicked.connect(self._copy_mac)
        mac_row.addWidget(copy_btn)

        layout.addRow("MAC Address:", mac_row)

        # Expiry only for activation
        if self.mode == "activate":
            self.expiry_input = QLineEdit()
            self.expiry_input.setPlaceholderText("YYYY-MM-DD")
            self.expiry_input.setStyleSheet(INPUT_STYLE)
            layout.addRow("Expiry Date:", self.expiry_input)

        # License Key
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.license_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("License Key:", self.license_input)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()

        action_label = "Activate" if self.mode == "activate" else "Log In"
        action_btn = QPushButton(action_label)
        action_btn.setStyleSheet(BTN_PRIMARY)
        action_btn.clicked.connect(self._on_action)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(BTN_SECONDARY)
        cancel_btn.clicked.connect(self._on_cancel)

        btns.addWidget(cancel_btn)
        btns.addWidget(action_btn)
        layout.addRow("", btns)

    def _on_cancel(self):
        """Handle cancel button - show confirmation before exiting."""
        reply = QMessageBox.question(
            self, "Exit", "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.reject()
        # If No, do nothing - dialog stays open

    def _copy_mac(self):
        QApplication.clipboard().setText(self.mac_display.text())
        QMessageBox.information(self, "Copied", "MAC address copied to clipboard.")

    def _on_action(self):
        key = self.license_input.text().strip()

        if not key:
            QMessageBox.warning(self, "Missing", "License key is required.")
            return

        if self.mode == "activate":
            expiry = self.expiry_input.text().strip()
            try:
                datetime.strptime(expiry, "%Y-%m-%d")
            except:
                QMessageBox.warning(self, "Invalid", "Expiry must be YYYY-MM-DD.")
                return

            if not self.license_manager.validate_license(key, expiry):
                QMessageBox.warning(self, "Invalid", "Key does not match device + expiry.")
                return

            if not self.license_manager.activate_license(key, expiry):
                QMessageBox.critical(self, "Error", "Failed to save license.")
                return

        else:  # login
            if not self.license_manager.login_with_key(key):
                QMessageBox.warning(self, "Login Failed", "Invalid or expired key.")
                return

        self.accept()

    def closeEvent(self, event):
        """Handle close event - ask for confirmation before exiting."""
        reply = QMessageBox.question(
            self, "Exit", "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


class ProfilesDialog(QDialog):
    def __init__(self, db: DatabaseManager, current_user: dict, plain_password: str, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_user = current_user or {}
        self.current_role = self.current_user.get("role", "user")
        self._plain_password = plain_password or ""
        self._users = []
        self.setModal(True)
        # Slightly wider/taller so long names are clearly visible
        self.setFixedSize(1100, 560)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._build_ui()
        self._load_users()

    def _build_ui(self):
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Profiles")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(HEADER_STYLE)
        wrapper.addWidget(header)

        body = QFrame()
        body.setStyleSheet(POPUP_BG)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(20, 20, 20, 20)
        wrapper.addWidget(body)

        self.table = QTableWidget()
        if self.current_role == "super_admin":
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels([
                "Name", "User ID", "Organization", "Role", "Active", "Actions"
            ])
        else:
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels([
                "Name", "User ID", "Organization", "Role", "Active"
            ])

        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(100)
        if self.current_role == "super_admin":
            # Let the Name column grow based on content so long names are fully visible
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        else:
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        # Make rows tall enough so action buttons are not clipped vertically
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        # Current user's password visibility (in-memory only)
        if self._plain_password:
            pw_row = QHBoxLayout()
            pw_row.setContentsMargins(0, 8, 0, 8)

            pw_label = QLabel("Your Password:")
            pw_label.setMinimumWidth(110)

            self.pw_display = QLineEdit(self._plain_password)
            self.pw_display.setEchoMode(QLineEdit.Password)
            self.pw_display.setReadOnly(True)
            self.pw_display.setStyleSheet(INPUT_STYLE)

            self.pw_toggle = QPushButton("Show")
            self.pw_toggle.setStyleSheet(BTN_SECONDARY)
            self.pw_toggle.setFixedWidth(70)
            self.pw_toggle.clicked.connect(self._toggle_password_visibility)

            pw_row.addWidget(pw_label)
            pw_row.addWidget(self.pw_display)
            pw_row.addWidget(self.pw_toggle)
            layout.addLayout(pw_row)

        btns = QHBoxLayout()
        btns.addStretch()

        if self.current_role == "super_admin":
            create_btn = QPushButton("Create User")
            create_btn.setStyleSheet(BTN_PRIMARY)
            create_btn.clicked.connect(self._on_create_user)
            btns.addWidget(create_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(BTN_SECONDARY)
        close_btn.clicked.connect(self.reject)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

    def _toggle_password_visibility(self):
        if not hasattr(self, "pw_display"):
            return
        if self.pw_display.echoMode() == QLineEdit.Password:
            self.pw_display.setEchoMode(QLineEdit.Normal)
            self.pw_toggle.setText("Hide")
        else:
            self.pw_display.setEchoMode(QLineEdit.Password)
            self.pw_toggle.setText("Show")

    def _load_users(self):
        users = self.db.list_users()
        current_id = self.current_user.get("user_id")

        if self.current_role == "user":
            users = [u for u in users if u.get("user_id") == current_id]

        self._users = users
        self.table.setRowCount(len(users))
        for row_idx, u in enumerate(users):
            self.table.setItem(row_idx, 0, QTableWidgetItem(u.get("name", "")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(u.get("user_id", "")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(u.get("organization", "")))
            self.table.setItem(row_idx, 3, QTableWidgetItem(u.get("role", "")))
            self.table.setItem(
                row_idx,
                4,
                QTableWidgetItem("Active" if u.get("is_active", True) else "Inactive"),
            )

            if self.current_role == "super_admin":
                actions_layout = QHBoxLayout()
                actions_layout.setContentsMargins(0, 0, 0, 0)
                # Increase spacing so buttons are not touching
                actions_layout.setSpacing(8)

                role_btn = QPushButton("Role")
                role_btn.setStyleSheet(BTN_SECONDARY)
                role_btn.clicked.connect(lambda _, r=row_idx: self._on_change_role(r))

                toggle_btn = QPushButton("Toggle")
                toggle_btn.setStyleSheet(BTN_SECONDARY)
                toggle_btn.clicked.connect(lambda _, r=row_idx: self._on_toggle_active(r))

                delete_btn = QPushButton("Delete")
                # Red-themed delete button to indicate destructive action
                delete_btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #e57373;
                        color: white;
                        border-radius: 6px;
                        padding: 6px 10px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #ef5350;
                    }
                    QPushButton:pressed {
                        background-color: #d32f2f;
                    }
                    """
                )
                delete_btn.clicked.connect(lambda _, r=row_idx: self._on_delete_user(r))

                actions_layout.addWidget(role_btn)
                actions_layout.addWidget(toggle_btn)
                actions_layout.addWidget(delete_btn)

                actions_widget = QWidget()
                actions_widget.setLayout(actions_layout)
                self.table.setCellWidget(row_idx, 5, actions_widget)

    def _on_create_user(self):
        dlg = CreateProfileDialog(first_user=False, default_org=self.current_user.get("organization", ""), parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return

        role = dlg.role_input.currentText().strip() or "user"
        if role not in ("super_admin", "super_user", "user"):
            QMessageBox.warning(self, "Invalid", "Role must be super_admin, super_user or user.")
            return

        ok = self.db.create_user(
            name=dlg.name_input.text().strip(),
            organization=dlg.org_input.text().strip(),
            user_id=dlg.user_id_input.text().strip(),
            password_plain=dlg.password_input.text(),
            role=role,
        )
        if not ok:
            QMessageBox.critical(self, "Error", "Failed to create user (maybe duplicate User ID).")
            return

        self._load_users()

    def _on_change_role(self, row: int):
        if row < 0 or row >= len(self._users):
            return
        user = self._users[row]
        if user.get("user_id") == self.current_user.get("user_id"):
            QMessageBox.warning(self, "Not allowed", "You cannot change your own role.")
            return

        roles = ["super_admin", "super_user", "user"]
        current_role = user.get("role", "user")
        try:
            index = roles.index(current_role)
        except ValueError:
            index = 2

        new_role, ok = QInputDialog.getItem(self, "Change Role", "Select new role:", roles, index, False)
        if not ok or not new_role:
            return

        if not self.db.update_user_role(user["id"], new_role):
            QMessageBox.critical(self, "Error", "Failed to update role.")
            return
        self._load_users()

    def _on_toggle_active(self, row: int):
        if row < 0 or row >= len(self._users):
            return
        user = self._users[row]
        new_active = not bool(user.get("is_active", True))
        if not self.db.update_user_active_status(user["id"], new_active):
            QMessageBox.critical(self, "Error", "Failed to update active status.")
            return
        self._load_users()

    def _on_delete_user(self, row: int):
        if row < 0 or row >= len(self._users):
            return
        user = self._users[row]
        if user.get("user_id") == self.current_user.get("user_id"):
            QMessageBox.warning(self, "Not allowed", "You cannot delete your own account.")
            return

        reply = QMessageBox.question(
            self,
            "Delete User",
            f"Are you sure you want to delete user '{user.get('user_id', '')}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        if not self.db.delete_user(user["id"]):
            QMessageBox.critical(self, "Error", "Failed to delete user.")
            return
        self._load_users()


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setFixedSize(520, 320)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._build_ui()

    def _build_ui(self):
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)

        header = QLabel("User Login")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(HEADER_STYLE)
        wrapper.addWidget(header)

        body = QFrame()
        body.setStyleSheet(POPUP_BG)
        layout = QFormLayout(body)
        layout.setContentsMargins(30, 30, 30, 30)
        wrapper.addWidget(body)

        self.user_id_input = QLineEdit()
        self.user_id_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("User ID:", self.user_id_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("Password:", self.password_input)

        btns = QHBoxLayout()
        btns.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(BTN_SECONDARY)
        cancel_btn.clicked.connect(self._on_cancel)

        login_btn = QPushButton("Login")
        login_btn.setStyleSheet(BTN_PRIMARY)
        login_btn.clicked.connect(self._on_login)

        btns.addWidget(cancel_btn)
        btns.addWidget(login_btn)
        layout.addRow("", btns)

    def _on_cancel(self):
        """Handle cancel button - show confirmation before exiting."""
        reply = QMessageBox.question(
            self, "Exit", "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.reject()
        # If No, do nothing - dialog stays open

    def _on_login(self):
        if not self.user_id_input.text().strip() or not self.password_input.text():
            QMessageBox.warning(self, "Missing", "User ID and Password are required.")
            return
        self.accept()

    def closeEvent(self, event):
        """Handle close event - ask for confirmation before exiting."""
        reply = QMessageBox.question(
            self, "Exit", "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


# ==============================================================
# Welcome Dialog — organization details (A1-C styled)
# ==============================================================
class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setFixedSize(520, 460)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._build_ui()

    def _build_ui(self):
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Welcome — Organization Setup")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(HEADER_STYLE)
        wrapper.addWidget(header)

        body = QFrame()
        body.setStyleSheet(POPUP_BG)
        layout = QFormLayout(body)
        layout.setContentsMargins(30, 30, 30, 30)
        wrapper.addWidget(body)

        # Inputs
        self.org = QLineEdit()
        self.loc = QLineEdit()
        self.region = QLineEdit()
        self.address = QLineEdit()
        self.country = QLineEdit()

        for w in [self.org, self.loc, self.region, self.address, self.country]:
            w.setStyleSheet(INPUT_STYLE)

        cfg = load_config()
        self.org.setText(cfg.get("organization_name", ""))
        self.loc.setText(cfg.get("location_name", ""))
        self.region.setText(cfg.get("region", ""))
        self.address.setText(cfg.get("address", ""))
        self.country.setText(cfg.get("country", ""))

        layout.addRow("Organization:", self.org)
        layout.addRow("Location:", self.loc)
        layout.addRow("Region:", self.region)
        layout.addRow("Address:", self.address)
        layout.addRow("Country:", self.country)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(BTN_PRIMARY)
        save_btn.clicked.connect(self._save)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(BTN_SECONDARY)
        cancel_btn.clicked.connect(self.reject)

        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addRow("", btns)

    def _save(self):
        if not self.org.text().strip() or not self.loc.text().strip():
            QMessageBox.warning(self, "Missing", "Organization and Location are required.")
            return

        cfg = load_config()
        cfg.update({
            "organization_name": self.org.text().strip(),
            "location_name": self.loc.text().strip(),
            "region": self.region.text().strip(),
            "address": self.address.text().strip(),
            "country": self.country.text().strip(),
        })
        save_config(cfg)
        self.accept()


class CreateProfileDialog(QDialog):
    def __init__(self, first_user: bool, default_org: str = "", parent=None):
        super().__init__(parent)
        self.first_user = first_user
        self.setModal(True)
        self.setFixedSize(520, 460)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._build_ui(default_org)

    def _build_ui(self, default_org: str):
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Create Profile")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(HEADER_STYLE)
        wrapper.addWidget(header)

        body = QFrame()
        body.setStyleSheet(POPUP_BG)
        layout = QFormLayout(body)
        layout.setContentsMargins(30, 30, 30, 30)
        wrapper.addWidget(body)

        self.name_input = QLineEdit()
        self.name_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("Name:", self.name_input)

        self.org_input = QLineEdit(default_org)
        self.org_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("Organization:", self.org_input)

        self.user_id_input = QLineEdit()
        self.user_id_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("User ID:", self.user_id_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("Password:", self.password_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("Confirm Password:", self.confirm_input)

        self.role_input = QComboBox()
        self.role_input.addItems(["super_admin", "super_user", "user"])
        if self.first_user:
            # Force initial profile to super_admin
            self.role_input.setCurrentText("super_admin")
            self.role_input.setEnabled(False)
        self.role_input.setStyleSheet(INPUT_STYLE)
        layout.addRow("Role:", self.role_input)

        btns = QHBoxLayout()
        btns.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(BTN_SECONDARY)
        cancel_btn.clicked.connect(self.reject)

        create_btn = QPushButton("Create")
        create_btn.setStyleSheet(BTN_PRIMARY)
        create_btn.clicked.connect(self._on_create)

        btns.addWidget(cancel_btn)
        btns.addWidget(create_btn)
        layout.addRow("", btns)

    def _on_create(self):
        name = self.name_input.text().strip()
        org = self.org_input.text().strip()
        uid = self.user_id_input.text().strip()
        pwd = self.password_input.text()
        cpwd = self.confirm_input.text()
        role = self.role_input.currentText().strip() or "user"

        if not name or not org or not uid or not pwd:
            QMessageBox.warning(self, "Missing", "All fields are required.")
            return
        if pwd != cpwd:
            QMessageBox.warning(self, "Mismatch", "Passwords do not match.")
            return
        if role not in ("super_admin", "super_user", "user"):
            QMessageBox.warning(self, "Invalid", "Role must be super_admin, super_user or user.")
            return

        self.accept()


# ==============================================================
# MAIN WINDOW
# ==============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.db_manager = DatabaseManager()
        self.license_manager = LicenseManager(self.db_manager)

        # user/session state
        self.current_user = None
        self.current_role = None
        self.current_password_plain = None

        # ------------------------
        # Build UI; license/user flows run from run_startup_flow()
        # ------------------------
        self.init_ui()
        self.setup_auto_refresh()

    def run_startup_flow(self) -> bool:
        """Run license flow then user login/profile flow.

        Returns False if the app should exit (e.g. user cancels).
        """
        if not self._ensure_license():
            QMessageBox.critical(self, "License Error", "License missing or invalid.")
            return False

        # If someone was previously logged in and we didn't explicitly log out,
        # restore that session without prompting for credentials.
        if not self._try_auto_login_from_config():
            if not self._ensure_user_login():
                return False

        self._apply_role_permissions()
        self._update_user_button()
        return True

    # ------------------------------------------------------
    # Startup License Logic
    # ------------------------------------------------------
    def _ensure_license(self) -> bool:
        info = self.db_manager.get_license_info()

        if info and info.get("license_key"):
            # Active?
            if info.get("is_active"):
                if self.license_manager.is_licensed():
                    # Require org setup if missing
                    cfg = load_config()
                    if not cfg.get("organization_name"):
                        WelcomeDialog(self).exec_()
                    return True
            else:
                # Not active → LOGIN popup (key only)
                dlg = LicenseDialog(self.license_manager, mode="login", parent=self)
                if dlg.exec_() == QDialog.Accepted:
                    cfg = load_config()
                    if not cfg.get("organization_name"):
                        WelcomeDialog(self).exec_()
                    return True
                return False

        # No license stored → Activation popup
        dlg = LicenseDialog(self.license_manager, mode="activate", parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return False

        # After activation → setup org details
        cfg = load_config()
        if not cfg.get("organization_name"):
            WelcomeDialog(self).exec_()

        return self.license_manager.is_licensed()

    def _ensure_user_login(self) -> bool:
        try:
            users = self.db_manager.list_users()
        except Exception:
            users = []

        cfg = load_config()
        org_name = cfg.get("organization_name", "")

        # First time after activation: create initial super_admin
        if not users:
            dlg = CreateProfileDialog(first_user=True, default_org=org_name, parent=self)
            if dlg.exec_() != QDialog.Accepted:
                return False

            created = self.db_manager.create_user(
                name=dlg.name_input.text().strip(),
                organization=dlg.org_input.text().strip(),
                user_id=dlg.user_id_input.text().strip(),
                password_plain=dlg.password_input.text(),
                role="super_admin",
            )
            if not created:
                QMessageBox.critical(self, "Error", "Failed to create initial user.")
                return False

            try:
                users = self.db_manager.list_users()
            except Exception:
                users = []
            if not users:
                return False

        # Normal login loop
        while True:
            login = LoginDialog(self)
            if login.exec_() != QDialog.Accepted:
                return False

            creds = self.db_manager.get_user_by_credentials(
                login.user_id_input.text().strip(),
                login.password_input.text(),
            )
            if not creds or not creds.get("is_active", True):
                QMessageBox.warning(self, "Invalid credentials", "Invalid credentials.")
                continue

            self.current_user = creds
            self.current_role = creds.get("role", "user")
            self.current_password_plain = login.password_input.text()
            # Persist last logged-in user for auto-login on next startup
            cfg = load_config()
            cfg["last_user_id"] = self.current_user.get("user_id")
            save_config(cfg)
            # Ensure toolbar/menu reflect the newly logged-in user
            self._update_user_button()
            return True

    def _try_auto_login_from_config(self) -> bool:
        cfg = load_config()
        last_user_id = cfg.get("last_user_id")
        if not last_user_id:
            return False

        user = self.db_manager.get_user_by_user_id(last_user_id)
        if not user or not user.get("is_active", True):
            # Clear stale entry
            cfg.pop("last_user_id", None)
            save_config(cfg)
            return False

        self.current_user = user
        self.current_role = user.get("role", "user")
        self.current_password_plain = None
        return True

    def _open_profiles(self):
        dlg = ProfilesDialog(
            self.db_manager,
            self.current_user or {},
            self.current_password_plain or "",
            parent=self,
        )
        dlg.exec_()

    def _apply_role_permissions(self):
        """Hide/restore modules according to role.

        For now: hide All Records for plain 'user' accounts.
        """
        if not self.current_role:
            return

        # All Records tab
        all_index = self.tabs.indexOf(self.all_records_widget)
        if self.current_role == "user":
            if all_index != -1:
                self.tabs.removeTab(all_index)
        else:
            if all_index == -1:
                self.tabs.addTab(self.all_records_widget, "All Records")

    # ------------------------------------------------------
    # Build UI
    # ------------------------------------------------------
    def init_ui(self):
        self.setWindowTitle("M-Neo VMS")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(MAIN_STYLE)

        # Icon
        ico = QIcon(str(APP_BASE / "assets" / "logo.ico"))
        if not ico.isNull():
            self.setWindowIcon(ico)

        # Toolbar (About + Profiles only)
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        about = QAction("About", self)
        about.triggered.connect(self._about)
        toolbar.addAction(about)

        # Restore dedicated Profiles button next to About
        profiles_action = QAction("Profiles", self)
        profiles_action.triggered.connect(self._open_profiles)
        toolbar.addAction(profiles_action)

        # Status bar
        cfg = load_config()
        org = cfg.get("organization_name", "—")
        loc = cfg.get("location_name", "—")
        self.org_label = QLabel(f"{org} — {loc}")
        self.statusBar().addPermanentWidget(self.org_label)
        self.statusBar().showMessage("Ready")

        # Tabs
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.dashboard_widget = DashboardWidget(self.db_manager)
        self.registration_widget = RegistrationWidget(self.db_manager)
        self.active_visitors_widget = ActiveVisitorsWidget(self.db_manager)
        self.history_widget = HistoryWidget(self.db_manager)
        self.all_records_widget = AllRecordsWidget(self.db_manager)

        self.tabs.addTab(self.dashboard_widget, "Dashboard")
        self.tabs.addTab(self.registration_widget, "Registration")
        self.tabs.addTab(self.active_visitors_widget, "Active Visitors")
        self.tabs.addTab(self.history_widget, "Today’s History")
        self.tabs.addTab(self.all_records_widget, "All Records")

        # User display in top-right corner of the tab bar (same row as module tabs)
        self.user_button = QToolButton(self)
        self.user_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.user_button.setPopupMode(QToolButton.InstantPopup)
        # Larger, pill-shaped style to match app theme
        self.user_button.setStyleSheet(
            """
            QToolButton {
                background-color: #f3edf7;
                color: #4a3b4d;
                border-radius: 18px;
                padding: 6px 18px;
                font-weight: 600;
                font-size: 11pt;
            }
            QToolButton:hover {
                background-color: #e4d8f0;
            }
            QToolButton::menu-indicator {
                image: none;
            }
            """
        )

        user_icon = QIcon(str(APP_BASE / "assets" / "user.ico"))
        if not user_icon.isNull():
            self.user_button.setIcon(user_icon)

        self.user_menu = QMenu(self)
        self.user_role_action = QAction("Role: -", self.user_menu)
        self.user_role_action.setEnabled(False)
        self.user_menu.addAction(self.user_role_action)
        self.user_menu.addSeparator()
        self.user_menu.addAction("Log Out", self._logout)
        self.user_button.setMenu(self.user_menu)
        self.user_button.setText("Not logged in")

        self.tabs.setCornerWidget(self.user_button, Qt.TopRightCorner)

        layout.addWidget(self.tabs)

        # Lazy data loading: refresh the selected tab when it becomes active
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Ensure initial tab (Dashboard) is up to date
        try:
            self.dashboard_widget.refresh_data()
        except Exception:
            pass

    # ------------------------------------------------------
    # ABOUT
    # ------------------------------------------------------
    def _about(self):
        cfg = load_config()

        QMessageBox.information(
            self,
            "About",
            f"""
<b>M-Neo VMS</b><br>
Organization: {cfg.get('organization_name', '—')}<br>
Location: {cfg.get('location_name', '—')}<br>
Region: {cfg.get('region', '—')}<br>
Address: {cfg.get('address', '—')}<br>
Country: {cfg.get('country', '—')}<br>
"""
        )

    # ------------------------------------------------------
    # LOGOUT (back to user login; license remains active)
    # ------------------------------------------------------
    def _logout(self):
        reply = QMessageBox.question(
            self, "Log Out",
            "You will be returned to the login screen. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # Clear persisted auto-login info
        cfg = load_config()
        cfg.pop("last_user_id", None)
        save_config(cfg)

        self.current_user = None
        self.current_role = None
        self.current_password_plain = None
        self._update_user_button()

        # Hide main window while login dialog is shown, so it is not visible behind it
        self.hide()
        try:
            if not self._ensure_user_login():
                # user cancelled login; close app while hidden
                self.close()
                return
            # Successful login: restore window and apply permissions
            self._apply_role_permissions()
            self.show()
        finally:
            # If _ensure_user_login raised unexpectedly, at least close the window
            if not self.isVisible():
                # avoid leaving a hidden, unusable window
                self.close()

    def _update_user_button(self):
        if not hasattr(self, "user_button"):
            return

        if self.current_user:
            name = self.current_user.get("name") or self.current_user.get("user_id", "User")
            role = self.current_role or ""
            # Button text: only show the user's name
            self.user_button.setText(name)
            # Menu: reflect the current role if we have the helper action
            if hasattr(self, "user_role_action") and self.user_role_action is not None:
                role_label = role or "-"
                self.user_role_action.setText(f"Role: {role_label}")
        else:
            self.user_button.setText("Not logged in")
            if hasattr(self, "user_role_action") and self.user_role_action is not None:
                self.user_role_action.setText("Role: -")

    # ------------------------------------------------------
    # Auto Refresh
    # ------------------------------------------------------
    def setup_auto_refresh(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh)
        self.refresh_timer.start(30000)

    def _refresh(self):
        try:
            self.dashboard_widget.refresh_data()
        except Exception:
            pass

        try:
            self.active_visitors_widget.refresh_data()
        except Exception:
            pass

        try:
            self.history_widget.refresh_data()
        except Exception:
            pass

        # For role 'user', the All Records tab is hidden; also skip loading data defensively.
        if self.current_role and self.current_role == "user":
            return

        try:
            self.all_records_widget.refresh_data()
        except Exception:
            pass

    def _on_tab_changed(self, index: int):
        widget = self.tabs.widget(index)

        try:
            if widget is self.dashboard_widget:
                self.dashboard_widget.refresh_data()
            elif widget is self.active_visitors_widget:
                self.active_visitors_widget.refresh_data()
            elif widget is self.history_widget:
                self.history_widget.refresh_data()
            elif widget is self.all_records_widget:
                # Only allow All Records to load for elevated roles
                if self.current_role and self.current_role != "user":
                    self.all_records_widget.refresh_data()
        except Exception:
            pass

    # ------------------------------------------------------
    # Exit dialog
    # ------------------------------------------------------
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Exit", "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
