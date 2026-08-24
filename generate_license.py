#!/usr/bin/env python3
"""
Offline license key generator for M-Neo VMS.
Run this on the admin/developer machine to create a per-client key.
"""
import hashlib
import sys
from datetime import datetime

from utils.license import DEFAULT_LICENSE_EXPIRY


def generate_license_key(mac: str, expiry_date: str = DEFAULT_LICENSE_EXPIRY) -> str:
    """
    Generate a license key from a MAC address and an expiry date.
    MAC format: e.g. '00:1A:2B:3C:4D:5E' (upper or lower case)
    Expiry format: 'YYYY-MM-DD'
    """
    # Normalize MAC to the exact format used by LicenseManager
    mac = mac.strip().upper()
    if not mac or len(mac.split(":")) != 6:
        raise ValueError("MAC must be in format 00:1A:2B:3C:4D:5E")

    # Validate expiry
    datetime.strptime(expiry_date, "%Y-%m-%d")

    base = f"{mac}_{expiry_date}_MNEO_VMS"
    hash_hex = hashlib.sha256(base.encode()).hexdigest()
    key = "-".join([hash_hex[i:i+4].upper() for i in range(0, 16, 4)])
    return key


def main():
    if len(sys.argv) >= 2:
        mac = sys.argv[1]
        expiry = sys.argv[2] if len(sys.argv) >= 3 else DEFAULT_LICENSE_EXPIRY
    else:
        mac = input("Client MAC address (e.g. 00:1A:2B:3C:4D:5E): ").strip()
        expiry = input(f"Expiry date (YYYY-MM-DD, default {DEFAULT_LICENSE_EXPIRY}): ").strip() or DEFAULT_LICENSE_EXPIRY

    try:
        key = generate_license_key(mac, expiry)
        print("\n--- Generated License Key ---")
        print(key)
        print("Expiry:", expiry)
        print("-----------------------------\n")
        print("Share this key with the client.")
        print("They will enter it in the License Activation dialog.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
