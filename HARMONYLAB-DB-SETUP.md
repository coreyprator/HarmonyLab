# HarmonyLab - Database Setup (Using Existing Cloud SQL)

## Your Existing Infrastructure

From your Super-Flashcards and Etymython projects:

| Setting | Value |
|---------|-------|
| **Project** | `super-flashcards-475210` |
| **Instance** | `flashcards-db` |
| **Instance IP** | `35.224.242.223` |
| **Region** | `us-central1` |
| **Root User** | `sqlserver` |

**Existing Databases on this instance:**
- `LanguageLearning` (Super-Flashcards)
- `Etymython` (Etymython)
- `HarmonyLab` ← **We'll add this**

---

## Step 1: Create HarmonyLab Database

```powershell
# Create the database
gcloud sql databases create HarmonyLab --instance=flashcards-db --project=super-flashcards-475210
```

---

## Step 2: Create HarmonyLab User

```powershell
# Create dedicated user for HarmonyLab
gcloud sql users create harmonylab_user `
  --instance=flashcards-db `
  --password=HarmonyUser2025! `
  --project=super-flashcards-475210
```

---

## Step 3: Grant User Permissions

Go to Cloud SQL Studio:
https://console.cloud.google.com/sql/instances/flashcards-db/studio?project=super-flashcards-475210

Login with:
- **Database**: `master`
- **User**: `sqlserver`
- **Password**: `SqlRoot2025!`

Run this SQL:

```sql
USE HarmonyLab

CREATE USER [harmonylab_user] FOR LOGIN [harmonylab_user]

ALTER ROLE db_owner ADD MEMBER [harmonylab_user]
```

---

## Step 4: Run the Schema

Still in Cloud SQL Studio, switch to HarmonyLab database and run the entire contents of:
`G:\My Drive\Code\Python\Harmony-Lab\HarmonyLab-Schema-v1.0.sql`

**Note**: Remove the `GO` statements if Cloud SQL Studio complains (it sometimes doesn't like them).

Verify with:
```sql
SELECT name FROM sys.tables ORDER BY name
```

Should show: `ChordVocabulary`, `Chords`, `Measures`, `MelodyNotes`, etc.

---

## Step 5: Create .env File

In `G:\My Drive\Code\Python\Harmony-Lab\`, create `.env`:

```ini
# HarmonyLab Environment Configuration
# Database Connection - Cloud SQL (shared instance)

DB_SERVER=35.224.242.223
DB_NAME=HarmonyLab
DB_USER=harmonylab_user
DB_PASSWORD=HarmonyUser2025!
DB_DRIVER=ODBC Driver 17 for SQL Server

# Cloud SQL requires encryption
DB_ENCRYPT=yes
DB_TRUST_SERVER_CERTIFICATE=yes

# Application Settings
DEBUG=true
HOST=0.0.0.0
PORT=8000
```

Or via PowerShell:

```powershell
@"
# HarmonyLab Environment Configuration
DB_SERVER=35.224.242.223
DB_NAME=HarmonyLab
DB_USER=harmonylab_user
DB_PASSWORD=HarmonyUser2025!
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_ENCRYPT=yes
DB_TRUST_SERVER_CERTIFICATE=yes
DEBUG=true
HOST=0.0.0.0
PORT=8000
"@ | Out-File -FilePath "G:\My Drive\Code\Python\Harmony-Lab\.env" -Encoding UTF8
```

---

## Step 6: Update connection.py

The connection.py that VS Code created needs the Cloud SQL connection string format. Replace the `get_connection_string()` function:

```python
def get_connection_string() -> str:
    """Build pyodbc connection string for Cloud SQL."""
    settings = get_settings()
    return (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_server};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
    )
```

---

## Step 7: Test the Connection

```powershell
cd "G:\My Drive\Code\Python\Harmony-Lab"
C:\venvs\Harmony-Lab\Scripts\Activate.ps1

# Quick connection test
python -c "from app.db.connection import get_db_connection; print('Testing...'); conn = get_db_connection(); print('Connected!' if conn else 'Failed'); conn.close() if conn else None"

# Or start the full API
python main.py
```

Visit: http://localhost:8000/docs

---

## Credentials Summary (Save to 1Password)

| Service | User | Password |
|---------|------|----------|
| Cloud SQL Root | `sqlserver` | `SqlRoot2025!` |
| Super-Flashcards | `flashcards_user` | `FlashUser2025!` |
| Etymython | `etymython_user` | `EtymUser2025!` |
| **HarmonyLab** | `harmonylab_user` | `HarmonyUser2025!` |

---

## Quick Reference Commands

```powershell
# List databases on instance
gcloud sql databases list --instance=flashcards-db --project=super-flashcards-475210

# Reset password if needed
gcloud sql users set-password harmonylab_user `
  --instance=flashcards-db `
  --password=NEW_PASSWORD `
  --project=super-flashcards-475210

# Connect via Cloud SQL Studio
# https://console.cloud.google.com/sql/instances/flashcards-db/studio?project=super-flashcards-475210
```

---

## VS Code Guidance

**For VS Code AI**: This project connects to Google Cloud SQL, not a local SQL Server.

- Instance IP: `35.224.242.223`
- Connection uses pyodbc with ODBC Driver 17
- Credentials are in `.env` file
- Test with `python main.py` then visit `/docs`
