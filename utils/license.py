import uuid
import hashlib
import psutil
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import logging

class LicenseManager:
    def __init__(self, db_manager=None):
        self.key = b'VMS_2024_SECRET_KEY_FOR_ENCRYPTION_'[:32]  # 32 bytes for Fernet
        self.fernet = Fernet(Fernet.generate_key())
        self.db_manager = db_manager
    
    def set_db_manager(self, db_manager):
        """Set database manager after initialization"""
        self.db_manager = db_manager
    
    def get_device_mac(self) -> str:
        """Get device MAC address"""
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) 
                           for i in range(0, 8*6, 8)][::-1])
            return mac
        except Exception as e:
            logging.error(f"Error getting MAC address: {e}")
            return "unknown"
    
    def generate_license_key(self, mac_address: str) -> str:
        """Generate license key based on MAC address"""
        try:
            # Create a unique string combining MAC and timestamp
            unique_string = f"{mac_address}_{datetime.now().strftime('%Y%m%d')}"
            
            # Generate hash
            hash_object = hashlib.sha256(unique_string.encode())
            hash_hex = hash_object.hexdigest()
            
            # Format as license key (XXXX-XXXX-XXXX-XXXX)
            license_key = '-'.join([hash_hex[i:i+4].upper() for i in range(0, 16, 4)])
            
            return license_key
        except Exception as e:
            logging.error(f"Error generating license key: {e}")
            return ""
    
    def validate_license(self, license_key: str, mac_address: str) -> bool:
        """Validate license key against MAC address"""
        try:
            expected_key = self.generate_license_key(mac_address)
            return license_key == expected_key
        except Exception as e:
            logging.error(f"Error validating license: {e}")
            return False
    
    def is_licensed(self) -> bool:
        """Check if current device has valid license"""
        if not self.db_manager:
            logging.error("Database manager not set")
            return False
        
        try:
            license_info = self.db_manager.get_license_info()
            current_mac = self.get_device_mac()
            
            if license_info and self.validate_license(license_info['license_key'], current_mac):
                logging.info("Valid license found for current device")
                return True
            
            logging.info("No valid license found")
            return False
        except Exception as e:
            logging.error(f"Error checking license status: {e}")
            return False
    
    def activate_license(self, license_key: str) -> bool:
        """Activate license for current device"""
        if not self.db_manager:
            logging.error("Database manager not set")
            return False
        
        try:
            current_mac = self.get_device_mac()
            
            # Validate the license key
            if not self.validate_license(license_key, current_mac):
                logging.warning(f"Invalid license key attempted: {license_key}")
                return False
            
            # Save to database
            success = self.db_manager.save_license(license_key, current_mac)
            if success:
                logging.info("License activated successfully")
            else:
                logging.error("Failed to save license to database")
            
            return success
        except Exception as e:
            logging.error(f"Error activating license: {e}")
            return False
    
    def get_license_for_current_device(self) -> str:
        """Generate license key for current device"""
        try:
            current_mac = self.get_device_mac()
            return self.generate_license_key(current_mac)
        except Exception as e:
            logging.error(f"Error generating license for current device: {e}")
            return ""
    
    def get_current_device_info(self) -> dict:
        """Get current device information for license display"""
        try:
            return {
                'mac_address': self.get_device_mac(),
                'license_key': self.get_license_for_current_device(),
                'hostname': psutil.cpu_count(),
                'platform': psutil.virtual_memory().total,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Error getting device info: {e}")
            return {'mac_address': 'unknown', 'license_key': ''}
    
    def revoke_license(self) -> bool:
        """Revoke current license (for testing purposes)"""
        if not self.db_manager:
            logging.error("Database manager not set")
            return False
        
        try:
            # Clear license from database
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM license WHERE id = 1')
                conn.commit()
            
            logging.info("License revoked successfully")
            return True
        except Exception as e:
            logging.error(f"Error revoking license: {e}")
            return False
    
    def get_system_info(self) -> dict:
        """Get system information for license validation"""
        try:
            return {
                'mac_address': self.get_device_mac(),
                'hostname': psutil.cpu_count(),
                'platform': psutil.virtual_memory().total,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Error getting system info: {e}")
            return {}