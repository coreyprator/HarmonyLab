# Harmony Lab

A harmonic progression training system for musicians to internalize chord progressions of jazz standards and popular songs.

## Project Structure

```
Harmony-Lab/
├── app/
│   ├── api/
│   │   └── routes/         # API endpoint definitions
│   ├── db/                 # Database connection and queries
│   ├── models/             # Pydantic models
│   └── services/           # Business logic (MIDI parsing, etc.)
├── config/                 # Configuration files
├── tests/                  # Test files
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (not in git)
```

## Setup

### 1. Virtual Environment

Virtual environment is on local hard drive at: `C:\venvs\Harmony-Lab`

```powershell
# Activate virtual environment
C:\venvs\Harmony-Lab\Scripts\Activate.ps1
```

### 2. Environment Variables

Copy `.env.example` to `.env` and update with your configuration:

```powershell
cp .env.example .env
```

Update the database connection details for your Cloud SQL instance.

### 3. Run the API

```powershell
C:\venvs\Harmony-Lab\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: http://localhost:8000
API documentation: http://localhost:8000/docs

## Database

Using MS SQL Server on Google Cloud SQL. Schema is defined in `HarmonyLab-Schema-v1.0.sql`.

## Documentation

- [Kickoff Document](HarmonyLab-Kickoff.md) - Full project vision and requirements
- [Infrastructure Setup](harmony-lab-infra-setup.md) - GCP setup instructions
- [Schema](HarmonyLab-Schema-v1.0.sql) - Database schema

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: MS SQL Server (Cloud SQL)
- **MIDI Parser**: mido
- **MusicXML Parser**: music21
- **Hosting**: Google Cloud Run (planned)
- **Frontend**: Vanilla JavaScript (planned)
