import uuid
import hashlib
import base64
import logging
from datetime import datetime, time
from cryptography.fernet import Fernet


class LicenseManager:
    def __init__(self, db_manager=None):
        self.db_manager = db_manager

    # ---------------------------------------------------------
    # DEVICE IDENTIFIER (MAC ADDRESS)
    # ---------------------------------------------------------
    def get_device_mac(self) -> str:
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                           for i in range(0, 8 * 6, 8)][::-1])
            return mac.upper()
        except Exception as e:
            logging.error(f"Error getting MAC address: {e}")
            return "UNKNOWN"

    # ---------------------------------------------------------
    # ENCRYPTION (Bound to Device MAC)
    # ---------------------------------------------------------
    def _get_encryption_key(self):
        """
        The key is derived from the MAC address.
        Copying DB to another machine breaks decryption.
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

    # ---------------------------------------------------------
    # LICENSE KEY GENERATION
    # ---------------------------------------------------------
    def generate_license_key(self, mac: str, expiry_date: str) -> str:
        """
        Vendor uses this externally to generate the user’s license key.
        """
        base_string = f"{mac}_{expiry_date}_MNEO_VMS"
        hash_hex = hashlib.sha256(base_string.encode()).hexdigest()

        # First 16 chars → XXXX-XXXX-XXXX-XXXX
        key = "-".join([hash_hex[i:i+4].upper() for i in range(0, 16, 4)])
        return key

    def validate_license(self, input_key: str, expiry_date: str) -> bool:
        mac = self.get_device_mac()
        expected = self.generate_license_key(mac, expiry_date)
        return input_key == expected

    # ---------------------------------------------------------
    # MAIN LICENSE VALIDATION USED BY APP
    # ---------------------------------------------------------
    def is_licensed(self) -> bool:

        if not self.db_manager:
            return False

        info = self.db_manager.get_license_info()
        if not info or not info.get("license_key"):
            return False

        try:
            decrypted = self.decrypt(info["license_key"])

            # Format must be: "<licensekey>|<YYYY-MM-DD>"
            if "|" not in decrypted:
                return False

            key, expiry_str = decrypted.split("|")
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()

            # License expires at EXACTLY 10:00 AM on the expiry date
            expiry_time = datetime.combine(expiry_date, time(10, 0))

            if datetime.now() > expiry_time:
                logging.warning(f"License expired on {expiry_time}")
                return False

            # Finally check key is correct for this machine
            return self.validate_license(key, expiry_str)

        except Exception as e:
            logging.error(f"License validation error: {e}")
            return False

    # ---------------------------------------------------------
    # STORE LICENSE IN DATABASE
    # ---------------------------------------------------------
    def activate_license(self, input_key: str, expiry_date: str) -> bool:
        if not self.validate_license(input_key, expiry_date):
            return False

        token = f"{input_key}|{expiry_date}"
        encrypted = self.encrypt(token)

        return self.db_manager.save_license(encrypted, self.get_device_mac())

    # ---------------------------------------------------------
    # SHOW MAC + SAMPLE KEY ON ACTIVATION SCREEN
    # ---------------------------------------------------------
    def get_current_device_info(self, expiry_date: str = None) -> dict:
        mac = self.get_device_mac()
        example = self.generate_license_key(mac, expiry_date or "2026-01-01")
        return {
            "mac_address": mac,
            "sample_license_key": example
        }

    # ---------------------------------------------------------
    # REMOVE LICENSE (Admin use)
    # ---------------------------------------------------------
    def revoke_license(self) -> bool:
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM license WHERE id = 1")
                conn.commit()
            return True
        except Exception:
            return False
