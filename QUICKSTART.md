# Quick Start Guide - Harmony Lab

## Prerequisites Checklist

Before running the API, ensure you have:

- [x] Virtual environment created at `C:\venvs\Harmony-Lab`
- [x] All dependencies installed
- [ ] Cloud SQL instance with HarmonyLab database created
- [ ] Database schema executed (`HarmonyLab-Schema-v1.0.sql`)
- [ ] `.env` file created with your database credentials

## Step 1: Configure Environment

Create your `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your database details:

```env
DB_SERVER=<your-cloud-sql-ip>
DB_NAME=HarmonyLab
DB_USER=sqlserver
DB_PASSWORD=<your-password>
DB_DRIVER=ODBC Driver 17 for SQL Server
```

## Step 2: Verify ODBC Driver

Check if you have the SQL Server ODBC driver installed:

```powershell
# List available ODBC drivers
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"}
```

If you don't have "ODBC Driver 17 for SQL Server", download from:
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

## Step 3: Run Database Schema

Connect to your Cloud SQL instance and run the schema:

```powershell
# Option 1: Using gcloud (if you have Cloud SQL proxy)
gcloud sql connect <your-instance-name> --user=sqlserver

# Option 2: Using sqlcmd
sqlcmd -S <your-instance-ip> -U sqlserver -P <password> -i HarmonyLab-Schema-v1.0.sql
```

Verify tables were created:
```sql
SELECT name FROM sys.tables ORDER BY name;
-- Should show: Chords, ChordVocabulary, Measures, MelodyNotes, 
--              QuizAttempts, RomanNumeralVocabulary, Sections, Songs, UserSongProgress
```

## Step 4: Start the API Server

```powershell
# Navigate to project directory
cd "G:\My Drive\Code\Python\Harmony-Lab"

# Activate virtual environment
C:\venvs\Harmony-Lab\Scripts\Activate.ps1

# Run the server
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 5: Test the API

Open your browser to:

**Interactive API Documentation**:
http://localhost:8000/docs

**Health Check**:
http://localhost:8000/health

**Available Endpoints**:
- `GET /api/v1/songs` - List all songs
- `POST /api/v1/songs` - Create a new song
- `GET /api/v1/vocabulary/chord-symbols` - Get chord vocabulary
- `GET /api/v1/vocabulary/roman-numerals` - Get roman numeral vocabulary

## Step 6: Create Your First Song

Using the interactive docs at http://localhost:8000/docs:

1. Click on `POST /api/v1/songs`
2. Click "Try it out"
3. Use this example:

```json
{
  "title": "Girl from Ipanema",
  "composer": "Antonio Carlos Jobim",
  "original_key": "F Major",
  "tempo_marking": "Moderate Bossa",
  "genre": "Bossa Nova",
  "time_signature": "4/4"
}
```

4. Click "Execute"
5. You should get a `201 Created` response with the song ID

## Troubleshooting

### Database Connection Issues

**Error**: "Failed to connect to database"
- Check your `.env` file has correct credentials
- Verify Cloud SQL instance is running
- Check firewall rules allow your IP
- Ensure HarmonyLab database exists

**Error**: "ODBC Driver not found"
- Install ODBC Driver 17 for SQL Server
- Update `DB_DRIVER` in `.env` if using different version

### Import Errors

**Error**: "No module named 'app'"
- Make sure you're running from project root directory
- Verify `__init__.py` files exist in all packages

**Error**: "No module named 'config'"
- Same as above
- Try: `python -m main` instead of `python main.py`

### Port Already in Use

**Error**: "Address already in use"
- Another process is using port 8000
- Kill the process or use different port:
  ```powershell
  python -m uvicorn main:app --reload --port 8001
  ```

## Next Development Steps

Once the API is running:

1. **Test all endpoints** using the interactive docs
2. **Create remaining routes**:
   - Measures CRUD
   - Chords CRUD
   - File import endpoints
3. **Implement MIDI parser** in `app/services/midi_parser.py`
4. **Implement MusicXML parser** in `app/services/musicxml_parser.py`
5. **Build frontend** for data entry and quiz modes

## Development Workflow

```powershell
# Start development server with auto-reload
python main.py

# Add a new route
# 1. Create file in app/api/routes/
# 2. Define endpoints using @router decorator
# 3. Import in main.py
# 4. Add to app.include_router()

# Test manually at http://localhost:8000/docs

# Add tests in tests/ directory
pytest
```

## VS Code Integration

If using VS Code:

1. Select Python interpreter: `C:\venvs\Harmony-Lab\Scripts\python.exe`
2. Install Python extension
3. Debug configuration will use this interpreter

## Questions?

Refer to:
- [HarmonyLab-Kickoff.md](HarmonyLab-Kickoff.md) - Full project vision
- [harmony-lab-infra-setup.md](harmony-lab-infra-setup.md) - GCP deployment
- [SETUP-COMPLETE.md](SETUP-COMPLETE.md) - Detailed setup summary

**Ready to start coding!** 🎵
