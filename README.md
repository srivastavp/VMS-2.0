# Visitor Management System

A modern, offline desktop application for managing visitor records with a clean and intuitive interface.

## Features

- **Registration Module**: Quick visitor registration with automatic timestamp capture
- **Dashboard**: Real-time metrics and daily check-in graphs
- **Active Visitors**: Track currently checked-in visitors with one-click checkout
- **History Tracking**: View today's visitor history and all records
- **Excel Export**: Export filtered records to Excel format
- **License Protection**: Device-specific license key validation
- **Modern UI**: Clean, responsive interface with professional styling

## Requirements

- Python 3.8+
- PyQt5
- SQLite (included with Python)
- Additional dependencies listed in requirements.txt

## Installation

1. Clone or download the application
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

```bash
python main.py
```

## Building Executable

To create a Windows executable:

```bash
pip install pyinstaller
python build_executable.py
```

The executable will be created in the `dist` directory.

## License Key Generation

The application uses device MAC address for license validation. To generate a license key for a specific device:

1. Get the device MAC address
2. Use the LicenseManager.generate_license_key() method
3. The license key format is: XXXX-XXXX-XXXX-XXXX

## Database

The application uses SQLite database (`visitor_management.db`) which is automatically created on first run. The database includes:

- `visitors` table: Stores all visitor records
- `license` table: Stores license information

## Features Overview

### Registration
- Visitor name, vehicle number, organization
- Person being visited and purpose
- Automatic check-in timestamp

### Dashboard
- Today's check-ins count (clickable)
- Active visitors count
- Average visit duration
- Daily check-ins graph for current month

### Active Visitors
- Real-time list of checked-in visitors
- One-click checkout functionality
- Automatic duration calculation

### History
- Today's complete visitor history
- Check-in/check-out times and durations
- Visual status indicators

### All Records
- Complete visitor database
- Date range filtering
- Excel export functionality

## Security Features

- Parameterized SQL queries prevent injection attacks
- Device-specific license key validation
- Local SQLite database for data security

## Support

For technical support or feature requests, please contact the development team.