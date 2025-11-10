import uuid
import hashlib
import psutil
import base64

from cryptography.fernet import Fernet
from datetime import datetime
import logging


class LicenseManager:
    def __init__(self, db_manager=None):
        self.db_manager = db_manager

    # --------------------
    # DEVICE IDENTIFIER
    # --------------------
    def get_device_mac(self) -> str:
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                           for i in range(0, 8 * 6, 8)][::-1])
            return mac.upper()
        except Exception as e:
            logging.error(f"Error getting MAC address: {e}")
            return "UNKNOWN"

    # --------------------
    # KEY GENERATION (unchanged)
    # --------------------
    def generate_license_key(self, mac_address: str) -> str:
        try:
            unique_string = f"{mac_address}_{datetime.now().strftime('%Y%m%d')}"
            hash_hex = hashlib.sha256(unique_string.encode()).hexdigest()
            return '-'.join([hash_hex[i:i+4].upper() for i in range(0, 16, 4)])
        except:
            return ""

    # --------------------
    # ENCRYPTION HELPERS
    # --------------------
    def _get_encryption_key(self):
        """
        Generate encryption key derived from MAC so that
        database copied to another system becomes invalid.
        """
        mac = self.get_device_mac()
        base = f"MNEO_VMS_SALT_{mac}"
        key = hashlib.sha256(base.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, text: str) -> str:
        cipher = self._get_encryption_key()
        return cipher.encrypt(text.encode()).decode()

    def decrypt(self, text: str) -> str:
        cipher = self._get_encryption_key()
        return cipher.decrypt(text.encode()).decode()

    # --------------------
    # VALIDATION
    # --------------------
    def validate_license(self, license_key_plain: str) -> bool:
        current_mac = self.get_device_mac()
        expected = self.generate_license_key(current_mac)
        return license_key_plain == expected

    # --------------------
    # CHECK IF LICENSE IS VALID
    # --------------------
    def is_licensed(self) -> bool:
        if not self.db_manager:
            return False

        info = self.db_manager.get_license_info()
        if not info or not info.get("license_key"):
            return False

        try:
            decrypted = self.decrypt(info["license_key"])
            return self.validate_license(decrypted)
        except:
            return False

    # --------------------
    # ACTIVATE LICENSE
    # --------------------
    def activate_license(self, input_key: str) -> bool:
        if not self.validate_license(input_key):
            return False

        encrypted = self.encrypt(input_key)
        return self.db_manager.save_license(encrypted, self.get_device_mac())

    # --------------------
    # DISPLAY INFO
    # --------------------
    def get_current_device_info(self) -> dict:
        mac = self.get_device_mac()
        return {
            'mac_address': mac,
            'license_key': self.generate_license_key(mac),
            'timestamp': datetime.now().isoformat()
        }

    # --------------------
    # REVOKE LICENSE
    # --------------------
    def revoke_license(self) -> bool:
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM license WHERE id = 1")
                conn.commit()
            return True
        except:
            return False
