# Harmony Lab - Setup Summary

**Date**: December 26, 2025
**Project Lead**: Corey
**Coder Agent**: Claude (Sonnet 4.5)

## Environment Setup Complete ✓

### Virtual Environment
- **Location**: `C:\venvs\Harmony-Lab`
- **Python Version**: 3.12.10
- **Status**: Created and configured

### Installed Packages

**Core Backend (FastAPI)**:
- fastapi==0.127.1
- uvicorn[standard]==0.40.0
- pyodbc==5.3.0
- pydantic==2.12.5
- pydantic-settings==2.12.0
- python-dotenv==1.2.1

**Music Processing**:
- mido==1.3.3 (MIDI parsing)
- music21==9.9.1 (MusicXML parsing)
- python-multipart==0.0.21 (file uploads)

## Project Structure

```
G:\My Drive\Code\Python\Harmony-Lab\
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── songs.py           ✓ CRUD operations for songs
│   │       ├── sections.py        ✓ Section management
│   │       └── vocabulary.py      ✓ Chord/roman numeral lookups
│   ├── db/
│   │   ├── __init__.py
│   │   └── connection.py          ✓ MS SQL connection handling
│   ├── models/
│   │   └── __init__.py            ✓ All Pydantic models
│   └── services/
│       └── __init__.py            (ready for MIDI/MusicXML parsers)
├── config/
│   ├── __init__.py
│   └── settings.py                ✓ Environment configuration
├── tests/                         (ready for test files)
├── main.py                        ✓ FastAPI application entry point
├── requirements.txt               ✓ Package dependencies
├── .env.example                   ✓ Environment template
├── .gitignore                     ✓ Git ignore patterns
├── README.md                      ✓ Project documentation
├── HarmonyLab-Kickoff.md          (existing - project vision)
├── HarmonyLab-Schema-v1.0.sql     (existing - database schema)
└── harmony-lab-infra-setup.md     (existing - GCP instructions)
```

## Files Created

### Configuration Files
1. **`.env.example`** - Environment variables template
2. **`requirements.txt`** - Python dependencies
3. **`.gitignore`** - Git ignore patterns
4. **`README.md`** - Project documentation
5. **`config/settings.py`** - Settings management with pydantic-settings

### Application Files
6. **`main.py`** - FastAPI application with:
   - Health check endpoints (/, /health)
   - CORS middleware configured
   - Three routers registered (songs, sections, vocabulary)

### Database Layer
7. **`app/db/connection.py`** - Database connection manager with:
   - Connection pooling
   - Context manager for cursor operations
   - Helper methods (execute_query, execute_non_query, execute_scalar)
   - Test connection method

### Models
8. **`app/models/__init__.py`** - Complete Pydantic models matching schema:
   - Song, SongCreate, SongUpdate
   - Section, SectionCreate
   - Measure, MeasureCreate
   - Chord, ChordCreate
   - ChordVocabulary, RomanNumeralVocabulary
   - MelodyNote, UserSongProgress
   - Composite models (SongDetail with nested relationships)

### API Routes
9. **`app/api/routes/songs.py`** - Songs CRUD:
   - GET /api/v1/songs (list with filtering/pagination)
   - GET /api/v1/songs/{id}
   - POST /api/v1/songs
   - PUT /api/v1/songs/{id}
   - DELETE /api/v1/songs/{id}

10. **`app/api/routes/sections.py`** - Sections management:
    - GET /api/v1/sections/{song_id}/sections
    - POST /api/v1/sections/{song_id}/sections
    - DELETE /api/v1/sections/{section_id}

11. **`app/api/routes/vocabulary.py`** - Vocabulary lookups:
    - GET /api/v1/vocabulary/chord-symbols
    - GET /api/v1/vocabulary/roman-numerals

## Next Steps (For You to Complete)

### 1. Database Connection Setup
You need to provide database connection details in a `.env` file:

```powershell
# Copy the example file
Copy-Item .env.example .env

# Edit .env with your Cloud SQL instance details
# You'll need:
# - DB_SERVER (Cloud SQL instance IP or connection name)
# - DB_USER (typically 'sqlserver')
# - DB_PASSWORD (your SQL Server password)
```

### 2. Run Database Schema
Execute the schema file against your Cloud SQL instance:
```sql
-- Connect to your Cloud SQL instance
-- Run: HarmonyLab-Schema-v1.0.sql
```

### 3. Test the API
Once database is configured, start the development server:

```powershell
# Activate virtual environment
C:\venvs\Harmony-Lab\Scripts\Activate.ps1

# Run the API server
C:\venvs\Harmony-Lab\Scripts\python.exe -m uvicorn main:app --reload

# Or run directly
C:\venvs\Harmony-Lab\Scripts\python.exe main.py
```

Visit:
- API root: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 4. Remaining Development (Future Sprints)

**Routes to Create**:
- `app/api/routes/measures.py` - Measure CRUD
- `app/api/routes/chords.py` - Chord CRUD
- `app/api/routes/imports.py` - File upload and parsing
- `app/api/routes/quiz.py` - Quiz generation and tracking
- `app/api/routes/progress.py` - User progress tracking

**Services to Create**:
- `app/services/midi_parser.py` - Parse MIDI files using mido
- `app/services/musicxml_parser.py` - Parse MusicXML using music21
- `app/services/chord_detection.py` - Detect chords from MIDI notes
- `app/services/quiz_generator.py` - Generate quiz questions

**Frontend**:
- Vanilla JavaScript frontend (per kickoff doc)
- Tone.js integration for playback
- Quiz interface

## What I Need From You

1. **Database Connection Details**:
   - Cloud SQL instance IP/connection name
   - Database credentials
   - Confirm the database "HarmonyLab" has been created

2. **Schema Execution Confirmation**:
   - Have you run `HarmonyLab-Schema-v1.0.sql` on your Cloud SQL instance?
   - Any errors during schema creation?

3. **GCP Configuration** (if deploying):
   - Project ID
   - Bucket name for file uploads
   - Service account details

4. **Testing Preferences**:
   - Do you want to test locally first before GCP deployment?
   - Any specific songs from your 37-song repertoire to start with?

## Commands Quick Reference

```powershell
# Activate venv
C:\venvs\Harmony-Lab\Scripts\Activate.ps1

# Install additional packages (if needed)
C:\venvs\Harmony-Lab\Scripts\python.exe -m pip install <package>

# Run API server
C:\venvs\Harmony-Lab\Scripts\python.exe -m uvicorn main:app --reload

# Run tests (when created)
C:\venvs\Harmony-Lab\Scripts\python.exe -m pytest
```

## Architecture Notes

- **Database**: Using pyodbc for MS SQL Server (your 20 years of expertise)
- **Connection Pattern**: Context managers for automatic commit/rollback
- **Models**: Pydantic v2 with full type validation
- **API**: RESTful with OpenAPI documentation
- **CORS**: Configured for local development (localhost:3000)

## Project Status: Foundation Complete ✓

The project scaffolding is complete and ready for:
1. Database configuration
2. Local testing
3. Implementation of remaining routes (measures, chords, imports)
4. MIDI/MusicXML parsing services
5. Frontend development

---

**Ready for your input on database connection details!**
