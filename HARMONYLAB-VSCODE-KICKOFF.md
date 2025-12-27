# HarmonyLab - VS Code AI Kickoff Document

**Project**: HarmonyLab  
**Created**: 2025-12-26  
**Sprint**: 1 - Foundation & Infrastructure

---

## PROJECT IDENTITY

| Field | Value |
|-------|-------|
| **Project Name** | HarmonyLab |
| **Project Slug** | `harmony-lab` |
| **Description** | Harmonic progression training system for jazz standards |
| **Local Path** | `G:\My Drive\Code\Python\Harmony-Lab` |
| **GitHub Repo** | `https://github.com/coreyprator/harmony-lab` |
| **GCP Project** | `super-flashcards-475210` (shared instance) |

### Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| **Runtime** | Python 3.12.x | ⚠️ DO NOT UPGRADE - ODBC breaks on 3.13+ |
| **Backend** | FastAPI + uvicorn | |
| **Database** | MS SQL Server (Cloud SQL) | Shared instance: `flashcards-db` |
| **ORM/DB Access** | pyodbc | Requires ODBC Driver 17 |
| **Music Parsing** | mido, music21 | MIDI and MusicXML |
| **Audio Playback** | Tone.js (frontend) | Phase 2 |
| **Deployment** | Cloud Run | |
| **CI/CD** | GitHub Actions | |

---

## ENVIRONMENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HARMONYLAB ENVIRONMENT                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────┐         ┌────────────────────────────────┐    │
│  │  LOCAL MACHINE       │         │  GOOGLE CLOUD PLATFORM         │    │
│  │  (Windows Desktop)   │         │                                │    │
│  │                      │         │  Project: super-flashcards-... │    │
│  │  VS Code + Python    │  ────►  │                                │    │
│  │  FastAPI Server      │   TLS   │  Cloud SQL Instance:           │    │
│  │  localhost:8000      │         │  ├── flashcards-db             │    │
│  │                      │         │  │   IP: DB_HOST_REDACTED        │    │
│  │  Virtual Env:        │         │  │                             │    │
│  │  C:\venvs\Harmony-Lab│         │  │   Databases:                │    │
│  │                      │         │  │   ├── LanguageLearning      │    │
│  └──────────────────────┘         │  │   ├── Etymython             │    │
│                                   │  │   └── HarmonyLab ◄────      │    │
│                                   │  │                             │    │
│  ┌──────────────────────┐         │  Cloud Storage:                │    │
│  │  GitHub              │         │  └── gs://harmony-lab-uploads  │    │
│  │  coreyprator/        │         │                                │    │
│  │  harmony-lab         │  ────►  │  Cloud Run:                    │    │
│  │                      │         │  └── harmony-lab-xxxxxx-uc     │    │
│  │  Actions → Deploy    │         │                                │    │
│  └──────────────────────┘         └────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Environment Facts

| Fact | Details |
|------|---------|
| **Database Location** | Google Cloud SQL, NOT localhost |
| **Instance IP** | `DB_HOST_REDACTED` |
| **Database Name** | `HarmonyLab` |
| **DB User** | `harmonylab_user` |
| **Authentication** | Passkeys for GitHub, gcloud CLI for GCP |
| **Python Version** | 3.12.x ONLY (ODBC compatibility) |
| **Virtual Env** | `C:\venvs\Harmony-Lab` |

---

## ROLE DEFINITIONS

### 🏛️ Claude — Architect

- System architecture and database schema (already designed)
- API endpoint structure
- Complete file generation
- Sprint planning and documentation
- Root cause analysis

### 👔 Corey — Project Lead

- Feature prioritization
- Final decision authority
- Testing and validation
- Routes questions to appropriate AI

### 💻 VS Code AI — Coder & Debugger

**YOUR RESPONSIBILITIES:**
- Implement the files Claude has designed
- Fix syntax errors and import issues
- Debug runtime errors
- Add logging and error handling
- Fix file paths

**CONSTRAINTS — DO NOT:**
- ❌ Upgrade Python beyond 3.12
- ❌ Change database schema
- ❌ Make architecture decisions
- ❌ Assume local database
- ❌ Create new API endpoints without Claude's design

**DO:**
- ✅ Use Cloud SQL connection (IP: DB_HOST_REDACTED)
- ✅ Use virtual env at `C:\venvs\Harmony-Lab`
- ✅ Report design issues to escalate to Claude
- ✅ Follow the .env configuration

---

## SETUP CHECKLIST

### Phase 1: Verify Prerequisites ✓

```powershell
# Already completed by VS Code
python --version  # Should be 3.12.x
```

### Phase 2: Virtual Environment ✓

```powershell
# Already created at:
C:\venvs\Harmony-Lab
```

### Phase 3: Dependencies ✓

```powershell
# Already installed:
# fastapi, uvicorn, pyodbc, pydantic, python-dotenv, mido, music21
```

### Phase 4: GitHub Repository

```powershell
cd "G:\My Drive\Code\Python\Harmony-Lab"

# Ensure .gitignore exists and includes .env
git init
git add .
git commit -m "Initial project setup"
git branch -M main

# Browser opens for Passkey auth
git remote add origin https://github.com/coreyprator/harmony-lab.git
git push -u origin main
```

### Phase 5: Database Setup

```powershell
# Create database
gcloud sql databases create HarmonyLab --instance=flashcards-db --project=super-flashcards-475210

# Create user
gcloud sql users create harmonylab_user `
  --instance=flashcards-db `
  --password=HarmonyUser2025! `
  --project=super-flashcards-475210
```

**In Cloud SQL Studio** (https://console.cloud.google.com/sql/instances/flashcards-db/studio?project=super-flashcards-475210):

Login: `sqlserver` / `DB_PASSWORD_REDACTED`

```sql
USE HarmonyLab
CREATE USER [harmonylab_user] FOR LOGIN [harmonylab_user]
ALTER ROLE db_owner ADD MEMBER [harmonylab_user]
```

Then run the schema from `HarmonyLab-Schema-v1.0.sql` (remove GO statements).

### Phase 6: Create .env File

```powershell
@"
# HarmonyLab Environment Configuration
DB_SERVER=DB_HOST_REDACTED
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

### Phase 7: Verify Connection

```powershell
C:\venvs\Harmony-Lab\Scripts\Activate.ps1
cd "G:\My Drive\Code\Python\Harmony-Lab"
python main.py
```

Visit: http://localhost:8000/docs

---

## PROJECT STRUCTURE

```
Harmony-Lab/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── songs.py          # Song CRUD
│   │       ├── sections.py       # Section management
│   │       └── vocabulary.py     # Chord/Roman numeral lookups
│   ├── db/
│   │   ├── __init__.py
│   │   └── connection.py         # Cloud SQL connection
│   ├── models/
│   │   └── __init__.py           # Pydantic models
│   └── services/
│       └── __init__.py           # MIDI parser (Phase 2)
├── config/
│   ├── __init__.py
│   └── settings.py               # Environment settings
├── tests/
│   └── __init__.py
├── .env                          # ⚠️ Never commit
├── .env.example
├── .gitignore
├── main.py                       # FastAPI app entry
├── requirements.txt
├── README.md
├── HarmonyLab-Schema-v1.0.sql    # Database schema
└── HarmonyLab-Kickoff.md         # Requirements doc
```

---

## DATABASE SCHEMA SUMMARY

**Core Tables:**
- `Songs` - Title, composer, key, tempo, genre
- `Sections` - Intro, A, B, Bridge, Coda
- `Measures` - Container for chords
- `Chords` - chord_symbol, roman_numeral, key_center

**Vocabulary Tables:**
- `ChordVocabulary` - Standardized chord notation (CMaj7, Cm7, etc.)
- `RomanNumeralVocabulary` - Standardized Roman numerals (I, ii, V7, etc.)

**Progress Tables:**
- `UserSongProgress` - Learning progress per song
- `QuizAttempts` - Quiz history

**Helper View:**
- `vw_SongProgression` - Flattened chord progression view

---

## SPRINT 1 GOALS

- [x] GCP project decisions (using shared instance)
- [ ] Database schema creation (run HarmonyLab-Schema-v1.0.sql)
- [ ] GitHub repository setup
- [ ] Verify API starts and connects to database
- [ ] Basic song CRUD endpoints working
- [ ] Vocabulary endpoints returning seed data

---

## COMMANDS CHEAT SHEET

```powershell
# Activate environment
C:\venvs\Harmony-Lab\Scripts\Activate.ps1

# Run API
python main.py

# Test connection
python -c "from app.db.connection import get_db_connection; print('OK' if get_db_connection() else 'FAIL')"

# Git push (Passkey auth via browser)
git add . && git commit -m "message" && git push

# Cloud SQL Studio
# https://console.cloud.google.com/sql/instances/flashcards-db/studio?project=super-flashcards-475210
```

---

## CREDENTIALS (Use 1Password)

| Service | User | Password |
|---------|------|----------|
| Cloud SQL Root | sqlserver | DB_PASSWORD_REDACTED |
| HarmonyLab DB | harmonylab_user | HarmonyUser2025! |

---

## ESCALATION TO CLAUDE

**Escalate when:**
- Architecture questions arise
- Database schema changes needed
- New API endpoints require design
- Performance or security concerns
- Design-level bugs found

**Tell the user:**
> "This appears to be an architecture-level decision. I recommend discussing with Claude before proceeding."

---

## NEXT STEPS FOR VS CODE AI

1. **Verify prerequisites** — Python 3.12.x, gcloud auth, ODBC driver
2. **Run database setup commands** — Create database and user
3. **Grant user permissions** — Via Cloud SQL Studio
4. **Run schema** — From HarmonyLab-Schema-v1.0.sql
5. **Create .env file** — With Cloud SQL credentials
6. **Test API** — `python main.py` → http://localhost:8000/docs
7. **Setup GitHub** — Initialize repo, push initial commit

**Start with Step 1 and proceed in order.**
