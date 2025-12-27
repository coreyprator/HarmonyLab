# HarmonyLab - Sprint 2 Handoff

**Date**: 2025-12-27  
**From**: Claude (Architect)  
**To**: VS Code AI (Coder)  
**Status**: Sprint 1 Complete ✓

---

## Sprint 1 Accomplishments ✓

| Task | Status |
|------|--------|
| GCP infrastructure (shared Cloud SQL) | ✓ Complete |
| Database schema deployed (9 tables) | ✓ Complete |
| Seed data loaded (30 chords, 52 roman numerals) | ✓ Complete |
| Secret Manager integration | ✓ Complete |
| GitHub repository | ✓ Complete |
| FastAPI server running | ✓ Complete |
| Songs, Sections, Vocabulary routes | ✓ Complete |

---

## Sprint 2 Goals

### Priority 1: Complete CRUD Routes

Implement the remaining API routes following the existing patterns in `app/api/routes/`.

#### 1. Measures Route (`app/api/routes/measures.py`)

```python
# Endpoints needed:
POST   /api/measures/              # Create measure in a section
GET    /api/measures/{id}          # Get single measure with chords
GET    /api/sections/{id}/measures # List measures in section
PUT    /api/measures/{id}          # Update measure
DELETE /api/measures/{id}          # Delete measure (cascades to chords)
```

**Database table**: `Measures`
```sql
-- Schema reference
CREATE TABLE Measures (
    id INT IDENTITY PRIMARY KEY,
    section_id INT NOT NULL FOREIGN KEY REFERENCES Sections(id),
    measure_number INT NOT NULL,
    created_at DATETIME2 DEFAULT GETDATE()
);
```

#### 2. Chords Route (`app/api/routes/chords.py`)

```python
# Endpoints needed:
POST   /api/chords/                # Create chord in a measure
GET    /api/chords/{id}            # Get single chord
GET    /api/measures/{id}/chords   # List chords in measure
PUT    /api/chords/{id}            # Update chord
DELETE /api/chords/{id}            # Delete chord

# Bulk operations (important for imports):
POST   /api/measures/{id}/chords/bulk  # Create multiple chords at once
```

**Database table**: `Chords`
```sql
CREATE TABLE Chords (
    id INT IDENTITY PRIMARY KEY,
    measure_id INT NOT NULL FOREIGN KEY REFERENCES Measures(id),
    beat_position DECIMAL(3,2) DEFAULT 1.0,
    chord_symbol VARCHAR(20) NOT NULL,
    roman_numeral VARCHAR(20),
    key_center VARCHAR(20),
    function_label VARCHAR(50),
    comments NVARCHAR(500),
    chord_order INT NOT NULL
);
```

#### 3. Progress Route (`app/api/routes/progress.py`)

```python
# Endpoints needed:
GET    /api/progress/                    # List all user progress
GET    /api/progress/song/{song_id}      # Get progress for specific song
POST   /api/progress/song/{song_id}      # Create/update progress
GET    /api/progress/stats               # Aggregate stats (songs practiced, accuracy)
```

**Database table**: `UserSongProgress`

#### 4. Quiz Route (`app/api/routes/quiz.py`)

```python
# Endpoints needed:
POST   /api/quiz/generate/{song_id}      # Generate quiz for a song
POST   /api/quiz/submit                  # Submit quiz answers
GET    /api/quiz/attempts                # List past quiz attempts
GET    /api/quiz/attempts/{id}           # Get specific attempt details
```

**Database table**: `QuizAttempts`

---

### Priority 2: Import Service

Create the MIDI parser service. This is the first import format to support.

#### File: `app/services/midi_parser.py`

```python
"""
MIDI Parser Service

Uses the `mido` library to:
1. Parse MIDI files
2. Extract chord data from chord tracks
3. Detect time signature and tempo
4. Map MIDI notes to chord symbols

Key functions needed:
- parse_midi_file(file_path: str) -> ParsedSong
- extract_chords(midi_data) -> List[ChordData]
- midi_notes_to_chord(notes: List[int]) -> str
"""

from mido import MidiFile
from typing import List, Optional
from pydantic import BaseModel

class ChordData(BaseModel):
    measure_number: int
    beat_position: float
    chord_symbol: str
    midi_notes: List[int]  # Original notes for verification

class ParsedSong(BaseModel):
    title: Optional[str]
    tempo: Optional[int]
    time_signature: str
    sections: List[SectionData]

# Implementation approach:
# 1. Load MIDI with mido.MidiFile()
# 2. Find chord track (usually track with simultaneous notes)
# 3. Group notes by time position
# 4. For each group, identify chord using interval matching
# 5. Return structured data for review before saving
```

**Chord Detection Algorithm**:
```python
# Standard chord templates (intervals from root)
CHORD_TEMPLATES = {
    'Maj7': [0, 4, 7, 11],      # 1 3 5 7
    'm7': [0, 3, 7, 10],        # 1 b3 5 b7
    '7': [0, 4, 7, 10],         # 1 3 5 b7
    'ø7': [0, 3, 6, 10],        # 1 b3 b5 b7
    'dim7': [0, 3, 6, 9],       # 1 b3 b5 bb7
    'm9': [0, 3, 7, 10, 14],    # 1 b3 5 b7 9
    'Maj9': [0, 4, 7, 11, 14],  # 1 3 5 7 9
    # ... etc
}

NOTE_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 
              'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
```

#### File: `app/api/routes/imports.py`

```python
# Endpoints needed:
POST   /api/imports/midi          # Upload and parse MIDI file
POST   /api/imports/preview       # Preview parsed data before saving
POST   /api/imports/confirm       # Confirm and save to database
GET    /api/imports/status/{id}   # Check import job status
```

---

### Priority 3: MusicXML Parser (Stretch Goal)

If MIDI parser is complete, start on MusicXML:

#### File: `app/services/musicxml_parser.py`

```python
"""
MusicXML Parser Service

Uses `music21` library to:
1. Parse MusicXML (.mxl, .xml) files
2. Extract chord symbols directly (MusicXML often has them!)
3. Extract key signatures, time signatures
4. Handle section markers if present
"""

from music21 import converter, chord, harmony
```

MusicXML is often easier than MIDI because chord symbols may already be encoded.

---

## Pydantic Models Needed

Add to `app/models/__init__.py`:

```python
# Measure models
class MeasureCreate(BaseModel):
    section_id: int
    measure_number: int

class MeasureResponse(BaseModel):
    id: int
    section_id: int
    measure_number: int
    chords: List[ChordResponse] = []

# Chord models
class ChordCreate(BaseModel):
    measure_id: int
    beat_position: float = 1.0
    chord_symbol: str
    roman_numeral: Optional[str] = None
    key_center: Optional[str] = None
    function_label: Optional[str] = None
    comments: Optional[str] = None
    chord_order: int

class ChordResponse(BaseModel):
    id: int
    measure_id: int
    beat_position: float
    chord_symbol: str
    roman_numeral: Optional[str]
    key_center: Optional[str]
    function_label: Optional[str]
    comments: Optional[str]
    chord_order: int

# Progress models
class ProgressResponse(BaseModel):
    song_id: int
    song_title: str
    last_practiced: Optional[datetime]
    times_practiced: int
    accuracy_rate: Optional[float]
    mastery_level: int

# Quiz models
class QuizQuestion(BaseModel):
    measure_number: int
    beat_position: float
    is_blank: bool
    displayed_chord: Optional[str]  # None if blank
    
class QuizSubmission(BaseModel):
    quiz_id: int
    answers: List[str]  # User's answers for blank positions

class QuizResult(BaseModel):
    total_questions: int
    correct_answers: int
    accuracy: float
    details: List[dict]  # Per-question results
```

---

## File Structure After Sprint 2

```
Harmony-Lab/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── songs.py        ✓ Exists
│   │       ├── sections.py     ✓ Exists
│   │       ├── vocabulary.py   ✓ Exists
│   │       ├── measures.py     ← NEW
│   │       ├── chords.py       ← NEW
│   │       ├── progress.py     ← NEW
│   │       ├── quiz.py         ← NEW
│   │       └── imports.py      ← NEW
│   ├── services/
│   │   ├── midi_parser.py      ← NEW
│   │   └── musicxml_parser.py  ← NEW (stretch)
│   └── models/
│       └── __init__.py         ← UPDATE with new models
└── ...
```

---

## Database Reference

### View for Easy Queries

Use the existing view for reading progressions:

```sql
SELECT * FROM vw_SongProgression WHERE song_id = 1
ORDER BY section_order, measure_number, chord_order;
```

### Stored Procedure

```sql
EXEC sp_GetSongProgression @SongId = 1;
```

---

## Testing Checklist

After implementing each route:

- [ ] Measures: Create, Read, Update, Delete
- [ ] Chords: Create, Read, Update, Delete, Bulk Create
- [ ] Progress: Create/Update progress, Get stats
- [ ] Quiz: Generate quiz, Submit answers, View history
- [ ] Imports: Upload MIDI, Preview, Confirm save

**Test with real data**:
1. Import a simple MIDI file (Blue Bossa has a clear ii-V-I pattern)
2. Verify chords are detected correctly
3. Create a quiz from the imported song
4. Submit answers and verify scoring

---

## Environment Reminders

| Setting | Value |
|---------|-------|
| Python | 3.12.x (DO NOT UPGRADE) |
| Virtual Env | `C:\venvs\Harmony-Lab` |
| Database | `HarmonyLab` on Cloud SQL |
| Credentials | Google Secret Manager |
| Run Server | `python main.py` → http://localhost:8000/docs |

---

## Escalate to Claude If:

- MIDI parsing algorithm needs design changes
- Quiz generation logic needs rework
- New database tables/columns needed
- Performance issues with bulk operations
- Authentication/authorization design needed

---

## Success Criteria for Sprint 2

1. ✓ All 5 new route files created and working
2. ✓ MIDI parser can extract chords from test files
3. ✓ Can import a song and generate a quiz from it
4. ✓ Quiz scoring works correctly
5. ✓ Progress tracking updates after quiz completion

---

**Next Sprint Preview (Sprint 3)**:
- Tone.js integration for audio playback
- Frontend song list and detail views
- Visual chord grid display
- Play button to hear progressions
