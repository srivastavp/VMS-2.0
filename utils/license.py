import uuid
import hashlib
import psutil
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import logging

class LicenseManager:
    def __init__(self):
        self.key = b'VMS_2024_SECRET_KEY_FOR_ENCRYPTION_'[:32]  # 32 bytes for Fernet
        self.fernet = Fernet(Fernet.generate_key())
    
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