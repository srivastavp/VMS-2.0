import sqlite3
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import logging

class DatabaseManager:
    def __init__(self, db_path: str = "visitor_management.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection for external use"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create visitors table with all required fields
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
                
                # Migrate existing data if needed
                self._migrate_database(cursor)
                
                # Create license table
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
    
    def _migrate_database(self, cursor):
        """Migrate existing database schema to new schema"""
        try:
            # Check if new columns exist
            cursor.execute("PRAGMA table_info(visitors)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Add new columns if they don't exist
            new_columns = {
                'nric': 'TEXT',
                'hp_no': 'TEXT',
                'first_name': 'TEXT',
                'last_name': 'TEXT',
                'category': 'TEXT',
                'destination': 'TEXT',
                'company': 'TEXT',
                'pass_number': 'TEXT',
                'remarks': 'TEXT'
            }
            
            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    try:
                        cursor.execute(f'ALTER TABLE visitors ADD COLUMN {col_name} {col_type}')
                        logging.info(f"Added column {col_name} to visitors table")
                    except sqlite3.Error as e:
                        logging.warning(f"Could not add column {col_name}: {e}")
            
            # Migrate existing name data to first_name and last_name if needed
            if 'first_name' in columns:
                cursor.execute('''
                    UPDATE visitors 
                    SET first_name = name, last_name = ''
                    WHERE (first_name IS NULL OR first_name = '') AND name IS NOT NULL
                ''')
                
        except sqlite3.Error as e:
            logging.error(f"Database migration error: {e}")
    
    def add_visitor(self, nric: str = None, hp_no: str = None, first_name: str = None,
                   last_name: str = None, category: str = None, purpose: str = None,
                   destination: str = None, company: str = None, vehicle_number: str = None,
                   pass_number: str = None, remarks: str = None, person_visited: str = None,
                   name: str = None, organization: str = None, check_in_time: datetime = None) -> bool:
        """Add a new visitor to the database with explicit timestamp"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Use explicit datetime.now() for consistent timestamp
                if check_in_time is None:
                    check_in_time = datetime.now()
                
                # Format timestamp in ISO format for consistency
                check_in_time_str = check_in_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Build full name if separate first/last provided
                if not name:
                    if first_name and last_name:
                        name = f"{first_name} {last_name}".strip()
                    elif first_name:
                        name = first_name
                    elif last_name:
                        name = last_name
                
                # Backward compatibility: if old parameters provided, use them
                if not first_name and name:
                    # Split name into first and last
                    name_parts = name.split(' ', 1)
                    first_name = name_parts[0] if name_parts else ''
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Ensure required fields have defaults
                if not first_name:
                    first_name = ''
                if not last_name:
                    last_name = ''
                if not name:
                    name = f"{first_name} {last_name}".strip() or 'Unknown'
                if not category:
                    category = 'Visitor'
                if not purpose:
                    purpose = ''
                if not destination:
                    destination = ''
                if not person_visited:
                    person_visited = ''
                
                cursor.execute('''
                    INSERT INTO visitors (nric, hp_no, first_name, last_name, name, category,
                                        purpose, destination, company, vehicle_number,
                                        pass_number, remarks, person_visited, organization,
                                        check_in_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nric, hp_no, first_name, last_name, name, category, purpose,
                      destination, company, vehicle_number, pass_number, remarks,
                      person_visited, organization, check_in_time_str))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error adding visitor: {e}")
            return False
    
    def find_existing_visitor(self, nric: str = None, hp_no: str = None) -> Optional[Dict]:
        """Find an existing visitor by NRIC or HP number"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if nric:
                    cursor.execute('''
                        SELECT nric, hp_no, first_name, last_name, name, category,
                               purpose, destination, company, vehicle_number, remarks
                        FROM visitors
                        WHERE nric = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                    ''', (nric,))
                elif hp_no:
                    cursor.execute('''
                        SELECT nric, hp_no, first_name, last_name, name, category,
                               purpose, destination, company, vehicle_number, remarks
                        FROM visitors
                        WHERE hp_no = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                    ''', (hp_no,))
                else:
                    return None
                
                result = cursor.fetchone()
                if result:
                    columns = ['nric', 'hp_no', 'first_name', 'last_name', 'name', 'category',
                              'purpose', 'destination', 'company', 'vehicle_number', 'remarks']
                    return dict(zip(columns, result))
                return None
        except sqlite3.Error as e:
            logging.error(f"Error finding existing visitor: {e}")
            return None
    
    def generate_pass_number(self) -> str:
        """Generate a unique pass number in format VMS-YYYYMMDD-XXXX"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM visitors
                    WHERE DATE(check_in_time) = DATE('now')
                ''')
                count = cursor.fetchone()[0]
                pass_num = f"VMS-{today}-{count + 1:04d}"
                return pass_num
        except sqlite3.Error as e:
            logging.error(f"Error generating pass number: {e}")
            # Fallback to timestamp-based pass
            return f"VMS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    def get_active_visitors(self) -> List[Dict]:
        """Get all visitors who haven't checked out"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, nric, hp_no, first_name, last_name, name, category,
                           purpose, destination, company, vehicle_number, pass_number,
                           person_visited, organization, check_in_time
                    FROM visitors 
                    WHERE check_out_time IS NULL
                    ORDER BY check_in_time DESC
                ''')
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting active visitors: {e}")
            return []
    
    def checkout_visitor(self, visitor_id: int) -> bool:
        """Check out a visitor with explicit timestamp"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Use explicit datetime.now() for consistent timestamp
                checkout_time = datetime.now()
                checkout_time_str = checkout_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Get check-in time
                cursor.execute('SELECT check_in_time FROM visitors WHERE id = ?', (visitor_id,))
                result = cursor.fetchone()
                if not result:
                    return False
                
                # Parse check-in time - handle both ISO format and string format
                check_in_str = result[0]
                try:
                    if isinstance(check_in_str, str):
                        # Try parsing ISO format first
                        try:
                            check_in_time = datetime.fromisoformat(check_in_str)
                        except ValueError:
                            # Fallback to strptime
                            check_in_time = datetime.strptime(check_in_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        check_in_time = datetime.fromisoformat(check_in_str)
                except Exception as e:
                    logging.error(f"Error parsing check-in time: {e}")
                    return False
                
                duration = int((checkout_time - check_in_time).total_seconds() // 60)  # minutes
                
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
    
    def get_todays_history(self) -> List[Dict]:
        """Get all visitors who checked in today"""
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
    
    def get_all_records(self, start_date: Optional[date] = None, 
                       end_date: Optional[date] = None) -> List[Dict]:
        """Get all visitor records with optional date filtering"""
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
        except sqlite3.Error as e:
            logging.error(f"Error getting all records: {e}")
            return []
    
    def get_daily_checkins_current_month(self) -> List[Tuple[date, int]]:
        """Get daily check-in counts for the current month"""
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
                
                return [(datetime.strptime(row[0], '%Y-%m-%d').date(), row[1]) 
                       for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Error getting daily check-ins: {e}")
            return []
    
    def get_todays_checkin_count(self) -> int:
        """Get count of today's check-ins"""
        try:
            today = date.today()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM visitors 
                    WHERE DATE(check_in_time) = ?
                ''', (today,))
                
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logging.error(f"Error getting today's check-in count: {e}")
            return 0
    
    def get_average_duration(self) -> float:
        """Get average duration of visits in minutes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT AVG(duration) FROM visitors 
                    WHERE duration IS NOT NULL
                ''')
                
                result = cursor.fetchone()[0]
                return result if result else 0.0
        except sqlite3.Error as e:
            logging.error(f"Error getting average duration: {e}")
            return 0.0
    
    def save_license(self, license_key: str, device_mac: str) -> bool:
        """Save license information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO license (id, license_key, device_mac)
                    VALUES (1, ?, ?)
                ''', (license_key, device_mac))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error saving license: {e}")
            return False
    
    def get_license_info(self) -> Optional[Dict]:
        """Get license information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM license WHERE id = 1')
                result = cursor.fetchone()
                
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                return None
        except sqlite3.Error as e:
            logging.error(f"Error getting license info: {e}")
            return None