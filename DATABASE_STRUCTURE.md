# VMS Database Structure

## Database File
- **File**: `visitor_management.db`
- **Type**: SQLite3
- **Location**: Root directory of the project

---

## Table 1: `visitors`

### Description
Main table storing all visitor records including check-in, check-out, and visitor details.

### Schema

| Column Name      | Data Type | Constraints           | Description                                    |
|------------------|-----------|----------------------|------------------------------------------------|
| `id`             | INTEGER   | PRIMARY KEY AUTOINCREMENT | Unique visitor record ID                       |
| `nric`           | TEXT      | NULL                 | National Registration Identity Card number     |
| `hp_no`          | TEXT      | NULL                 | Mobile/HP number                               |
| `first_name`     | TEXT      | NOT NULL             | Visitor's first name                           |
| `last_name`      | TEXT      | NOT NULL             | Visitor's last name                            |
| `name`           | TEXT      | NOT NULL             | Full name (first_name + last_name)             |
| `category`       | TEXT      | NOT NULL             | Visitor category (e.g., Visitor, Contractor)   |
| `purpose`        | TEXT      | NOT NULL             | Purpose of visit                               |
| `destination`    | TEXT      | NOT NULL             | Destination within premises                    |
| `company`        | TEXT      | NULL                 | Company/Organization name                      |
| `vehicle_number` | TEXT      | NULL                 | Vehicle registration number                    |
| `pass_number`    | TEXT      | NULL                 | Generated pass number (VMS-YYYYMMDD-XXXX)      |
| `remarks`        | TEXT      | NULL                 | Additional remarks/notes                       |
| `person_visited` | TEXT      | NOT NULL             | Name of person being visited                   |
| `organization`   | TEXT      | NULL                 | Organization (legacy field, use company)       |
| `check_in_time`  | DATETIME  | NOT NULL             | Check-in timestamp (YYYY-MM-DD HH:MM:SS)       |
| `check_out_time` | DATETIME  | NULL                 | Check-out timestamp (YYYY-MM-DD HH:MM:SS)      |
| `duration`       | INTEGER   | NULL                 | Visit duration in minutes                      |
| `created_at`     | DATETIME  | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp                      |

### Indexes
- Primary key on `id`
- Recommended indexes (not created by default):
  - `idx_check_in_time` on `check_in_time` for date-based queries
  - `idx_nric` on `nric` for existing visitor lookup
  - `idx_hp_no` on `hp_no` for existing visitor lookup
  - `idx_name` on `first_name, last_name` for name-based lookup

### Sample Data
```sql
INSERT INTO visitors (
    nric, hp_no, first_name, last_name, name, category, purpose, 
    destination, company, vehicle_number, pass_number, remarks, 
    person_visited, check_in_time
) VALUES (
    'S1234567A', '91234567', 'John', 'Doe', 'John Doe', 'Visitor',
    'Meeting', 'Office Block A', 'ABC Corp', 'SBA1234X', 'VMS-20251106-0001',
    'VIP Guest', 'Jane Smith', '2025-11-06 09:00:00'
);
```

---

## Table 2: `license`

### Description
Stores license activation information for the application (hardware-bound licensing).

### Schema

| Column Name       | Data Type | Constraints           | Description                                    |
|-------------------|-----------|----------------------|------------------------------------------------|
| `id`              | INTEGER   | PRIMARY KEY          | License record ID (always 1)                   |
| `license_key`     | TEXT      | NOT NULL             | License key (XXXX-XXXX-XXXX-XXXX format)       |
| `device_mac`      | TEXT      | NOT NULL             | MAC address of licensed device                 |
| `activation_date` | DATETIME  | DEFAULT CURRENT_TIMESTAMP | License activation timestamp                   |
| `is_active`       | BOOLEAN   | DEFAULT 1            | License active status (1=active, 0=inactive)   |

### Notes
- Only one license record exists (id=1)
- License key is generated based on device MAC address
- Use `INSERT OR REPLACE` to update license

### Sample Data
```sql
INSERT OR REPLACE INTO license (id, license_key, device_mac) 
VALUES (1, '07A8-E038-6C62-15EA', 'ac:5a:fc:a3:6a:14');
```

---

## Key Relationships

### Active Visitors
- Query: `SELECT * FROM visitors WHERE check_out_time IS NULL`
- Shows all visitors currently on premises

### Today's History
- Query: `SELECT * FROM visitors WHERE DATE(check_in_time) = DATE('now')`
- Shows all visitors who checked in today

### Checked Out Visitors
- Query: `SELECT * FROM visitors WHERE check_out_time IS NOT NULL`
- Shows all visitors who have checked out

---

## Important Queries

### 1. Get Active Visitors
```sql
SELECT id, nric, hp_no, first_name, last_name, name, category,
       purpose, destination, company, vehicle_number, pass_number,
       person_visited, organization, check_in_time
FROM visitors 
WHERE check_out_time IS NULL
ORDER BY check_in_time DESC;
```

### 2. Check Out Visitor
```sql
UPDATE visitors 
SET check_out_time = '2025-11-06 17:30:00', 
    duration = 510  -- minutes
WHERE id = 1;
```

### 3. Find Existing Visitor by Name
```sql
SELECT nric, hp_no, first_name, last_name, name, category,
       purpose, destination, company, vehicle_number, remarks
FROM visitors
WHERE LOWER(first_name) = LOWER('John') 
  AND LOWER(last_name) = LOWER('Doe')
ORDER BY created_at DESC
LIMIT 1;
```

### 4. Get All Records with Date Filter
```sql
SELECT * FROM visitors 
WHERE DATE(check_in_time) BETWEEN '2025-11-01' AND '2025-11-30'
ORDER BY check_in_time DESC;
```

### 5. Filter by Organization
```sql
SELECT * FROM visitors 
WHERE company LIKE '%ABC Corp%'
ORDER BY check_in_time DESC;
```

---

## Duration Calculation

Duration is automatically calculated when a visitor checks out:

```python
duration = int((checkout_time - check_in_time).total_seconds() // 60)  # minutes
```

**Display Format:**
- If duration >= 60 minutes: `"Xh Ym"` (e.g., "2h 15m")
- If duration < 60 minutes: `"Ym"` (e.g., "45m")
- If not checked out: `"Active"`

---

## Pass Number Format

Auto-generated pass numbers follow this format:
```
VMS-YYYYMMDD-XXXX
```

Example: `VMS-20251106-0001`

Where:
- `VMS` = System prefix
- `YYYYMMDD` = Date (e.g., 20251106)
- `XXXX` = Sequential number for that day (0001, 0002, etc.)

---

## Database Backup

To backup the database:
```bash
# Copy the SQLite file
copy visitor_management.db visitor_management_backup_YYYYMMDD.db
```

To restore:
```bash
# Replace with backup
copy visitor_management_backup_YYYYMMDD.db visitor_management.db
```

---

## Migration Notes

The database includes automatic migration logic in `_migrate_database()` that:
1. Checks for missing columns
2. Adds new columns if they don't exist
3. Migrates old data to new schema format
4. Preserves existing data during updates

---

## Database Location

Default: `visitor_management.db` in project root directory

To change location, modify in `database.py`:
```python
db_manager = DatabaseManager(db_path="path/to/your/database.db")
```
