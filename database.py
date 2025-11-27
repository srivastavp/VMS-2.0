# database.py
import sqlite3
import os
import logging
import uuid
import re
import hashlib
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any, Union
from threading import Lock


# -------------------------
# DEVICE IDENTIFIER
# -------------------------
def get_device_mac() -> str:
    """Return unique machine identifier (MAC-based). Hex uppercase format."""
    return hex(uuid.getnode()).upper()


# -------------------------
# REGEXP SUPPORT FOR SQLITE
# -------------------------
def regexp(pattern: str, value: Optional[str]) -> bool:
    if value is None:
        return False
    return re.match(pattern, value) is not None


# -------------------------
# Lightweight in-memory cache
# -------------------------
class _SimpleCache:
    def __init__(self, ttl_seconds: int = 5):
        self._ttl = timedelta(seconds=ttl_seconds)
        self._store: Dict[str, Tuple[datetime, Any]] = {}
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            v = self._store.get(key)
            if not v:
                return None
            created, value = v
            if datetime.now() - created > self._ttl:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any):
        with self._lock:
            self._store[key] = (datetime.now(), value)

    def invalidate(self, prefix: Optional[str] = None):
        with self._lock:
            if prefix is None:
                self._store.clear()
            else:
                keys = [k for k in self._store.keys() if k.startswith(prefix)]
                for k in keys:
                    del self._store[k]


class DatabaseManager:
    """
    Optimized SQLite manager:
      - PRAGMA tuning for better performance
      - Centralized query helpers
      - Simple short-lived caching for read-heavy endpoints
      - Indexes created for frequently queried columns
      - MAC-bound database protection
    """

    def __init__(self, db_path: str = None, cache_ttl: int = 5):
        # place DB inside project/data by default (portable)
        base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent
        data_dir = base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        if db_path is None:
            db_path = data_dir / "visitor_management.db"

        self.db_path = str(db_path)
        self._conn_lock = Lock()
        self._cache = _SimpleCache(ttl_seconds=cache_ttl)

        # Ensure DB file exists and apply REGEXP function + PRAGMAs
        self._init_connection_environment()
        # Initialize schema & indices
        self.init_database()
        # Enforce device binding logic (may wipe visitor logs if DB switched machines)
        self._verify_device_identity()

        logging.info("Database initialized at %s", self.db_path)

    # -------------------------
    # low-level connection helpers
    # -------------------------
    def get_connection(self) -> sqlite3.Connection:
        """
        Return a new sqlite3.Connection configured with recommended pragmas.
        Use short-lived connections (connect / close) to avoid concurrency issues.
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=5,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        conn.row_factory = sqlite3.Row

        # Register REGEXP function per-connection + performance PRAGMAs
        try:
            conn.create_function("REGEXP", 2, regexp)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            conn.execute("PRAGMA foreign_keys=ON;")
        except Exception:
            # If any pragma fails, we still keep working with defaults
            logging.exception("Failed to apply PRAGMA on new connection")

        return conn

    def _init_connection_environment(self):
        # ensure DB file is reachable and create one connection to initialize PRAGMAs
        try:
            conn = self.get_connection()
            conn.close()
        except Exception:
            logging.exception("Failed to initialize DB connection environment")

    # -------------------------
    # central query helpers
    # (accept params either as tuple/list OR as dict for named params)
    # -------------------------
    def _fetchall(self, query: str, params: Union[Tuple, Dict, List] = ()) -> List[sqlite3.Row]:
        try:
            with self.get_connection() as conn:
                cur = conn.execute(query, params)
                rows = cur.fetchall()
                return rows
        except sqlite3.Error:
            logging.exception("Query failed: %s params=%s", query, params)
            return []

    def _fetchone(self, query: str, params: Union[Tuple, Dict, List] = ()):
        try:
            with self.get_connection() as conn:
                cur = conn.execute(query, params)
                return cur.fetchone()
        except sqlite3.Error:
            logging.exception("Query failed: %s params=%s", query, params)
            return None

    def _execute(self, query: str, params: Union[Tuple, Dict, List] = ()):
        try:
            with self.get_connection() as conn:
                cur = conn.execute(query, params)
                conn.commit()
                return cur
        except sqlite3.Error:
            logging.exception("Execution failed: %s params=%s", query, params)
            return None

    # -------------------------
    # schema / indices
    # -------------------------
    def init_database(self):
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()

                # Base schema (original)
                cur.execute('''
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
                        pass_number TEXT,          -- Visit ID (kept as is, UI renames)
                        remarks TEXT,
                        person_visited TEXT NOT NULL,
                        organization TEXT,
                        check_in_time DATETIME NOT NULL,
                        check_out_time DATETIME,
                        duration INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cur.execute('''
                    CREATE TABLE IF NOT EXISTS blacklist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hp_no TEXT NOT NULL UNIQUE,
                        name TEXT,
                        nric TEXT,
                        reason TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # --- Migration: ensure id_number column exists (new physical badge field) ---
                cur.execute("PRAGMA table_info(visitors)")
                cols = [row["name"] for row in cur.fetchall()]
                if "id_number" not in cols:
                    # optional physical badge number; stored as TEXT but expected to be numeric in UI
                    cur.execute("ALTER TABLE visitors ADD COLUMN id_number TEXT")

                cur.execute('''
                    CREATE TABLE IF NOT EXISTS license (
                        id INTEGER PRIMARY KEY,
                        license_key TEXT NOT NULL,
                        device_mac TEXT NOT NULL,
                        activation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active INTEGER DEFAULT 1
                    )
                ''')

                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        organization TEXT NOT NULL,
                        user_id TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Indices for faster lookups
                cur.execute("CREATE INDEX IF NOT EXISTS idx_visitors_checkin ON visitors (DATE(check_in_time));")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_visitors_nric ON visitors (nric);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_visitors_hp ON visitors (hp_no);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_visitors_checkout ON visitors (check_out_time);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_visitors_pass ON visitors (pass_number);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users (user_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_hp_no ON blacklist (hp_no);")

                conn.commit()
                logging.info("Database schema & indices ensured")
        except sqlite3.Error:
            logging.exception("Database initialization error")

    # -------------------------
    # DEVICE PROTECTION (unchanged logic; strict)
    # -------------------------
    def _verify_device_identity(self):
        current_mac = get_device_mac()
        try:
            row = self._fetchone("SELECT device_mac FROM license WHERE id = 1")
            if not row:
                # first run: create license placeholder with this device mac (empty key)
                self._execute(
                    "INSERT OR REPLACE INTO license (id, license_key, device_mac, is_active) "
                    "VALUES (1, ?, ?, 0)",
                    ("", current_mac)
                )
                return

            stored_mac = row["device_mac"] if isinstance(row, sqlite3.Row) and "device_mac" in row else row[0]
            if stored_mac != current_mac:
                logging.warning("Database appears to have been copied from another machine. Clearing visitor logs.")
                # wipe visitor logs (audit policy), update device mac
                self._execute("DELETE FROM visitors")
                self._execute("UPDATE license SET device_mac=? WHERE id=1", (current_mac,))
                logging.info("DB now bound to this device (mac updated)")
                # invalidate caches
                self._cache.invalidate()
        except Exception:
            logging.exception("Device identity verification failed")

    # -------------------------
    # VALIDATORS
    # -------------------------
    @staticmethod
    def validate_nric(nric: str) -> bool:
        return bool(re.match(r"^[STFG][0-9]{7}[A-Z]$", nric.upper()))

    @staticmethod
    def validate_hp(hp_no: str) -> bool:
        return hp_no.isdigit() and len(hp_no) == 8

    # -------------------------
    # VISITOR STATE HELPERS (for existing visitor logic)
    # -------------------------
    def has_active_visit(self, nric: str = "", hp_no: str = "") -> bool:
        """
        Return True if there is any ACTIVE visit (check_out_time IS NULL)
        for the given NRIC and/or HP number.
        Used to block onboarding of a visitor who is currently inside.
        """
        if not nric and not hp_no:
            return False

        clauses = []
        params: List[Any] = []

        if nric:
            clauses.append("nric = ?")
            params.append(nric.upper())
        if hp_no:
            clauses.append("hp_no = ?")
            params.append(hp_no)

        where_id = " OR ".join(clauses)
        query = f"""
            SELECT 1
            FROM visitors
            WHERE ({where_id}) AND check_out_time IS NULL
            LIMIT 1
        """

        row = self._fetchone(query, tuple(params))
        return bool(row)

    def get_most_recent_visit_for_autofill(
        self,
        nric: str = "",
        hp_no: str = ""
    ) -> Optional[Dict]:
        """
        Fetch the MOST RECENT *completed* visit (check_out_time IS NOT NULL)
        for the given NRIC / HP.
        This is used to pre-fill the registration form for frequent visitors.
        """
        if not nric and not hp_no:
            return None

        clauses = []
        params: List[Any] = []

        if nric:
            clauses.append("nric = ?")
            params.append(nric.upper())
        if hp_no:
            clauses.append("hp_no = ?")
            params.append(hp_no)

        where_id = " OR ".join(clauses)

        query = f"""
            SELECT
                nric,
                hp_no,
                first_name,
                last_name,
                company,
                vehicle_number,
                purpose,
                destination,
                person_visited,
                check_in_time AS last_visit
            FROM visitors
            WHERE ({where_id})
              AND check_out_time IS NOT NULL
            ORDER BY check_in_time DESC
            LIMIT 1
        """

        row = self._fetchone(query, tuple(params))
        if not row:
            return None

        return {
            "nric": row["nric"] or "",
            "hp_no": row["hp_no"] or "",
            "first_name": row["first_name"] or "",
            "last_name": row["last_name"] or "",
            "company": row["company"] or "",
            "vehicle_number": row["vehicle_number"] or "",
            "purpose": row["purpose"] or "",
            "destination": row["destination"] or "",
            "person_visited": row["person_visited"] or "",
            "last_visit": row["last_visit"],
        }

    # -------------------------
    # WRITE OPERATIONS (invalidate caches on success)
    # -------------------------
    def add_visitor(self, **kwargs) -> bool:
        """
        Add visitor. Accepts same kwargs as before plus optional id_number.
        On success: invalidate caches relevant to active visitors and counts.
        """
        try:
            if kwargs.get("nric"):
                kwargs["nric"] = kwargs["nric"].upper()
                if not self.validate_nric(kwargs["nric"]):
                    logging.debug("Invalid NRIC format when adding visitor")
                    return False

            if kwargs.get("hp_no") and not self.validate_hp(kwargs["hp_no"]):
                logging.debug("Invalid HP format when adding visitor")
                return False

            if not kwargs.get("name"):
                fn = kwargs.get("first_name", "")
                ln = kwargs.get("last_name", "")
                kwargs["name"] = f"{fn} {ln}".strip()

            # ensure check_in_time string
            kwargs["check_in_time"] = kwargs.get("check_in_time") or datetime.now()
            if isinstance(kwargs["check_in_time"], datetime):
                kwargs["check_in_time"] = kwargs["check_in_time"].strftime('%Y-%m-%d %H:%M:%S')

            # optional physical badge number
            kwargs.setdefault("id_number", None)

            query = '''
                INSERT INTO visitors (
                    nric, hp_no, first_name, last_name, name, category,
                    purpose, destination, company, vehicle_number,
                    pass_number, id_number, remarks, person_visited,
                    organization, check_in_time
                ) VALUES (
                    :nric, :hp_no, :first_name, :last_name, :name, :category,
                    :purpose, :destination, :company, :vehicle_number,
                    :pass_number, :id_number, :remarks, :person_visited,
                    :organization, :check_in_time
                )
            '''

            # Execute with named parameters dict (sqlite accepts dict for :name style)
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, kwargs)
                conn.commit()

            # invalidate relevant caches
            self._cache.invalidate(prefix="active")
            self._cache.invalidate(prefix="counts")
            return True
        except sqlite3.Error:
            logging.exception("Error adding visitor (sqlite error)")
            return False
        except Exception:
            logging.exception("Unexpected error in add_visitor")
            return False

    def checkout_visitor(self, visitor_id: int) -> bool:
        """
        Set check_out_time and duration. On success, invalidate caches.
        """
        try:
            checkout_time = datetime.now()
            row = self._fetchone(
                "SELECT check_in_time FROM visitors WHERE id = ?",
                (visitor_id,)
            )
            if not row:
                logging.debug("Checkout attempted for non-existing visitor id=%s", visitor_id)
                return False

            check_in_str = row["check_in_time"] if isinstance(row, sqlite3.Row) else row[0]
            # support both isoformat and our stored format
            try:
                check_in_dt = datetime.fromisoformat(check_in_str)
            except Exception:
                check_in_dt = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')

            duration_minutes = int((checkout_time - check_in_dt).total_seconds() // 60)
            self._execute(
                '''
                UPDATE visitors
                SET check_out_time = ?, duration = ?
                WHERE id = ?
                ''',
                (checkout_time.strftime('%Y-%m-%d %H:%M:%S'), duration_minutes, visitor_id)
            )

            self._cache.invalidate(prefix="active")
            self._cache.invalidate(prefix="history")
            self._cache.invalidate(prefix="counts")
            return True
        except sqlite3.Error:
            logging.exception("checkout_visitor failed")
            return False

    # -------------------------
    # PASS NUMBER / VISIT ID generation
    # -------------------------
    def generate_pass_number(self) -> str:
        """
        Generates the Visit ID (previously called pass number).
        Format kept as: VMS-YYYYMMDD-XXXX
        """
        try:
            today = datetime.now().strftime('%Y%m%d')
            # Use today's count but avoid expensive full scans; indexed by check_in_time
            row = self._fetchone(
                "SELECT COUNT(*) as c FROM visitors WHERE DATE(check_in_time)=DATE('now')"
            )
            count = row["c"] if row else 0
            return f"VMS-{today}-{count + 1:04d}"
        except Exception:
            logging.exception("generate_pass_number fallback")
            return f"VMS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # -------------------------
    # READ / SEARCH operations (with caching where useful)
    # -------------------------
    def find_visitors_by_nric(self, nric: str = "", hp_no: str = "") -> List[Dict]:
        """
        USED BY Registration.search_existing()

        Behaviour:
        - Returns AT MOST ONE dict (wrapped in a list)
        - That dict corresponds to the most recent COMPLETED visit
          for that NRIC / HP.
        - Dict includes fields used for auto-fill.
        """
        try:
            profile = self.get_most_recent_visit_for_autofill(nric=nric, hp_no=hp_no)
            if not profile:
                return []
            return [profile]
        except sqlite3.Error:
            logging.exception("find_visitors_by_nric failed")
            return []

    def get_active_visitors(self) -> List[Dict]:
        """
        Cached for a very short TTL because UI refreshes frequently.
        """
        cached = self._cache.get("active:all")
        if cached is not None:
            return cached

        try:
            rows = self._fetchall(
                '''
                SELECT
                    id, nric, hp_no, first_name, last_name, category,
                    purpose, destination, company, vehicle_number,
                    pass_number, id_number, person_visited, remarks,
                    check_in_time
                FROM visitors
                WHERE check_out_time IS NULL
                ORDER BY check_in_time DESC
                '''
            )
            result = [dict(r) for r in rows]
            self._cache.set("active:all", result)
            return result
        except sqlite3.Error:
            logging.exception("get_active_visitors failed")
            return []

    def get_todays_history(self) -> List[Dict]:
        cached = self._cache.get("history:today")
        if cached is not None:
            return cached
        try:
            today = date.today().strftime("%Y-%m-%d")
            rows = self._fetchall(
                '''
                SELECT
                    name, first_name, last_name, nric, hp_no, category,
                    vehicle_number, company, organization, purpose,
                    destination, person_visited, remarks, pass_number, id_number,
                    check_in_time, check_out_time, duration
                FROM visitors
                WHERE DATE(check_in_time) = ?
                ORDER BY check_in_time DESC
                ''',
                (today,)
            )
            result = [dict(r) for r in rows]
            self._cache.set("history:today", result)
            return result
        except sqlite3.Error:
            logging.exception("get_todays_history failed")
            return []

    def get_all_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        try:
            if start_date and end_date:
                rows = self._fetchall(
                    '''
                    SELECT * FROM visitors
                    WHERE DATE(check_in_time) BETWEEN ? AND ?
                    ORDER BY check_in_time DESC
                    ''',
                    (start_date, end_date)
                )
            else:
                rows = self._fetchall(
                    '''
                    SELECT * FROM visitors
                    ORDER BY check_in_time DESC
                    '''
                )
            return [dict(r) for r in rows]
        except sqlite3.Error:
            logging.exception("get_all_records failed")
            return []

    def get_daily_checkins_current_month(self) -> List[Tuple[date, int]]:
        try:
            rows = self._fetchall(
                '''
                SELECT DATE(check_in_time) as d, COUNT(*) as c
                FROM visitors
                WHERE strftime('%Y-%m', check_in_time) = strftime('%Y-%m', 'now')
                GROUP BY DATE(check_in_time)
                ORDER BY DATE(check_in_time)
                '''
            )
            return [
                (datetime.strptime(r["d"], '%Y-%m-%d').date(), r["c"])
                for r in rows
            ]
        except sqlite3.Error:
            logging.exception("get_daily_checkins_current_month failed")
            return []

    def get_todays_checkin_count(self) -> int:
        cached = self._cache.get("counts:today")
        if cached is not None:
            return cached
        try:
            today = date.today().strftime("%Y-%m-%d")
            row = self._fetchone(
                "SELECT COUNT(*) as c FROM visitors WHERE DATE(check_in_time)=?",
                (today,)
            )
            count = row["c"] if row else 0
            self._cache.set("counts:today", count)
            return count
        except sqlite3.Error:
            logging.exception("get_todays_checkin_count failed")
            return 0

    def get_average_duration(self) -> float:
        cached = self._cache.get("counts:avg_duration")
        if cached is not None:
            return cached
        try:
            row = self._fetchone(
                "SELECT AVG(duration) as avgd FROM visitors WHERE duration IS NOT NULL"
            )
            avgd = float(row["avgd"]) if row and row["avgd"] is not None else 0.0
            self._cache.set("counts:avg_duration", avgd)
            return avgd
        except sqlite3.Error:
            logging.exception("get_average_duration failed")
            return 0.0

    # -------------------------
    # LICENSE storage & retrieval
    # -------------------------
    def save_license(self, license_key: str, device_mac: str, is_active: bool = True) -> bool:
        """
        Stores encrypted license key against device.
        is_active controls whether app should ask for full activation (expiry)
        or simple log-in next time.
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    '''
                    INSERT OR REPLACE INTO license (id, license_key, device_mac, is_active, activation_date)
                    VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''',
                    (license_key, device_mac, 1 if is_active else 0)
                )
                conn.commit()
            # invalidate cache if any license-dependent operations exist
            self._cache.invalidate()
            return True
        except sqlite3.Error:
            logging.exception("save_license failed")
            return False

    def set_license_active(self, active: bool) -> bool:
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE license SET is_active = ? WHERE id = 1",
                    (1 if active else 0,)
                )
                conn.commit()
            self._cache.invalidate()
            return True
        except sqlite3.Error:
            logging.exception("set_license_active failed")
            return False

    def get_license_info(self) -> Optional[Dict]:
        try:
            row = self._fetchone(
                "SELECT id, license_key, device_mac, activation_date, is_active FROM license WHERE id=1"
            )
            if not row:
                return None
            return {
                "id": row["id"],
                "license_key": row["license_key"],
                "device_mac": row["device_mac"],
                "activation_date": row["activation_date"],
                "is_active": bool(row["is_active"]),
            }
        except sqlite3.Error:
            logging.exception("get_license_info failed")
            return None

    def _hash_password(self, user_id: str, password_plain: str) -> str:
        base = f"{user_id}::{password_plain}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def create_user(self, name: str, organization: str, user_id: str, password_plain: str, role: str) -> bool:
        try:
            password_hash = self._hash_password(user_id, password_plain)
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    '''
                    INSERT INTO users (name, organization, user_id, password_hash, role, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    ''',
                    (name, organization, user_id, password_hash, role)
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            logging.exception("create_user integrity error (likely duplicate user_id)")
            return False
        except sqlite3.Error:
            logging.exception("create_user failed")
            return False

    def get_user_by_credentials(self, user_id: str, password_plain: str) -> Optional[Dict]:
        try:
            password_hash = self._hash_password(user_id, password_plain)
            row = self._fetchone(
                '''
                SELECT id, name, organization, user_id, role, is_active, created_at
                FROM users
                WHERE user_id = ? AND password_hash = ?
                LIMIT 1
                ''',
                (user_id, password_hash)
            )
            if not row:
                return None
            return {
                "id": row["id"],
                "name": row["name"],
                "organization": row["organization"],
                "user_id": row["user_id"],
                "role": row["role"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
            }
        except sqlite3.Error:
            logging.exception("get_user_by_credentials failed")
            return None

    def get_user_by_user_id(self, user_id: str) -> Optional[Dict]:
        """Fetch a single user row by user_id (no password check)."""
        try:
            row = self._fetchone(
                '''
                SELECT id, name, organization, user_id, role, is_active, created_at
                FROM users
                WHERE user_id = ?
                LIMIT 1
                ''',
                (user_id,),
            )
            if not row:
                return None
            return {
                "id": row["id"],
                "name": row["name"],
                "organization": row["organization"],
                "user_id": row["user_id"],
                "role": row["role"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
            }
        except sqlite3.Error:
            logging.exception("get_user_by_user_id failed")
            return None

    def list_users(self) -> List[Dict]:
        try:
            rows = self._fetchall(
                '''
                SELECT id, name, organization, user_id, role, is_active, created_at
                FROM users
                ORDER BY created_at ASC
                '''
            )
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "organization": r["organization"],
                    "user_id": r["user_id"],
                    "role": r["role"],
                    "is_active": bool(r["is_active"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        except sqlite3.Error:
            logging.exception("list_users failed")
            return []

    def delete_user(self, user_identifier: Union[int, str]) -> bool:
        try:
            if isinstance(user_identifier, int):
                params = (user_identifier,)
                query = "DELETE FROM users WHERE id = ?"
            else:
                params = (user_identifier,)
                query = "DELETE FROM users WHERE user_id = ?"
            self._execute(query, params)
            return True
        except sqlite3.Error:
            logging.exception("delete_user failed")
            return False

    def update_user_active_status(self, user_identifier: Union[int, str], is_active: bool) -> bool:
        try:
            if isinstance(user_identifier, int):
                params = (1 if is_active else 0, user_identifier)
                query = "UPDATE users SET is_active = ? WHERE id = ?"
            else:
                params = (1 if is_active else 0, user_identifier)
                query = "UPDATE users SET is_active = ? WHERE user_id = ?"
            self._execute(query, params)
            return True
        except sqlite3.Error:
            logging.exception("update_user_active_status failed")
            return False

    # -------------------------
    # BLACKLIST HELPERS (by HP No)
    # -------------------------
    def is_hp_blacklisted(self, hp_no: str) -> bool:
        """Return True if the given HP number is blacklisted."""
        try:
            row = self._fetchone(
                "SELECT 1 FROM blacklist WHERE hp_no = ? LIMIT 1",
                (hp_no,),
            )
            return bool(row)
        except sqlite3.Error:
            logging.exception("is_hp_blacklisted failed")
            return False

    def add_to_blacklist_from_visit(self, hp_no: str, reason: str = "") -> bool:
        """Add an HP No to blacklist using latest visit data (name/NRIC) if available."""
        if not hp_no:
            return False
        try:
            # Try to derive name/NRIC from most recent completed visit
            visit = self.get_most_recent_visit_for_autofill(hp_no=hp_no)
            name = ""
            nric = ""
            if visit:
                fn = visit.get("first_name", "") or ""
                ln = visit.get("last_name", "") or ""
                name = f"{fn} {ln}".strip()
                nric = visit.get("nric", "") or ""

            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    '''
                    INSERT OR REPLACE INTO blacklist (hp_no, name, nric, reason)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (hp_no, name, nric, reason),
                )
                conn.commit()
            return True
        except sqlite3.Error:
            logging.exception("add_to_blacklist_from_visit failed")
            return False

    def get_blacklist(self) -> List[Dict]:
        """Return all blacklisted HP numbers with basic info."""
        try:
            rows = self._fetchall(
                '''
                SELECT id, hp_no, name, nric, reason, created_at
                FROM blacklist
                ORDER BY created_at DESC
                '''
            )
            return [
                {
                    "id": r["id"],
                    "hp_no": r["hp_no"],
                    "name": r["name"],
                    "nric": r["nric"],
                    "reason": r["reason"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]
        except sqlite3.Error:
            logging.exception("get_blacklist failed")
            return []

    def remove_from_blacklist(self, hp_no: str) -> bool:
        """Whitelist an HP No by removing it from the blacklist table."""
        try:
            self._execute("DELETE FROM blacklist WHERE hp_no = ?", (hp_no,))
            return True
        except sqlite3.Error:
            logging.exception("remove_from_blacklist failed")
            return False

    def update_user_role(self, user_identifier: Union[int, str], role: str) -> bool:
        try:
            if isinstance(user_identifier, int):
                params = (role, user_identifier)
                query = "UPDATE users SET role = ? WHERE id = ?"
            else:
                params = (role, user_identifier)
                query = "UPDATE users SET role = ? WHERE user_id = ?"
            self._execute(query, params)
            return True
        except sqlite3.Error:
            logging.exception("update_user_role failed")
            return False
