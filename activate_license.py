#!/usr/bin/env python3
"""
Quick script to activate license for current device
"""
from database import DatabaseManager
from utils.license import LicenseManager

def main():
    print("VMS License Activation Tool")
    print("=" * 50)
    
    # Initialize managers
    db_manager = DatabaseManager()
    license_manager = LicenseManager()
    license_manager.set_db_manager(db_manager)
    
    # Get device info
    device_info = license_manager.get_current_device_info()
    print(f"\nDevice MAC Address: {device_info['mac_address']}")
    print(f"Generated License Key: {device_info['license_key']}")
    
    # Activate license
    print("\nActivating license...")
    if license_manager.activate_license(device_info['license_key']):
        print("✓ License activated successfully!")
        print("\nYou can now run the application with: python main.py")
    else:
        print("✗ Failed to activate license")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
