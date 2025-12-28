# HarmonyLab Cloud Migration - Corrective Action Guide

**Date**: 2025-12-28  
**Status**: CORRECTIVE ACTION REQUIRED  
**Reference**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.5  
**Target**: Align HarmonyLab with cloud-first deployment methodology

---

## Executive Summary

HarmonyLab was built with a localhost development pattern. Per methodology v3.5, we must migrate to:

| Current State ❌ | Required State ✅ |
|------------------|-------------------|
| `.env` files for credentials | Google Secret Manager |
| `localhost:8000` development | Cloud Run deployment |
| No CI/CD pipeline | GitHub Actions auto-deploy |
| No Dockerfile | Container-based deployment |
| Manual testing | Cloud Run URL testing |

---

## PART 1: Files to Create

### 1.1 Dockerfile

Create `Dockerfile` in project root:

```dockerfile
# HarmonyLab Dockerfile
# Python 3.12 with MS SQL ODBC driver for Cloud Run

FROM python:3.12-slim

# Install system dependencies and ODBC driver
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    apt-transport-https \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run uses PORT environment variable
ENV PORT=8080
EXPOSE 8080

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

### 1.2 GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

env:
  PROJECT_ID: super-flashcards-475210
  SERVICE_NAME: harmonylab
  REGION: us-central1
  REPOSITORY: harmonylab

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      id-token: write
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Google Auth
        id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
      
      - name: Configure Docker
        run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev
      
      - name: Build Container
        run: |
          docker build -t ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }} .
      
      - name: Push Container
        run: |
          docker push ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }}
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.SERVICE_NAME }} \
            --image ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/${{ env.REPOSITORY }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
            --platform managed \
            --region ${{ env.REGION }} \
            --allow-unauthenticated \
            --set-secrets=DB_SERVER=harmonylab-db-server:latest,DB_NAME=harmonylab-db-name:latest,DB_USER=harmonylab-db-user:latest,DB_PASSWORD=harmonylab-db-password:latest
      
      - name: Show URL
        run: |
          gcloud run services describe ${{ env.SERVICE_NAME }} \
            --region ${{ env.REGION }} \
            --format="value(status.url)"
```

---

### 1.3 Updated config/settings.py

Replace current `.env`-based settings with Secret Manager:

```python
"""
HarmonyLab Settings - Cloud-First Configuration
Loads secrets from Google Secret Manager (production)
Falls back to environment variables (CI/CD)
"""
import os
from functools import lru_cache
from typing import Optional

# Only import secretmanager if available (not required in CI/CD)
try:
    from google.cloud import secretmanager
    HAS_SECRET_MANAGER = True
except ImportError:
    HAS_SECRET_MANAGER = False


def get_secret(secret_id: str, project_id: str = "super-flashcards-475210") -> str:
    """
    Fetch secret from Google Secret Manager.
    Falls back to environment variable if Secret Manager unavailable.
    """
    # Environment variable takes precedence (for Cloud Run injection)
    env_key = secret_id.upper().replace("-", "_")
    env_value = os.getenv(env_key)
    if env_value:
        return env_value
    
    # Try Secret Manager
    if HAS_SECRET_MANAGER:
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"Warning: Could not fetch secret {secret_id}: {e}")
    
    # Final fallback for local development
    raise ValueError(f"Secret {secret_id} not found in environment or Secret Manager")


class Settings:
    """Application settings loaded from Secret Manager."""
    
    def __init__(self):
        self._project_id = "super-flashcards-475210"
        self._prefix = "harmonylab"
    
    @property
    def db_server(self) -> str:
        return get_secret(f"{self._prefix}-db-server", self._project_id)
    
    @property
    def db_name(self) -> str:
        return get_secret(f"{self._prefix}-db-name", self._project_id)
    
    @property
    def db_user(self) -> str:
        return get_secret(f"{self._prefix}-db-user", self._project_id)
    
    @property
    def db_password(self) -> str:
        return get_secret(f"{self._prefix}-db-password", self._project_id)
    
    @property
    def db_driver(self) -> str:
        # Cloud Run uses Linux driver name
        if os.getenv("K_SERVICE"):  # Cloud Run sets this
            return "ODBC Driver 17 for SQL Server"
        # Local Windows development
        return os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    
    @property
    def debug(self) -> bool:
        return os.getenv("DEBUG", "false").lower() == "true"
    
    @property
    def host(self) -> str:
        return os.getenv("HOST", "0.0.0.0")
    
    @property
    def port(self) -> int:
        return int(os.getenv("PORT", "8080"))


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Convenience export
settings = get_settings()
```

---

### 1.4 Updated app/db/connection.py

```python
"""
Database connection for Cloud SQL.
Uses Secret Manager credentials.
"""
import pyodbc
from config.settings import settings


class Database:
    """Database connection manager for Cloud SQL."""
    
    def __init__(self):
        self._connection = None
    
    @property
    def connection_string(self) -> str:
        """Build pyodbc connection string for Cloud SQL."""
        return (
            f"DRIVER={{{settings.db_driver}}};"
            f"SERVER={settings.db_server};"
            f"DATABASE={settings.db_name};"
            f"UID={settings.db_user};"
            f"PWD={settings.db_password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
        )
    
    def get_connection(self):
        """Get a new database connection."""
        try:
            return pyodbc.connect(self.connection_string)
        except pyodbc.Error as e:
            print(f"Database connection failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


# Singleton instance
db = Database()


def get_db_connection():
    """Convenience function for getting a connection."""
    return db.get_connection()
```

---

### 1.5 Health Check Endpoint

Add to `main.py`:

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    from app.db.connection import db
    
    try:
        db_ok = db.test_connection()
    except Exception:
        db_ok = False
    
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "service": "harmonylab",
        "version": "1.0.0"
    }
```

---

## PART 2: Secret Manager Setup

### 2.1 Create Secrets

```powershell
# Create HarmonyLab secrets in Secret Manager
echo -n "35.224.242.223" | gcloud secrets create harmonylab-db-server `
  --data-file=- --project=super-flashcards-475210

echo -n "HarmonyLab" | gcloud secrets create harmonylab-db-name `
  --data-file=- --project=super-flashcards-475210

echo -n "harmonylab_user" | gcloud secrets create harmonylab-db-user `
  --data-file=- --project=super-flashcards-475210

echo -n "HarmonyUser2025!" | gcloud secrets create harmonylab-db-password `
  --data-file=- --project=super-flashcards-475210

# Verify
gcloud secrets list --project=super-flashcards-475210 --filter="name:harmonylab"
```

### 2.2 Grant Cloud Run Access

```powershell
# Get the Cloud Run service account
$SA = "super-flashcards-475210@appspot.gserviceaccount.com"

# Grant access to each secret
foreach ($secret in @("harmonylab-db-server", "harmonylab-db-name", "harmonylab-db-user", "harmonylab-db-password")) {
    gcloud secrets add-iam-policy-binding $secret `
        --member="serviceAccount:$SA" `
        --role="roles/secretmanager.secretAccessor" `
        --project=super-flashcards-475210
}
```

---

## PART 3: GitHub Actions Setup

### 3.1 Create Artifact Registry Repository

```powershell
# Create repository for container images
gcloud artifacts repositories create harmonylab `
    --repository-format=docker `
    --location=us-central1 `
    --project=super-flashcards-475210
```

### 3.2 Set Up Workload Identity Federation

```powershell
# Create workload identity pool (if not exists)
gcloud iam workload-identity-pools create "github-actions" `
    --location="global" `
    --project=super-flashcards-475210

# Create provider
gcloud iam workload-identity-pools providers create-oidc "github" `
    --location="global" `
    --workload-identity-pool="github-actions" `
    --issuer-uri="https://token.actions.githubusercontent.com" `
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" `
    --project=super-flashcards-475210

# Create service account for GitHub Actions
gcloud iam service-accounts create github-actions-harmonylab `
    --display-name="GitHub Actions for HarmonyLab" `
    --project=super-flashcards-475210

# Grant necessary roles
$SA = "github-actions-harmonylab@super-flashcards-475210.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding super-flashcards-475210 `
    --member="serviceAccount:$SA" `
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding super-flashcards-475210 `
    --member="serviceAccount:$SA" `
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding super-flashcards-475210 `
    --member="serviceAccount:$SA" `
    --role="roles/iam.serviceAccountUser"

# Allow GitHub to impersonate service account
gcloud iam service-accounts add-iam-policy-binding $SA `
    --role="roles/iam.workloadIdentityUser" `
    --member="principalSet://iam.googleapis.com/projects/YOUR_PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/attribute.repository/coreyprator/HarmonyLab" `
    --project=super-flashcards-475210
```

### 3.3 Add GitHub Secrets

In GitHub repo settings → Secrets and variables → Actions:

| Secret Name | Value |
|-------------|-------|
| `WIF_PROVIDER` | `projects/YOUR_PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions/providers/github` |
| `WIF_SERVICE_ACCOUNT` | `github-actions-harmonylab@super-flashcards-475210.iam.gserviceaccount.com` |

---

## PART 4: Files to Update

### 4.1 requirements.txt

Add Secret Manager dependency:

```
fastapi>=0.104.0
uvicorn>=0.24.0
pyodbc>=5.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
google-cloud-secret-manager>=2.16.0
mido>=1.3.0
music21>=9.1.0
python-multipart>=0.0.6
```

### 4.2 README.md

Replace localhost references:

```markdown
# HarmonyLab

Harmonic progression training system for jazz standards.

## Development Methodology

This project follows [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.5

## Architecture

- **Backend**: FastAPI on Cloud Run
- **Database**: MS SQL Server on Cloud SQL
- **Credentials**: Google Secret Manager
- **CI/CD**: GitHub Actions

## Development Workflow

```
Write Code → Push to GitHub → GitHub Actions → Cloud Run → Test
```

**NO LOCALHOST DEVELOPMENT** - All testing happens on Cloud Run URL.

## Deployment

Automatic on push to `main` branch.

### Get Cloud Run URL

```bash
gcloud run services describe harmonylab --region=us-central1 --format="value(status.url)"
```

### Manual Deploy (if needed)

```bash
gcloud run deploy harmonylab \
  --source . \
  --region us-central1 \
  --project super-flashcards-475210
```

## API Documentation

Production: `https://[CLOUD_RUN_URL]/docs`

## Health Check

```bash
curl https://[CLOUD_RUN_URL]/health
```

## GCP Resources

| Resource | Value |
|----------|-------|
| Project | `super-flashcards-475210` |
| Cloud SQL Instance | `flashcards-db` |
| Database | `HarmonyLab` |
| Secret Prefix | `harmonylab-*` |
| Region | `us-central1` |
```

### 4.3 Delete These Files

- `.env` (if exists)
- `.env.example` (replace with Secret Manager docs)
- `QUICKSTART.md` (replace with cloud workflow)
- Any localhost references in documentation

---

## PART 5: Ableton-midi-bench Review

### Assessment

| Feature | Ableton-midi-bench | HarmonyLab Need | Verdict |
|---------|-------------------|-----------------|---------|
| MIDI File Loading | ✅ Uses `mido` | ✅ Same library | **Reusable pattern** |
| Note Extraction | ✅ Extracts timing, pitch, velocity | ✅ Need same | **Reusable** |
| Chord Detection | ❌ Not implemented | ✅ Required | **Must build** |
| Timing Analysis | ✅ Detailed metrics | ⚪ Nice to have | **Future feature** |
| SQL Integration | ✅ MS SQL patterns | ✅ Same stack | **Reusable patterns** |

### Recommendation: Partial Integration

**USE from Ableton-midi-bench:**

1. **MIDI loading pattern** — The `mido` usage patterns are solid:
   ```python
   from mido import MidiFile
   mid = MidiFile('song.mid')
   for track in mid.tracks:
       for msg in track:
           if msg.type == 'note_on':
               # Extract note data
   ```

2. **Environment variable pattern** — Their config approach is cleaner than `.env`:
   ```python
   $env:MIDI_BENCH_SQL_SERVER = '.\SQLEXPRESS01'
   ```

3. **Test structure** — Their `tests/` organization is good

**DO NOT USE:**

1. **GUI code** — HarmonyLab is web-based, not desktop
2. **Timing analysis** — Different focus (chord detection vs performance benchmarking)
3. **Local SQL patterns** — We use Cloud SQL

### Integration Path

Create `app/services/midi_parser.py` borrowing patterns:

```python
"""
MIDI Parser for HarmonyLab
Borrows patterns from Ableton-midi-bench for file loading
Adds chord detection specific to harmonic analysis
"""
from mido import MidiFile, MidiTrack
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ExtractedNote:
    """A note extracted from MIDI."""
    pitch: int
    start_tick: int
    duration_ticks: int
    velocity: int
    channel: int


@dataclass
class DetectedChord:
    """A chord detected from simultaneous notes."""
    measure: int
    beat: float
    symbol: str
    notes: List[int]
    confidence: float


# Chord detection templates (intervals from root)
CHORD_TEMPLATES = {
    'Maj7': {0, 4, 7, 11},
    'm7': {0, 3, 7, 10},
    '7': {0, 4, 7, 10},
    'ø7': {0, 3, 6, 10},
    'dim7': {0, 3, 6, 9},
    'Maj': {0, 4, 7},
    'm': {0, 3, 7},
    'dim': {0, 3, 6},
    'aug': {0, 4, 8},
}

NOTE_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


def load_midi(filepath: str) -> MidiFile:
    """Load MIDI file using mido."""
    return MidiFile(filepath)


def extract_notes(mid: MidiFile) -> List[ExtractedNote]:
    """Extract all notes from MIDI file."""
    notes = []
    for track in mid.tracks:
        current_time = 0
        pending_notes: Dict[Tuple[int, int], int] = {}  # (pitch, channel) -> start_tick
        
        for msg in track:
            current_time += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                pending_notes[(msg.note, msg.channel)] = current_time
            
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                key = (msg.note, msg.channel)
                if key in pending_notes:
                    start = pending_notes.pop(key)
                    notes.append(ExtractedNote(
                        pitch=msg.note,
                        start_tick=start,
                        duration_ticks=current_time - start,
                        velocity=msg.velocity,
                        channel=msg.channel
                    ))
    
    return sorted(notes, key=lambda n: n.start_tick)


def detect_chord(pitches: List[int]) -> Tuple[str, float]:
    """
    Detect chord from list of MIDI pitches.
    Returns (chord_symbol, confidence).
    """
    if not pitches:
        return ("N.C.", 0.0)
    
    # Normalize to pitch classes
    pitch_classes = set(p % 12 for p in pitches)
    
    best_match = ("?", 0.0)
    
    for root in range(12):
        for chord_type, intervals in CHORD_TEMPLATES.items():
            # Rotate template to this root
            template = {(root + i) % 12 for i in intervals}
            
            # Calculate match score
            matches = len(pitch_classes & template)
            total = len(template)
            
            if matches == total and len(pitch_classes) == total:
                # Perfect match
                return (NOTE_NAMES[root] + chord_type, 1.0)
            
            score = matches / max(len(pitch_classes), total)
            if score > best_match[1]:
                best_match = (NOTE_NAMES[root] + chord_type, score)
    
    return best_match


def parse_midi_for_chords(filepath: str, ticks_per_beat: int = 480) -> List[DetectedChord]:
    """
    Parse MIDI file and detect chords.
    Groups simultaneous notes and identifies chord symbols.
    """
    mid = load_midi(filepath)
    notes = extract_notes(mid)
    
    # Group notes by time window (within 1/16 note = ticks_per_beat/4)
    window = ticks_per_beat // 4
    chords = []
    
    i = 0
    while i < len(notes):
        # Collect all notes within window
        group_start = notes[i].start_tick
        group_notes = []
        
        while i < len(notes) and notes[i].start_tick - group_start < window:
            group_notes.append(notes[i].pitch)
            i += 1
        
        if len(group_notes) >= 3:  # Need at least 3 notes for a chord
            symbol, confidence = detect_chord(group_notes)
            
            measure = group_start // (ticks_per_beat * 4) + 1
            beat = (group_start % (ticks_per_beat * 4)) / ticks_per_beat + 1
            
            chords.append(DetectedChord(
                measure=measure,
                beat=round(beat, 2),
                symbol=symbol,
                notes=group_notes,
                confidence=confidence
            ))
    
    return chords
```

---

## PART 6: Definition of Done Checklist

| Requirement | Status | Verification |
|-------------|--------|--------------|
| Dockerfile created | ⬜ | `docker build -t harmonylab .` succeeds |
| GitHub Actions workflow | ⬜ | Push triggers deployment |
| Secrets in Secret Manager | ⬜ | `gcloud secrets list \| grep harmonylab` |
| No .env in production | ⬜ | `.env` not in repo, not on Cloud Run |
| Cloud Run URL accessible | ⬜ | `curl https://[URL]/health` returns 200 |
| Health endpoint responds | ⬜ | Returns `{"status": "healthy"}` |
| Database connected | ⬜ | Health shows `"database": "connected"` |
| README updated | ⬜ | No localhost references |
| Ableton-midi-bench reviewed | ⬜ | Decision documented above |

---

## PART 7: VS Code AI Instructions

Copy this to VS Code AI:

```
CORRECTIVE ACTION: HarmonyLab Cloud Migration

This project must be migrated from localhost to cloud-first per methodology v3.5.

TASKS (in order):
1. Create Dockerfile (see PART 1.1)
2. Create .github/workflows/deploy.yml (see PART 1.2)
3. Replace config/settings.py with Secret Manager version (see PART 1.3)
4. Update app/db/connection.py (see PART 1.4)
5. Add /health endpoint to main.py (see PART 1.5)
6. Update requirements.txt with google-cloud-secret-manager
7. Update README.md - remove ALL localhost references
8. Delete .env and .env.example if they exist

CONSTRAINTS:
- Python 3.12.x ONLY
- NO .env files - use Secret Manager
- NO localhost testing - deploy to Cloud Run
- All secrets via: gcloud secrets create harmonylab-*

GCP RESOURCES:
- Project: super-flashcards-475210
- Instance: flashcards-db
- Database: HarmonyLab
- Region: us-central1

After changes, push to main and verify GitHub Actions deploys successfully.
```

---

**Document Version**: 1.0  
**Created**: 2025-12-28  
**Reference**: project-methodology v3.5
