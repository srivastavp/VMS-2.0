import uuid
import hashlib
import base64
import logging
from datetime import datetime, time
from cryptography.fernet import Fernet


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
    # KEY GENERATION
    # --------------------
    def generate_license_key(self, mac: str, expiry_date: str) -> str:
        """
        MAC + expiry date (YYYY-MM-DD)
        MUST match the admin-generated key.
        """
        base_string = f"{mac}_{expiry_date}_MNEO_VMS"
        hash_hex = hashlib.sha256(base_string.encode()).hexdigest()
        # Format into xxxx-xxxx-xxxx-xxxx (first 16 chars of hash)
        key = "-".join([hash_hex[i:i+4].upper() for i in range(0, 16, 4)])
        return key

    def validate_license(self, input_key: str, expiry_date: str) -> bool:
        mac = self.get_device_mac()
        expected = self.generate_license_key(mac, expiry_date)
        return input_key == expected

    # --------------------
    # CHECK LICENSE
    # --------------------
    def is_licensed(self) -> bool:
        """Check DB if license exists, active and is still valid."""
        if not self.db_manager:
            return False

        info = self.db_manager.get_license_info()
        if not info or not info.get("license_key"):
            return False

        # if license exists but currently deactivated (logout) treat as not licensed
        if not info.get("is_active", False):
            return False

        try:
            decrypted = self.decrypt(info["license_key"])
            # license string format: <plain_key>|<expiry_date>
            if "|" not in decrypted:
                return False

            key, expiry_str = decrypted.split("|")
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()

            expiry_time = datetime.combine(expiry_date, time(10, 0))
            if datetime.now() > expiry_time:
                logging.warning("License expired.")
                return False

            return self.validate_license(key, expiry_str)
        except Exception as e:
            logging.error(f"License validation error: {e}")
            return False

    # --------------------
    # ACTIVATE / STORE LICENSE
    # --------------------
    def activate_license(self, input_key: str, expiry_date: str) -> bool:
        """Activates license with expiry and stores encrypted string."""
        if not self.validate_license(input_key, expiry_date):
            return False

        combo = f"{input_key}|{expiry_date}"
        encrypted = self.encrypt(combo)
        return self.db_manager.save_license(encrypted, self.get_device_mac(), is_active=True)

    # --------------------
    # LOGIN (after logout) — only key is requested
    # --------------------
    def login_with_key(self, input_key: str) -> bool:
        """
        When the DB has a stored (encrypted) license but is_active=0 (logged out),
        the user can provide just the key. We compare against stored key and expiry.
        If matches and not expired, mark license active and return True.
        """
        try:
            info = self.db_manager.get_license_info()
            if not info or not info.get("license_key"):
                return False

            # decrypt stored encrypted string (this will raise if mac changed / copy)
            decrypted = self.decrypt(info["license_key"])
            if "|" not in decrypted:
                return False

            stored_key, expiry_str = decrypted.split("|")
            # check supplied key matches stored key
            if input_key != stored_key:
                return False

            # check expiry
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            expiry_time = datetime.combine(expiry_date, time(10, 0))
            if datetime.now() > expiry_time:
                logging.warning("Stored license expired.")
                return False

            # OK: mark license active
            return self.db_manager.set_license_active(True)
        except Exception as e:
            logging.error(f"login_with_key error: {e}")
            return False

    # --------------------
    # DISPLAY INFO
    # --------------------
    def get_current_device_info(self, expiry_date: str = None) -> dict:
        mac = self.get_device_mac()
        example_key = self.generate_license_key(mac, expiry_date or "2026-01-01")
        return {
            'mac_address': mac,
            'sample_license_key': example_key
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
