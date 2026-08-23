# Visitor Management System

A modern, offline desktop application for managing visitor records with a clean and intuitive interface.

## Features

- **Registration Module**: Quick visitor registration with automatic timestamp capture
- **Direct Visitor Pass Printing**: Visitor passes print automatically to a configured
  Windows printer (e.g. a Brother QL-800 label printer) right after registration
- **Dashboard**: Real-time metrics and daily check-in graphs
- **Active Visitors**: Track currently checked-in visitors with one-click checkout and reprint
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

## Running Tests

```bash
python -m unittest discover -s tests
```

Printer-related tests mock the underlying Windows/Qt printer calls, so
they do not require a physical printer or a real display to run.

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

## Visitor Pass Printing (Brother QL-800 / any Windows printer)

Visitor passes print automatically right after a visitor is registered,
sent straight to a configured Windows printer through the normal Windows
print spooler. **No Brother b-PAC SDK is used** — the Brother QL-800 (or
any other label/receipt printer) is treated as a plain Windows printer.
A PDF pass remains available as a fallback (see below).

### 1. Install the printer in Windows

Install the Brother QL-800 using its official Windows driver (from the
Brother support site) as you would install any other printer. Once it
shows up in **Windows Settings → Printers & scanners**, it's ready to be
used by the VMS.

### 2. Select the printer in the VMS

Open **Printer Settings** from the toolbar (top of the main window):

1. Pick the installed printer from the dropdown (click **Refresh** if it
   was just installed).
2. Set the **Label Width** / **Label Height** to match the label roll
   actually loaded in the printer (in mm). The default (62 x 29 mm) is an
   assumption based on the QL-800's box-standard continuous DK tape —
   **confirm this against the actual roll in use** and adjust if needed.
3. Click **Test Print** to send a sample pass to the printer without
   creating any visitor record. Confirm the label prints, is sized
   correctly, and is cut.
4. Click **Save**. The selected printer and label size persist across
   application restarts.

If no printer is explicitly configured yet, the VMS will use the current
Windows default printer and will say so — it will not silently send
passes to an unconfigured/inappropriate printer.

### 3. Normal use

After registering a visitor, the pass prints automatically — no PDF needs
to be opened or manually printed. Reception staff can also reprint a pass
for any currently active visitor from the **Active Visitors** tab using
the **Print Pass** button.

### 4. If the printer is unavailable

Visitor registration always succeeds and is saved to the database first,
independent of printing. If printing fails (printer off, disconnected,
offline, not configured, or any spooler error), a dialog explains the
reason and offers:

- **Retry Print** — try sending the job again (e.g. after reconnecting
  the printer), or
- **Save PDF** — save the same pass as a PDF (CR80 ID-card size) to the
  Desktop as a fallback, useful for troubleshooting, administrative use,
  or printing via another application.

## Security Features

- Parameterized SQL queries prevent injection attacks
- Device-specific license key validation
- Local SQLite database for data security

## Support

For technical support or feature requests, please contact the development team.