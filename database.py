import sqlite3
import os
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import logging
import uuid
import re


# -------------------------
# DEVICE IDENTIFIER
# -------------------------
def get_device_mac() -> str:
    """Return unique machine identifier (MAC-based)."""
    return hex(uuid.getnode()).upper()


# -------------------------
# REGEXP SUPPORT FOR SQLITE
# -------------------------
def regexp(pattern, value):
    if value is None:
        return False
    return re.match(pattern, value) is not None


class DatabaseManager:
    def __init__(self, db_path: str = None):

        # -------------------------
        # Store DB per machine
        # -------------------------
        if db_path is None:
            appdata = Path(os.getenv("APPDATA")) / "M-Neo-VMS"
            appdata.mkdir(parents=True, exist_ok=True)
            db_path = appdata / "visitor_management.db"

        self.db_path = str(db_path)

        # Enable SQLite REGEXP
        conn = sqlite3.connect(self.db_path)
        conn.create_function("REGEXP", 2, regexp)
        conn.close()

        self.init_database()
        self._verify_device_identity()

    # -------------------------------------------------------
    def get_connection(self):
        return sqlite3.connect(self.db_path)

    # -------------------------------------------------------
    # DATABASE INITIALIZATION
    # -------------------------------------------------------
    def init_database(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS visitors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nric TEXT,
                        hp_no TEXT,
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        purpose TEXT NOT NULL,
                        destination TEXT NOT NULL,
                        company TEXT,
                        vehicle_number TEXT,
                        pass_number TEXT,
                        remarks TEXT,
                        person_visited TEXT NOT NULL,
                        organization TEXT,
                        check_in_time DATETIME NOT NULL,
                        check_out_time DATETIME,
                        duration INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS license (
                        id INTEGER PRIMARY KEY,
                        license_key TEXT NOT NULL,
                        device_mac TEXT NOT NULL,
                        activation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')

                conn.commit()
                logging.info("Database initialized successfully")

        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")

    # -------------------------------------------------------
    # DEVICE BINDING LOGIC
    # -------------------------------------------------------
    def _verify_device_identity(self):
        """If DB was copied to another machine → reset visitor data."""
        current_mac = get_device_mac()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT device_mac FROM license WHERE id = 1")
            row = cursor.fetchone()

            if not row:
                cursor.execute("INSERT INTO license (id, license_key, device_mac) VALUES (1, '', ?)", (current_mac,))
                conn.commit()
                return

            stored_mac = row[0]

            if stored_mac != current_mac:
                logging.warning("⚠ Database copied from a different machine — Resetting visitor records.")
                cursor.execute("DELETE FROM visitors")
                cursor.execute("UPDATE license SET device_mac=? WHERE id=1", (current_mac,))
                conn.commit()
                logging.info("✅ Reset complete — Database now bound to this device.")

    # -------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------
    @staticmethod
    def validate_nric(nric: str) -> bool:
        return bool(re.match(r"^[STFG][0-9]{7}[A-Z]$", nric.upper()))

    @staticmethod
    def validate_hp(hp_no: str) -> bool:
        return hp_no.isdigit() and len(hp_no) == 8

    # -------------------------------------------------------
    # ADD VISITOR (includes validation)
    # -------------------------------------------------------
    def add_visitor(self, **kwargs) -> bool:
        try:
            if kwargs.get("nric"):
                kwargs["nric"] = kwargs["nric"].upper()
                if not self.validate_nric(kwargs["nric"]):
                    logging.warning("Rejected invalid NRIC format.")
                    return False

            if kwargs.get("hp_no") and not self.validate_hp(kwargs["hp_no"]):
                logging.warning("Rejected invalid HP number format.")
                return False

            check_in_time = kwargs.get("check_in_time", datetime.now())
            kwargs["check_in_time"] = check_in_time.strftime('%Y-%m-%d %H:%M:%S')

            if not kwargs.get("name"):
                fn = kwargs.get("first_name", "")
                ln = kwargs.get("last_name", "")
                kwargs["name"] = f"{fn} {ln}".strip()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO visitors (
                        nric, hp_no, first_name, last_name, name, category,
                        purpose, destination, company, vehicle_number,
                        pass_number, remarks, person_visited, organization, check_in_time
                    ) VALUES (
                        :nric, :hp_no, :first_name, :last_name, :name, :category,
                        :purpose, :destination, :company, :vehicle_number,
                        :pass_number, :remarks, :person_visited, :organization, :check_in_time
                    )
                ''', kwargs)
                conn.commit()
                return True

        except Exception as e:
            logging.error(f"Error adding visitor: {e}")
            return False

    # -------------------------------------------------------
    # PASS NUMBER GENERATION
    # -------------------------------------------------------
    def generate_pass_number(self) -> str:
        try:
            today = datetime.now().strftime('%Y%m%d')
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM visitors WHERE DATE(check_in_time)=DATE('now')")
                count = cursor.fetchone()[0]
                return f"VMS-{today}-{count + 1:04d}"
        except:
            return f"VMS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # -------------------------------------------------------
    # EXISTING VISITOR LOOKUP
    # -------------------------------------------------------
    def find_visitors_by_nric(self, nric: str = "", hp_no: str = "") -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if nric and hp_no:
                    query = """
                        SELECT nric, first_name, last_name, company, vehicle_number,
                               hp_no, category, check_in_time as last_visit
                        FROM visitors
                        WHERE nric LIKE ? OR hp_no LIKE ?
                        ORDER BY check_in_time DESC
                    """
                    params = (f"%{nric}%", f"%{hp_no}%")
                elif nric:
                    query = """
                        SELECT nric, first_name, last_name, company, vehicle_number,
                               hp_no, category, check_in_time as last_visit
                        FROM visitors
                        WHERE nric LIKE ?
                        ORDER BY check_in_time DESC
                    """
                    params = (f"%{nric}%",)
                elif hp_no:
                    query = """
                        SELECT nric, first_name, last_name, company, vehicle_number,
                               hp_no, category, check_in_time as last_visit
                        FROM visitors
                        WHERE hp_no LIKE ?
                        ORDER BY check_in_time DESC
                    """
                    params = (f"%{hp_no}%",)
                else:
                    return []

                cursor.execute(query, params)
                rows = cursor.fetchall()

                result = []
                for row in rows:
                    result.append({
                        'nric': row[0] or '',
                        'first_name': row[1] or '',
                        'last_name': row[2] or '',
                        'company': row[3] or '',
                        'vehicle_number': row[4] or '',
                        'hp_no': row[5] or '',
                        'category': row[6] or '',
                        'last_visit': row[7] if len(row) > 7 else None
                    })
                return result

        except sqlite3.Error as e:
            logging.error(f"Error finding visitors by NRIC/HP: {e}")
            return []

    # -------------------------------------------------------
    # ACTIVE VISITORS
    # -------------------------------------------------------
    def get_active_visitors(self) -> List[Dict]:
        """Get all visitors who haven't checked out"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        id,
                        nric,
                        hp_no,
                        first_name,
                        last_name,
                        category,
                        purpose,
                        destination,
                        company,
                        vehicle_number,
                        person_visited,
                        remarks,
                        check_in_time
                    FROM visitors
                    WHERE check_out_time IS NULL
                    ORDER BY check_in_time DESC
                """)

                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting active visitors: {e}")
            return []


    # -------------------------------------------------------
    # CHECKOUT
    # -------------------------------------------------------
    def checkout_visitor(self, visitor_id: int) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                checkout_time = datetime.now()
                checkout_time_str = checkout_time.strftime('%Y-%m-%d %H:%M:%S')

                cursor.execute('SELECT check_in_time FROM visitors WHERE id = ?', (visitor_id,))
                result = cursor.fetchone()
                if not result:
                    return False

                check_in_str = result[0]
                check_in_time = datetime.fromisoformat(check_in_str)

                duration = int((checkout_time - check_in_time).total_seconds() // 60)

                cursor.execute('''
                    UPDATE visitors
                    SET check_out_time = ?, duration = ?
                    WHERE id = ?
                ''', (checkout_time_str, duration, visitor_id))
                conn.commit()
                return True

        except sqlite3.Error as e:
            logging.error(f"Error checking out visitor: {e}")
            return False

    # -------------------------------------------------------
    # HISTORY + REPORTS (unchanged logic)
    # -------------------------------------------------------
    def get_todays_history(self) -> List[Dict]:
        try:
            today = date.today()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, first_name, last_name, nric, hp_no, category,
                           vehicle_number, company, organization, purpose, destination, pass_number,
                           check_in_time, check_out_time, duration
                    FROM visitors
                    WHERE DATE(check_in_time) = ?
                    ORDER BY check_in_time DESC
                ''', (today,))
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting today's history: {e}")
            return []

    def get_all_records(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if start_date and end_date:
                    cursor.execute('''
                        SELECT * FROM visitors
                        WHERE DATE(check_in_time) BETWEEN ? AND ?
                        ORDER BY check_in_time DESC
                    ''', (start_date, end_date))
                else:
                    cursor.execute('''
                        SELECT * FROM visitors
                        ORDER BY check_in_time DESC
                    ''')

                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_daily_checkins_current_month(self) -> List[Tuple[date, int]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DATE(check_in_time) as date, COUNT(*) as count
                    FROM visitors
                    WHERE strftime('%Y-%m', check_in_time) = strftime('%Y-%m', 'now')
                    GROUP BY DATE(check_in_time)
                    ORDER BY date
                ''')
                return [(datetime.strptime(row[0], '%Y-%m-%d').date(), row[1]) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_todays_checkin_count(self) -> int:
        try:
            today = date.today()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM visitors WHERE DATE(check_in_time) = ?", (today,))
                return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0

    def get_average_duration(self) -> float:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT AVG(duration) FROM visitors WHERE duration IS NOT NULL")
                result = cursor.fetchone()[0]
                return result if result else 0.0
        except sqlite3.Error:
            return 0.0

    # -------------------------------------------------------
    # LICENSE MANAGEMENT (unchanged)
    # -------------------------------------------------------
    def save_license(self, license_key: str, device_mac: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO license (id, license_key, device_mac)
                    VALUES (1, ?, ?)
                ''', (license_key, device_mac))
                conn.commit()
                return True
        except sqlite3.Error:
            return False

    def get_license_info(self) -> Optional[Dict]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM license WHERE id = 1")
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                return None
        except sqlite3.Error:
            return None
