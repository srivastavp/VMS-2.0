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
                
                # Create visitors table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS visitors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        vehicle_number TEXT,
                        organization TEXT,
                        person_visited TEXT NOT NULL,
                        purpose TEXT NOT NULL,
                        check_in_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        check_out_time DATETIME,
                        duration INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
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
    
    def add_visitor(self, name: str, vehicle_number: str, organization: str, 
                   person_visited: str, purpose: str) -> bool:
        """Add a new visitor to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO visitors (name, vehicle_number, organization, 
                                        person_visited, purpose)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, vehicle_number, organization, person_visited, purpose))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error adding visitor: {e}")
            return False
    
    def get_active_visitors(self) -> List[Dict]:
        """Get all visitors who haven't checked out"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, vehicle_number, organization, person_visited, 
                           purpose, check_in_time
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
        """Check out a visitor"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                checkout_time = datetime.now()
                
                # Get check-in time
                cursor.execute('SELECT check_in_time FROM visitors WHERE id = ?', (visitor_id,))
                result = cursor.fetchone()
                if not result:
                    return False
                
                check_in_time = datetime.fromisoformat(result[0])
                duration = int((checkout_time - check_in_time).total_seconds() // 60)  # minutes
                
                cursor.execute('''
                    UPDATE visitors 
                    SET check_out_time = ?, duration = ?
                    WHERE id = ?
                ''', (checkout_time, duration, visitor_id))
                
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
                    SELECT name, vehicle_number, organization, purpose, 
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