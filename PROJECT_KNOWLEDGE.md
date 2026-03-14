# PROJECT_KNOWLEDGE.md -- HarmonyLab
<!-- CHECKPOINT: HL-PK-9F3A -->

**Generated**: 2026-02-15
**Updated**: 2026-03-14T20:20:00Z — Sprint HL-MEGA-003: v2.14.0 (note count enrichment for MuseScore imports, header stats display, Darren review doc)
**Method**: Full project read-through of every source file, config, schema, workflow, and documentation file.
**Purpose**: Single-file knowledge recovery for any AI agent resuming work on this project.

---

## 1. Project Identity

| Field | Value | Source |
|-------|-------|--------|
| Project Name | HarmonyLab | `CLAUDE.md` line 63 |
| Description | Jazz chord progression training app | `CLAUDE.md` line 64 |
| Repository | https://github.com/coreyprator/harmonylab | `CLAUDE.md` line 65 |
| Local Path | `G:\My Drive\Code\Python\harmonylab` | `CLAUDE.md` line 66 |
| Methodology | [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology) v3.14 | `CLAUDE.md` line 67 |
| Current Version | v2.14.0 | `main.py` VERSION (updated 2026-03-14) |
| Latest Revision | harmonylab-00165+ (backend), harmonylab-frontend-00081-j96 (frontend) | HL-MEGA-003 2026-03-14 |
| Production URL | https://harmonylab.rentyourcio.com | `PROJECT_STATUS.md` line 5 |
| API Docs | https://harmonylab.rentyourcio.com/docs | `PROJECT_STATUS.md` line 189 |
| CLAUDE.md Last Updated | 2026-02-07 | `CLAUDE.md` line 269 |

---

## 2. GCP Infrastructure (Exact Values)

All values sourced from `CLAUDE.md` lines 71-83 unless otherwise noted.

| Resource | Value |
|----------|-------|
| GCP Project ID | `super-flashcards-475210` |
| Region | `us-central1` |
| Cloud Run Service (Backend) | `harmonylab` |
| Cloud Run Service (Frontend) | `harmonylab-frontend` |
| Cloud Run URL (Backend) | `https://harmonylab-wmrla7fhwa-uc.a.run.app` |
| Cloud Run URL (Frontend) | `https://harmonylab-frontend-wmrla7fhwa-uc.a.run.app` |
| Cloud SQL Instance | `flashcards-db` (shared with Super-Flashcards) |
| Cloud SQL IP | `35.224.242.223` |
| Database Name | `HarmonyLab` |
| Custom Domain | `harmonylab.rentyourcio.com` |
| Artifact Registry | `us-central1-docker.pkg.dev/super-flashcards-475210/harmonylab/harmonylab` |

> **Note:** The `harmonylab-frontend` Cloud Run service serves the vanilla HTML/CSS/JS frontend.
> Pages: index.html (song list), song.html (song detail + analysis + MIDI), quiz.html, progress.html, login.html.
> Deployed via `gcloud run deploy harmonylab-frontend --source frontend/ --region us-central1`.

Source for Artifact Registry path: `.github/workflows/deploy.yml` line 40.

---

## 3. Secret Manager

All values sourced from `CLAUDE.md` lines 119-126 and `config/settings.py`.

| Secret Name | Purpose | Referenced In |
|-------------|---------|---------------|
| `harmonylab-db-password` | Database password | `CLAUDE.md` line 121, `config/settings.py` line 69, `deploy.yml` line 53 |
| `harmonylab-db-user` | Database user (harmonylab_user) | `CLAUDE.md` line 122, `config/settings.py` line 65 |
| `harmonylab-db-server` | Database server IP | `CLAUDE.md` line 123, `config/settings.py` line 58 |
| `harmonylab-db-name` | Database name | `CLAUDE.md` line 124, `config/settings.py` line 61 |
| `harmonylab-jwt-secret` | JWT token signing key | `config/settings.py` line 110 |
| `harmonylab-google-client-id` | Google OAuth Client ID | `config/settings.py` line 120 |
| `harmonylab-google-client-secret` | Google OAuth Client Secret | `config/settings.py` line 128 |

The `config/settings.py` `get_secret()` function (lines 18-46) first checks environment variables (full name like `HARMONYLAB_DB_SERVER`, then short name like `DB_SERVER`), then falls back to Google Secret Manager using project ID `super-flashcards-475210`.

Cloud Run environment detection: `os.getenv("K_SERVICE")` returns truthy on Cloud Run (`config/settings.py` lines 75, 86, 135).

Secrets are injected at deploy time via the GitHub Actions workflow (`deploy.yml` line 53):
```
--set-secrets=DB_SERVER=harmonylab-db-server:latest,DB_NAME=harmonylab-db-name:latest,DB_USER=harmonylab-db-user:latest,DB_PASSWORD=harmonylab-db-password:latest
```

---

## 4. Tech Stack

### Backend
| Component | Technology | Version Constraint | Source |
|-----------|-----------|-------------------|--------|
| Language | Python | 3.12 | `Dockerfile` line 4 |
| Framework | FastAPI | >= 0.104.0 | `requirements.txt` line 1 |
| ASGI Server | Uvicorn | >= 0.24.0 | `requirements.txt` line 2 |
| Data Validation | Pydantic | >= 2.5.0 | `requirements.txt` line 4 |
| Database Driver | pyodbc | >= 5.0.0 | `requirements.txt` line 3 |
| ODBC Driver | ODBC Driver 17 for SQL Server | -- | `Dockerfile` line 15, `config/settings.py` line 78 |
| Secret Manager Client | google-cloud-secret-manager | >= 2.16.0 | `requirements.txt` line 6 |
| MIDI Parser | mido | >= 1.3.0 | `requirements.txt` line 7 |
| Music Analysis | music21 | >= 9.1.0 | `requirements.txt` line 8 |
| OAuth Client | authlib | >= 1.2.0 | `requirements.txt` line 10 |
| JWT Tokens | python-jose[cryptography] | >= 3.3.0 | `requirements.txt` line 11 |
| File Uploads | python-multipart | >= 0.0.6 | `requirements.txt` line 9 |
| Session Signing | itsdangerous | >= 2.1.0 | `requirements.txt` line 12 |
| HTTP Client | httpx | >= 0.24.0 | `requirements.txt` line 13 |

### Database
| Component | Technology | Source |
|-----------|-----------|--------|
| Engine | Microsoft SQL Server | `app/db/connection.py` line 22, `CLAUDE.md` line 82 |
| Hosting | Google Cloud SQL | `CLAUDE.md` line 81 |
| Instance | `flashcards-db` (shared) | `CLAUDE.md` line 81 |

### Frontend
| Component | Technology | Source |
|-----------|-----------|--------|
| Stack | Vanilla HTML/CSS/JS | `frontend/song.html`, `frontend/styles.css` |
| Audio | Tone.js (CDN) | `frontend/song.html` line 9 |
| MIDI | Web MIDI API (native) | `frontend/song.html` |
| Pages | index.html, song.html, quiz.html, progress.html, login.html | `frontend/` |
| Hosting | Cloud Run (nginx) | `frontend/Dockerfile` |

### Container
| Component | Value | Source |
|-----------|-------|--------|
| Base Image | python:3.12-slim-bookworm | `Dockerfile` line 4 |
| Exposed Port | 8080 | `Dockerfile` line 31 |
| Entrypoint | `uvicorn main:app --host 0.0.0.0 --port 8080` | `Dockerfile` line 34 |

---

## 5. Database Schema

### Schema Files
- `HarmonyLab-Schema-v1.0.sql` -- Full schema with GO batch separators (for SSMS/sqlcmd).
- `HarmonyLab-Schema-CloudSQL.sql` -- Cloud SQL compatible version (GO separators removed, `_min` suffix for case-insensitive collation handling). Referenced in `HARMONYLAB-DB-SETUP.md`.

### Core Tables (from `HarmonyLab-Schema-v1.0.sql`)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **Songs** | Song metadata | id, title, composer, arranger, original_key, tempo_marking, genre, time_signature, year_composed, notes, source_file_name, source_file_type, created_at, updated_at |
| **Sections** | Song structure (Intro, A, B, Bridge, Coda) | id, song_id (FK), name, section_order, repeat_count, notes. Unique on (song_id, section_order) |
| **Measures** | Container for chords within sections | id, section_id (FK), measure_number, created_at. Unique on (section_id, measure_number) |
| **Chords** | Core learning content | id, measure_id (FK), beat_position, chord_symbol, roman_numeral, key_center, function_label, comments, chord_order. Unique on (measure_id, chord_order) |
| **ChordVocabulary** | Standardized chord notation lookup | id, canonical_symbol (unique), display_name, chord_type, intervals, aliases (JSON). Seeded with 30 chord types |
| **RomanNumeralVocabulary** | Standardized Roman numeral lookup | id, canonical_symbol (unique), scale_degree, quality, function_type. Seeded with 52 symbols |
| **MelodyNotes** | For Tone.js playback timing reference | id, song_id (FK), measure_number, beat_position, midi_note, duration, velocity |
| **UserSongProgress** | Per-user per-song progress tracking | id, user_id, song_id (FK), last_practiced, times_practiced, accuracy_rate, mastery_level (0-5), notes. Unique on (user_id, song_id) |
| **QuizAttempts** | Quiz history | id, user_id, song_id (FK), quiz_type, section_id (FK nullable), started_at, completed_at, total_questions, correct_answers, details (JSON) |

### Migration-Created Tables (from `app/migrations.py`)

| Table | Migration # | Purpose |
|-------|-------------|---------|
| **SongAnalysis** | 1 | Cached harmonic analysis results. Columns: id, song_id (FK unique), detected_key, manual_key_override, confidence, analysis_json, created_at, updated_at |
| **ChordAnalysisOverrides** | 2 | User overrides for auto-analysis. Columns: id, song_id (FK), chord_index, roman_override, function_override, key_context_override, is_pivot_chord, pivot_to_key, notes, created_at, updated_at. Unique on (song_id, chord_index) |
| **KeyRegions** | 3 | Key region boundaries for modulation tracking. Columns: id, song_id (FK), start_chord_index, end_chord_index, key_center, transition_type, pivot_chord_index, notes, is_user_defined, created_at. Unique on (song_id, start_chord_index) |
| **Users** | 4 | Authentication users. Columns: id, email (unique), display_name, google_id (unique), avatar_url, created_at, last_login_at, is_active. Indexed on email and google_id |

### Database Objects
- **View**: `vw_SongProgression` -- Joins Songs > Sections > Measures > Chords for full progression display (`HarmonyLab-Schema-v1.0.sql` lines 287-306)
- **Stored Procedure**: `sp_GetSongProgression(@SongId)` -- Returns full progression ordered by section, measure, chord (`HarmonyLab-Schema-v1.0.sql` lines 312-331)

### Data Hierarchy
```
Song
  -> Section (ordered by section_order)
    -> Measure (ordered by measure_number)
      -> Chord (ordered by chord_order, positioned by beat_position)
```

Source: `HarmonyLab-Kickoff.md` and schema FK constraints.

---

## 6. API Endpoints

All routes registered in `main.py` lines 102-115. Total: 45+ endpoints.

### Auth (`app/api/routes/auth.py`, prefix: `/api/v1/auth`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/google/login` | Initiate Google OAuth login flow |
| GET | `/google/callback` | Handle OAuth callback, create/update user, issue JWT tokens |
| POST | `/refresh` | Exchange refresh token cookie for new access token |
| GET | `/me` | Get current authenticated user profile (requires JWT) |
| POST | `/logout` | Clear auth cookies |

### Songs (`app/api/routes/songs.py`, prefix: `/api/v1/songs`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List songs with pagination (skip/limit) and optional genre filter |
| GET | `/{song_id}` | Get single song |
| POST | `/` | Create song |
| PUT | `/{song_id}` | Update song (partial update) |
| DELETE | `/{song_id}` | Delete song (cascades) |
| GET | `/{song_id}/notes` | **v2.0.1**: Get individual notes (MelodyNotes) for a song, ordered by measure/beat |

### Sections (`app/api/routes/sections.py`, prefix: `/api/v1/songs`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/{song_id}/sections` | List sections for a song |
| POST | `/{song_id}/sections` | Create section |
| DELETE | `/{song_id}/sections/{section_id}` | Delete section |

### Measures (`app/api/routes/measures.py`, prefix: `/api/v1/measures`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/` | Create measure |
| GET | `/{measure_id}` | Get measure with its chords |
| GET | `/section/{section_id}` | List measures for a section |
| PUT | `/{measure_id}` | Update measure |
| DELETE | `/{measure_id}` | Delete measure |

### Chords (`app/api/routes/chords.py`, prefix: `/api/v1/chords`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/` | Create chord |
| POST | `/bulk` | Bulk create chords (for imports) |
| GET | `/{chord_id}` | Get single chord |
| GET | `/measure/{measure_id}` | List chords in a measure |
| PUT | `/{chord_id}` | Update chord |
| DELETE | `/{chord_id}` | Delete chord |

### Vocabulary (`app/api/routes/vocabulary.py`, prefix: `/api/v1/vocabulary`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/chord-symbols` | List all chord vocabulary entries |
| GET | `/roman-numerals` | List all Roman numeral vocabulary entries |

### Quiz (`app/api/routes/quiz.py`, prefix: `/api/v1/quiz`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate` | Generate fill-in-the-blank quiz from a song |
| POST | `/submit` | Submit answers and get scored results |
| GET | `/attempts` | List quiz attempts for a user (optional song_id filter) |
| GET | `/attempts/{attempt_id}` | Get detailed results for a specific attempt |

### Progress (`app/api/routes/progress.py`, prefix: `/api/v1/progress`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all progress for a user |
| GET | `/song/{song_id}` | Get progress for a specific song (auto-creates if missing) |
| POST | `/song/{song_id}` | Update progress after practice (weighted accuracy: 70% old + 30% new) |
| GET | `/stats` | Aggregate statistics (songs practiced, accuracy, streak) |
| GET | `/history` | Recent quiz activity (configurable limit) |
| GET | `/songs` | Song progress list for all practiced songs |

### Imports (`app/api/routes/imports.py`, prefix: `/api/v1/imports`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/midi/preview` | Legacy: Upload and parse MIDI file, return preview (no DB save) |
| POST | `/midi/import` | Legacy: Import MIDI file and save to database |
| POST | `/score/preview` | **HL-014**: Universal format preview (.mscz .mscx .musicxml .mid) — returns title/key/tempo/chords |
| POST | `/score/import` | **HL-014**: Universal format import — saves to Cloud SQL |
| POST | `/batch` | **HL-018**: ZIP batch import — accepts ZIP of any supported formats, skips duplicates |
| POST | `/score/reparse-notes` | **v2.0.1**: Re-upload .mscz to extract individual notes for existing song. Query param: song_id. Clears old MelodyNotes, inserts new. |
| POST | `/seed-standards` | **HL-008**: Seed 15 jazz standards directly (no file upload); safe to call multiple times |

### Analysis (`app/api/routes/analysis.py`, prefix: `/api/v1/analysis`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/roman` | **v2.2.0**: Calculate Roman numeral for a chord symbol in a given key (params: symbol, key) |
| GET | `/songs/{song_id}/key-centers` | **v2.2.0**: Get key center regions and ii-V-I patterns for a song |
| GET | `/songs/{song_id}/patterns` | **v2.2.0**: Get detected harmonic patterns (ii-V-I, ii-V-i) for a song |
| POST | `/songs/{song_id}/transpose` | **v2.2.0**: Transpose song analysis by N semitones (session-only, not persisted) |
| GET | `/songs/{song_id}` | Get harmonic analysis (cached, with override application) |
| POST | `/songs/{song_id}` | Re-analyze with manual key override |
| PUT | `/songs/{song_id}/chord/{chord_index}` | Override analysis for a specific chord |
| DELETE | `/songs/{song_id}/chord/{chord_index}` | Remove chord override |
| GET | `/songs/{song_id}/overrides` | List all overrides for a song |

### Exports (`app/api/routes/exports.py`, prefix: `/api/v1/exports`) *(added 2026-02-27, HL-015)*
| Method | Path | Description |
|--------|------|-------------|
| GET | `/musescore/{song_id}` | Export song as annotated MuseScore file (.mscx or .mscz). Params: format (mscx/mscz), include_analysis (bool) |

### MIDI Input (`app/api/routes/midi_input.py`, prefix: `/api/v1/midi`) *(added 2026-02-27, HL-017)*
| Method | Path | Description |
|--------|------|-------------|
| POST | `/identify` | Identify chord from MIDI note numbers (for Web MIDI API / MIDI keyboard). Returns chord symbol, root, quality, optional Roman numeral |
| POST | `/rhythm/analyze` | Analyze rhythmic patterns from uploaded MIDI file |
| GET | `/rhythm/song/{song_id}` | Analyze rhythm for stored song (uses MelodyNotes or chord positions) |
| GET | `/webmidi-check` | Web MIDI API setup info and browser compatibility |

---

## Schema

**Introspection URL:** https://harmonylab-wmrla7fhwa-uc.a.run.app/openapi.json
**Note:** harmonylab.rentyourcio.com is the frontend (React). Schema is on the backend direct URL.
**Framework:** FastAPI (auto-generated OpenAPI 3.x)

Phase 0 schema fetch:
```bash
curl -s https://harmonylab-wmrla7fhwa-uc.a.run.app/openapi.json | python -c "
import sys, json
spec = json.load(sys.stdin)
paths = spec.get('paths', {})
for p in sorted(paths.keys()):
    print(p)
"
```

Key endpoint paths (update as routes change):
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Health check |
| /api/v1/songs/ | GET, POST | List or create songs |
| /api/v1/songs/{song_id} | GET, PUT, DELETE | Manage song |
| /api/v1/songs/{song_id}/notes | GET | Get song note data |
| /api/v1/songs/{song_id}/imports | GET | Import history for song |
| /api/v1/imports/score/preview | POST | Preview score file before import |
| /api/v1/imports/score/import | POST | Import score file (.mscx/.musicxml) |
| /api/v1/imports/batch | POST | Batch import multiple files |
| /api/v1/analysis/songs/{song_id} | GET | Analyze song harmony |
| /api/v1/analysis/songs/{song_id}/patterns | GET | Harmonic patterns (ii-V-I etc.) |
| /api/v1/analysis/songs/{song_id}/key-centers | GET | Key center analysis |
| /api/v1/chords/ | GET | List chords |
| /api/v1/quiz/generate | POST | Generate chord recognition quiz |

---

## 7. Services

### Universal Score Parser (`app/services/score_parser.py`) *(added 2026-02-21, updated 2026-02-22)*

Unified parser for all supported music file formats. Key components:

- **`ParsedScore` dataclass**: title, key, time_signature, tempo, chords (list of `ScoreChord`).
- **`ScoreChord` dataclass**: measure_number, beat_position, chord_symbol, chord_order.
- **`parse_music_file(file_path, filename)`**: Dispatches by extension.
  - `.mscz` → unzip with `zipfile`, extract `.mscx`, parse XML with `xml.etree.ElementTree`
  - `.mscx` → parse XML directly. Uses `measure.iter('Harmony')` to find `<Harmony>/<name>` elements at any nesting depth (MuseScore 4 wraps in `<voice>`).
  - `.musicxml/.xml/.mxl` → `music21.converter.parse()`, extracts `harmony.ChordSymbol` objects
  - `.mid/.midi` → delegates to existing `app.services.midi_parser.parse_midi_file()`
- **Root numbering** (fixed 2026-02-27): Two distinct systems depending on MuseScore version:
  - `_CHROMATIC_ROOT` (MS 4.4.x and earlier): chromatic numbering (14=C, 15=Db, 16=D, ..., 25=B)
  - `_TPC_ROOT` (MS 4.5.x+): Tonal Pitch Class / circle-of-fifths (14=C, 15=G, 16=D, 17=A, ..., 13=F, 12=Bb)
  - Version auto-detected from `<programVersion>` XML tag. Falls back to chromatic if version unavailable.
- **harmonyInfo wrapper** (fixed 2026-02-27): MuseScore 4.6+ wraps `<name>` and `<root>` inside `<harmonyInfo>` subelement. Parser checks direct children first, then falls back to harmonyInfo child.
- **N.C. handling**: "N.C." (no chord) markers stored as-is, skipped from root prepending.
- **Key maps**: `_SHARP_KEYS` (0=C…7=C#), `_FLAT_KEYS` (-1=F…-7=Cb)
- **Diagnostic logging** (added 2026-02-22): logs measures_scanned, measures_with_harmony, total_chords. Warns if 0 chords found.
- **MuseScore 4 note** (2026-02-22): MuseScore 4 wraps content in `<voice>` elements. Fixed by using `iter()` instead of direct child iteration.
- **Import data capture audit** (HL-033, 2026-03-05): Captured: chord symbols, melody notes (first staff only via MelodyNotes table), key signature, time signature, tempo. NOT captured: inner voices (harmony/bass parts), dynamics, per-section tempo/key changes, phrase breaks/rehearsal marks.

### MIDI Parser (`app/services/midi_parser.py`)

Parses MIDI files using the `mido` library. Key components:

- **CHORD_TEMPLATES**: 30 chord type templates defined as interval arrays (triads, sevenths, sixths, extended, suspended, altered dominants). Source: lines 57-100. **v2.1.0**: Added 7b9, 7#9, 7b13, 7#11, 7alt, 6/9, m6/9 templates.
- **NOTE_NAMES**: Chromatic scale `['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']`. Source: line 102.
- **`parse_midi_file(file_path)`**: Main entry point. Returns `ParsedSong` with title, tempo, time_signature, total_measures, and list of `ChordData` objects.
- **Track selection**: Finds the track with most note-on events as the chord track. Source: lines 252-268.
- **`identify_chord(notes)`**: Maps MIDI notes to chord symbol via rotation-based root detection with template matching. Tries every pitch class as candidate root, scores exact matches highest (1000+), then subset matches (coverage-based). Root-position voicings get bonus. Handles inversions correctly. Source: lines 124-205.
- **`extract_chords_from_track()`**: Time-window grouping algorithm — notes whose onsets fall within `chord_window_beats` (default 2.0) are grouped. Handles both block-chord and arpeggiated styles. Source: lines 313-383.

## Chord Identification — Interval Priority Rule

When identifying chords from a note set:
1. Evaluate structural intervals FIRST: sus4, sus2, dim, aug, power chords.
2. Only attempt slash-chord pattern matching AFTER structural types are ruled out.
3. Extended voicings (9, 11, 13) should be tested within the structural type, not as separate candidates.

Root cause: HL-026 — G9sus4 was misidentified as F6/9 because slash-chord
matching ran before sus4 evaluation. Fixed in v2.1.1. This ordering must
be preserved in all future chord ID refactors.

### Key Center Detection (`app/services/key_center_service.py`) *(added 2026-03-05, HL-037/HL-042)*

Interval-based key center detection and ii-V-I pattern recognition, independent of global key.

- **`_parse_chord(symbol)`**: Parses chord symbol into root pitch class (0-11) and quality flags (is_minor, is_dom7, is_maj7, is_half_dim, is_dim, is_major_triad).
- **`detect_ii_v_i_patterns(chords)`**: Detects ii-V-I (major) and ii-V-i (harmonic minor) patterns. Uses interval math: ii root at +2 semitones from I, V root at +7 from I. V must be dom7. Returns list of pattern dicts with type, indices, target_key, mode, label, start/end_measure.
- **`detect_key_centers(chords, detected_key)`**: 7-step algorithm: (1) home key from last chord (90% jazz rule), (2) chord-key map from patterns, (3) best-fit assignment per chord, (4) raw regions from consecutive assignments, (5) merge relative major/minor regions, (6) absorb tiny regions (<3 chords), (7) merge consecutive same-key regions. Returns list of region dicts with start/end index, start/end measure, key_center, mode, confidence (0.8 for pattern-backed, 0.5 for inferred). **v2.2.1**: Added steps 5-7 to reduce over-fragmentation (Autumn Leaves went from 13 regions to 1).
- **`_are_relative_keys(key1, mode1, key2, mode2)`**: Checks if two keys share same key signature (relative major/minor, 3 semitones apart). **v2.2.1**: Added to support region merging.
- **Note names**: Uses flat-preferred jazz convention: `['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']`.
- **Autumn Leaves (song 34)**: Stored in Bb major / G minor (original_key="G minor"). Last chord=Gm. Contains ii-V-I/Bb and ii-V-i/Gm patterns. Not Am/C — depends on the arrangement imported.

### Harmonic Analysis (`app/services/analysis_service.py`)

Uses `music21` for Roman numeral analysis, key detection, and pattern recognition.

- **`HarmonicAnalyzer` class**: Core analyzer.
  - `FUNCTION_COLORS`: tonic=#22c55e (green), subdominant=#3b82f6 (blue), dominant=#ef4444 (red), secondary=#f59e0b (orange), chromatic=#8b5cf6 (purple), diminished=#6b7280 (gray). Source: lines 15-23.
  - `analyze_progression(chords, key_override)`: Main method. Returns dict with detected_key, confidence, analyzed chords, and patterns.
  - `_detect_key(chords)`: Auto-detects key using music21's `analyze('key')`. Iterates all chords to find up to 16 valid ones (skips empty/N.C.). Converts ChordSymbol to plain Chord to avoid Krumhansl-Schmuckler algorithm issues.
  - `_normalize_chord_symbol(symbol)`: Normalizes chord symbols for music21. Converts flat notation (Ab → A-), MuseScore jazz font shorthand (^→maj, -→m, 0→dim, t/△→maj7), strips parenthetical extensions `(b5)→b5`, `(#9)→#9`, and handles 6/9→69, Maj→(empty). **v2.1.0**: Added parenthesis stripping for altered extensions.
  - `_fallback_roman(symbol)`: **v2.1.0**: Derives Roman numeral from root note alone when music21 can't parse the full chord symbol. Calculates pitch interval from tonic, maps to scale degree (I-VII with accidentals), determines case from quality (minor/dim = lowercase).
  - `_format_jazz_roman(rn, chord, symbol)`: Formats Roman numerals in jazz style (e.g., "IVmaj7" not "i#653"). Handles secondary dominants. Source: lines 141-155.
  - `_get_quality_suffix(symbol)`: Maps ~30 chord suffixes (Maj7, m7, dim, etc.) to jazz notation. Source: lines 157-212.
  - `_get_function(rn)`: Maps scale degrees to harmonic function. Degrees 1,3,6=tonic; 2,4=subdominant; 5,7=dominant; else=chromatic. Source: lines 214-223.
  - `_detect_patterns(chords)`: Legacy basic ii-V-I detection via Roman numeral text matching. Source: lines 225-242. **v2.2.0**: Superseded by `key_center_service.detect_ii_v_i_patterns()` for interval-based detection.
- **`analyze_song(chords, key_override)`**: Module-level convenience function. Source: lines 245-248.

### MuseScore Export (`app/services/score_exporter.py`) *(added 2026-02-27, HL-015)*

Generates annotated MuseScore files (.mscx/.mscz) from HarmonyLab song data + analysis results.

- **`export_mscx(song_data, analysis_data)`**: Generates .mscx XML string with:
  - TPC root numbering for Harmony elements (circle-of-fifths via `_NOTE_TO_TPC` map)
  - Chord symbols as `<Harmony>` elements with root and name
  - Roman numerals as color-coded `<StaffText>` annotations (colors match HarmonicAnalyzer FUNCTION_COLORS)
  - Metadata: title, composer, key signature, tempo, time signature
- **`export_mscz(song_data, analysis_data)`**: Wraps .mscx in ZIP container for .mscz format
- **`_parse_root_from_symbol(symbol)`**: Extracts root note and quality from chord symbol string

### Rhythm Analyzer (`app/services/rhythm_analyzer.py`) *(added 2026-02-27, HL-017)*

Analyzes rhythmic patterns from MIDI data.

- **`analyze_rhythm(note_onsets, tpb, ts_n, ts_d)`**: Core analysis function. Returns:
  - `feel`: swing/straight/reverse_swing (based on IOI ratio > 1.3 = swing)
  - `swing_ratio`: Average long/short ratio for eighth note pairs
  - `syncopation_score`: Percentage of notes on off-beats
  - `density_notes_per_beat`: Rhythmic density metric
  - `primary_subdivision`: Most common note value (quarter/eighth/sixteenth/triplet)
  - `subdivision_breakdown`: Count of each subdivision type
- **`analyze_rhythm_from_midi(file_path)`**: Parses MIDI file with mido, returns per-track + overall analysis
- Requires minimum 4 notes for meaningful analysis

### Authentication (`app/services/auth_service.py`)

JWT token management based on Super-Flashcards pattern.

- Algorithm: HS256. Source: line 14.
- Access token expiry: 15 minutes. Source: line 15.
- Refresh token expiry: 30 days. Source: line 16.
- Functions: `create_access_token`, `create_refresh_token`, `decode_refresh_token`, `decode_access_token`, `sanitize_oauth_data`, `generate_username_from_email`.
- JWT signing key sourced from Secret Manager (`harmonylab-jwt-secret`). Source: `config/settings.py` line 110.
- Google OAuth flow uses `authlib` with `openid email profile` scope. Source: `app/api/routes/auth.py` lines 35-47.
- On successful OAuth callback, redirects to frontend with access token as URL parameter: `{frontend_url}/index.html?auth=success&token={access_token}`. Source: `app/api/routes/auth.py` line 223.
- Production frontend URL: `https://harmonylab.rentyourcio.com`. Source: `app/api/routes/auth.py` line 219.

---

## 8. Database Connectivity

### Connection Architecture (`app/db/connection.py`)

Two classes coexist:

1. **`Database` class** (singleton at module level as `db`): Builds pyodbc connection string, provides `get_connection()` and `test_connection()`. Autocommit enabled on connections. Source: lines 12-51, 55.

2. **`DatabaseConnection` class** (instantiated per-request or via `get_db()` dependency): Wrapper with query execution methods:
   - `execute_query(query, params)` -- Returns list of dicts. Source: lines 72-85.
   - `execute_scalar(query, params)` -- Returns first column of first row. Source: lines 87-99.
   - `execute_non_query(query, params)` -- INSERT/UPDATE/DELETE, returns rowcount, calls `conn.commit()`. Source: lines 101-114.
   - `execute_with_commit(query, params)` -- Query with commit, returns list of dicts. Source: lines 116-130.

3. **`get_db()` function**: FastAPI dependency returning `DatabaseConnection()`. Source: lines 133-135.

### Connection String Format
```
DRIVER={ODBC Driver 17 for SQL Server};SERVER={db_server};DATABASE={db_name};UID={db_user};PWD={db_password};Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;
```
Source: `app/db/connection.py` lines 20-30.

### Usage Pattern
Some route modules use `Depends(get_db)` for dependency injection (songs, analysis). Others instantiate `DatabaseConnection(settings)` directly (quiz, progress, chords, imports, auth). Both patterns work -- they use the same underlying singleton `db` for connection creation.

---

## 9. Deployment

### Backend Deployment Command
```powershell
cd "G:\My Drive\Code\Python\harmonylab"
gcloud run deploy harmonylab --source . --region us-central1 --allow-unauthenticated
```
Source: `CLAUDE.md` lines 100-103.

### Frontend Deployment Command
```powershell
cd "G:\My Drive\Code\Python\harmonylab\frontend"
gcloud run deploy harmonylab-frontend --source . --region us-central1 --allow-unauthenticated
```
Source: `CLAUDE.md` lines 106-109.

### CI/CD Pipeline (`.github/workflows/deploy.yml`)
- **Trigger**: Push to `main` branch. Source: line 4.
- **Authentication**: Workload Identity Federation via `google-github-actions/auth@v2`. Uses GitHub secrets `WIF_PROVIDER` and `WIF_SERVICE_ACCOUNT`. Source: lines 27-30.
- **Build**: Docker build, tag with commit SHA, push to Artifact Registry at `us-central1-docker.pkg.dev/super-flashcards-475210/harmonylab/harmonylab:{sha}`. Source: lines 39-44.
- **Deploy**: `gcloud run deploy` with `--set-secrets` flag injecting 4 database secrets as environment variables. Source: lines 46-53.
- **Note**: Only deploys backend (`harmonylab` service). Frontend (`harmonylab-frontend`) has NO CI/CD. CONFIRMED 2026-03-07. Frontend must always be deployed manually: `cd frontend/ && gcloud run deploy harmonylab-frontend --source . --region us-central1 --allow-unauthenticated --quiet`

### ✅ Branch RESOLVED (2026-02-20, HL-007)
Active development branch is now `main`. `origin/master` deleted. GitHub default branch set to `main`.
CI/CD workflow (`.github/workflows/deploy.yml`) already triggered on `main` — no change needed.
Local branch renamed, tracking `origin/main`. `CLAUDE.md` updated: `git push origin master` -> `git push origin main`.

### Container (`Dockerfile`)
- Base image: `python:3.12-slim-bookworm`
- Installs Microsoft ODBC Driver 17 from Microsoft's Debian 12 repository
- Copies `requirements.txt` first for layer caching, then full app
- Exposes port 8080
- Runs: `uvicorn main:app --host 0.0.0.0 --port 8080`

Source: `Dockerfile` lines 1-34.

### Log Viewing
```powershell
gcloud run logs read harmonylab --region=us-central1 --limit=50
gcloud run logs read harmonylab-frontend --region=us-central1 --limit=50
```
Source: `CLAUDE.md` lines 113-115.

### PINEAPPLE Test Protocol
Before debugging any deployment issue:
1. Add `"canary": "PINEAPPLE-99999"` to `/health` endpoint
2. Deploy
3. Verify with curl that the canary value appears
4. If missing, deployment itself failed -- fix that first

Source: `CLAUDE.md` lines 210-217.

### Health Check Verification
```
curl https://harmonylab.rentyourcio.com/health
```
Source: `CLAUDE.md` line 169.

## CI/CD
- GitHub Actions: `.github/workflows/deploy.yml`
- Trigger: push to `main` or manual `workflow_dispatch`
- Auth: Workload Identity Federation via `WIF_PROVIDER` and `WIF_SERVICE_ACCOUNT` secrets
- Deploy method: Docker build + GAR push + Cloud Run deploy (not `--source .`)
- Health check step: added 2026-02-26 (PM-MS1)
- Health check URL: https://harmonylab.rentyourcio.com/health
- **Note**: Uses WIF instead of `credentials_json`. Consider migrating to `GCP_SA_KEY` for consistency.

---

## 10. Application Startup

On startup (`main.py` lines 45-52), the FastAPI `startup` event runs `run_migrations()` from `app/migrations.py`. This function:

1. Creates `SongAnalysis` table if not exists (Migration 1)
2. Creates `ChordAnalysisOverrides` table if not exists (Migration 2)
3. Creates `KeyRegions` table if not exists (Migration 3)
4. Creates `Users` table if not exists (Migration 4) plus indexes on email and google_id

All migrations are idempotent (check `INFORMATION_SCHEMA.TABLES` before creating). Failures are caught and logged as warnings (non-fatal). Source: `app/migrations.py` lines 10-132.

### Middleware Stack (registered in `main.py` lines 27-42)
1. **CORSMiddleware**: `allow_origins=["https://harmonylab.rentyourcio.com", "https://harmonylab-frontend-wmrla7fhwa-uc.a.run.app", "http://localhost:8080", "http://localhost:3000"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`. **v2.2.2**: Explicit origins required — wildcard `*` is invalid with `allow_credentials=True` (browsers reject it).
2. **SessionMiddleware**: Uses JWT secret key, `same_site="none"`, `https_only=True`. Required for OAuth state storage.

### Router Registration Order (`main.py` lines 102-115)
1. auth (first, for login/logout)
2. songs
3. sections
4. vocabulary
5. measures
6. chords
7. progress
8. quiz
9. imports
10. analysis
11. exports *(added 2026-02-27, HL-015)*
12. midi_input *(added 2026-02-27, HL-017)*

---

## 11. Authentication Flow

Google OAuth flow implemented in `app/api/routes/auth.py`:

1. **Login**: `GET /api/v1/auth/google/login` redirects to Google with `openid email profile` scope.
2. **Callback**: `GET /api/v1/auth/google/callback` receives OAuth token from Google, extracts user info.
   - If user exists by `google_id`: updates `last_login_at`.
   - If user exists by `email` but no `google_id`: links Google account.
   - If new user: creates record in `Users` table.
   - Issues JWT access token (15 min) and refresh token (30 day, HTTP-only cookie).
   - Redirects to `{frontend_url}/index.html?auth=success&token={access_token}`.
3. **Token Refresh**: `POST /api/v1/auth/refresh` reads refresh token from cookie, verifies user still active, issues new token pair.
4. **Get User**: `GET /api/v1/auth/me` requires valid JWT (Bearer header or `access_token` cookie).
5. **Logout**: `POST /api/v1/auth/logout` clears cookies.

**Dependency**: `get_current_user(request)` function extracts JWT from Authorization header or cookie, decodes it, verifies user exists and is active in database. Source: `app/api/routes/auth.py` lines 53-101.

**Optional Auth**: `get_current_user_optional(request)` returns None instead of raising exception. Source: `app/api/routes/auth.py` lines 104-109.

**Note**: Most API routes do NOT currently require authentication. The `user_id` parameter is passed as a query parameter (e.g., quiz and progress endpoints). This is a known architectural gap -- endpoints accept user_id directly rather than extracting it from JWT.

---

## 12. Quiz System

### Quiz Generation (`POST /api/v1/quiz/generate`)

Source: `app/api/routes/quiz.py` lines 17-159.

1. Validates song exists.
2. Fetches all chords for the song (or specific section), ordered by section_order, measure_number, chord_order.
3. Filters out chords with empty/null symbols.
4. Excludes index 0 from blank candidates (so every question has at least 1 context chord).
5. Selects blanks: uses `num_questions` if specified, otherwise `blank_percentage` (default 30%).
6. For each blank:
   - Provides up to 3 preceding context chords.
   - Generates 4 multiple-choice options (1 correct + up to 3 wrong from song's unique chords).
   - Falls back to common jazz chords if not enough wrong options: `['Cmaj7', 'Dm7', 'Em7', 'Fmaj7', 'G7', 'Am7', 'Bm7b5', 'Cm7', 'Fm7', 'Bb7', 'Ebmaj7', 'Abmaj7', 'Dbmaj7']`.
7. Creates `QuizAttempts` record with answers stored as JSON in `details` column.
8. Returns `attempt_id`, `total_questions`, and `questions` array.

### Quiz Submission (`POST /api/v1/quiz/submit`)

Source: `app/api/routes/quiz.py` lines 162-243.

1. Retrieves attempt record and stored correct answers.
2. Case-insensitive comparison of user answers vs. correct answers.
3. Updates `QuizAttempts` with `completed_at`, `correct_answers`, and results JSON.
4. Calls `update_song_progress()` to update `UserSongProgress` with weighted accuracy.
5. Returns `QuizResult` with per-question breakdown.

### Progress Tracking

Accuracy uses weighted average: `new_accuracy = (old * 0.7) + (new * 0.3)`. Source: `app/api/routes/progress.py` line 135.

Mastery level (0-5 scale) adjusts based on accuracy:
- >= 95%: increment (max 5)
- >= 80%: hold (max 4)
- < 60%: decrement (min 0)

Source: `app/api/routes/progress.py` lines 143-148.

---

## 13. Known Issues and Technical Debt

### From `PROJECT_STATUS.md` (dated 2025-01-28)
| Issue | Severity | Source |
|-------|----------|--------|
| 0% test coverage | High | `PROJECT_STATUS.md` lines 97, 162 |
| Frontend not built | High | `PROJECT_STATUS.md` line 96. Frontend directory is empty (no tracked source files) |
| Chord voicing playback incorrect | Medium | `PROJECT_STATUS.md` line 104 |
| MIDI parser includes melody notes in chord detection | Low | `PROJECT_STATUS.md` line 105 |
| No manual chord editing UI | Medium | `PROJECT_STATUS.md` line 106 |
| MusicXML import not implemented | Low | **RESOLVED 2026-02-21 (HL-014)**: Universal /score/preview + /score/import endpoints now handle all formats |

### From Sprint 2026-02-18 Investigation
| Item | Status | Detail |
|------|--------|--------|
| Analysis quality UAT | **Conditional Pass** | Roman numerals work, chord symbols pass, confidence scores need improvement |
| MIDI import P0 | ✅ **Resolved** | Arpeggio grouping fix; BWV 846 imports correctly with chords |
| Songs imported | 2 | Corcovado + Bach BWV 846 (Prelude in C major) |
| Audio playback | ✅ Working | Confirmed 2026-02-15 (corrected stale handoff data) |
| Quiz system | ✅ Working | Backend + frontend UI functional |
| Roman numeral formatting | ✅ Fixed | jazz Roman numerals working |

### Active Bugs
| Bug | Severity | Description |
|-----|----------|-------------|
| Chord voicing playback inconsistent | Medium | Some chord voicings play incorrectly but audio playback is confirmed Working. |

> **HL-014 RESOLVED (2026-02-21):** Universal score parser (score_parser.py). /score/preview + /score/import endpoints. Supports .mscz, .mscx, .musicxml, .mid. Old /musicxml/* 501 stubs removed.
> **HL-018 RESOLVED (2026-02-21):** /batch endpoint accepts ZIP of any supported formats, duplicate detection, per-file error logging.
> **HL-008 RESOLVED (2026-02-21):** 15 jazz standards seeded via /seed-standards. All in DB and query-able. Songs: Autumn Leaves, All The Things You Are, Blue Bossa, Fly Me To The Moon, Take The A Train, Misty, Summertime, Satin Doll, So What, Wave, Maiden Voyage, Watermelon Man, Round Midnight, Footprints, There Will Never Be Another You.
> **CHD-01 REWORK RESOLVED (2026-02-22):** `chord-modal` (Analysis view, the default view) now has Root/Quality/Extension/Bass `<select>` dropdowns replacing the old readonly `modal-symbol` text input. `saveOverride()` PUTs chord symbol change to `/api/v1/chords/{id}` first, then saves analysis override. `parseChordSymbol()` is reused to pre-populate dropdowns on open. The `chord-edit-modal` (Chords view) is unchanged.
> **IMP-03 RESOLVED (2026-02-22):** `.mscz` parser: changed direct child iteration to `measure.iter('Harmony')` — fixes MuseScore 4 `<voice>` nesting. Fixed operator precedence bug. Added diagnostic logging. Added specific user message for 0-chord MuseScore imports.
> **HL-009 CONFIRMED (2026-02-21):** Chord dropdown editing already implemented in song.html. No change needed.
> **HL-008 EXPANDED (2026-02-27):** 10 additional jazz standards imported from .mscz files (IDs 58-67): Quizas Quizas Quizas, Amazing Grace, So What, My Foolish Heart, Nardis, Baubles Bangles and Beads, Bouree-Bach, Almost Like Being in Love, Amor em Paz, Manha de Carnaval. 8/10 analysis confidence ≥50%.
> **HL-012 RESOLVED (2026-02-27):** Chord granularity improved. analysis_service.py _normalize_chord_symbol() now handles MuseScore jazz font (^=maj, -=m, 0=dim, t=maj7). _detect_key() iterates all chords, converts ChordSymbol to plain Chord for better Krumhansl-Schmuckler results. Analysis output enriched with measure/beat context and total_measures count. Decimal serialization bug fixed.
> **HL-015 RESOLVED (2026-02-27):** MuseScore export via GET /api/v1/exports/musescore/{song_id}. Generates .mscx or .mscz with TPC root numbering, chord symbols as Harmony elements, color-coded Roman numeral StaffText annotations.
> **HL-017 RESOLVED (2026-02-27):** Rhythm analysis (swing/straight detection, syncopation scoring, subdivision breakdown) + MIDI keyboard input (POST /api/v1/midi/identify for real-time chord ID via Web MIDI API). Per-track MIDI file analysis. Song rhythm analysis from MelodyNotes or chord positions.
> **PARSER FIX (2026-02-27):** score_parser.py: Dual root numbering (chromatic for MS 4.4.x, TPC for MS 4.5+), version auto-detection, harmonyInfo wrapper support for MS 4.6+, N.C. handling.
> **HL-007 RESOLVED (2026-02-20):** Branch renamed master->main. origin/master deleted. GitHub default = main.
> **HL-010 RESOLVED (2026-02-20):** song.html now defaults to Analysis view.
> **HL-011 UPDATED (2026-03-07):** Version fetch changed from backend root URL to frontend `/health` endpoint in both `auth.js` and `login.html`. Frontend nav badges now show the frontend version (2.2.3), not the backend version (2.2.2). This is correct: frontend should display its own version.
> **HL-013 DOCUMENTED (2026-02-20):** MIDI files are temp-only (tempfile.NamedTemporaryFile, deleted after parse). Only chord data in Cloud SQL. No GCS used. No persistence issue for Cloud Run.
> **HL-MS2 FIX-1 RESOLVED (2026-02-28):** Song 65 "No chords found" — Song 50 (duplicate "Almost Like Being in Love") had 0 chords. analysis.py now returns empty analysis with helpful message instead of 404. Songs 61/69 have 31 chords. Delete song UI added to clean up duplicates.
> **HL-MS2 FIX-2 RESOLVED (2026-02-28):** Note extraction [object Object] — Frontend sent song_id in FormData but backend expects Query param. Fixed to send as URL query param. Added robust error extraction for non-string detail fields.
> **HL-MS2 FIX-3 RESOLVED (2026-02-28):** Roman numeral "?" — analysis_service._normalize_chord_symbol() now strips parenthetical extensions (b5), (#9), (b9). Added _fallback_roman() deriving Roman numeral from root-to-tonic interval when music21 fails. Reduced Song 65 from ~15 "?" to 0.
> **HL-NEW-001 RESOLVED (2026-02-28):** MIDI Quiz Mode — Listen/Quiz toggle on song detail page. App shows target chord, PL plays on MIDI keyboard, app scores correct/incorrect. Sequential and random modes. Score tracking.
> **HL-NEW-002 RESOLVED (2026-02-28):** MIDI notes display — Real-time display of individual note names (e.g., G3, B3, D4, F4) alongside chord ID. Uses activeNotes Set. Clears after 2s timeout.
> **HL-NEW-003 RESOLVED (2026-02-28):** Altered chord templates — Added 7b9, 7#9, 7b13, 7#11, 7alt, 6/9, m6/9 to CHORD_TEMPLATES. Rotation-based matching + subset scoring handles inversions and partial voicings.
> **HL-NEW-005 RESOLVED (2026-02-28):** Delete song — UI button with confirmation dialog on song detail page. Uses existing DELETE /api/v1/songs/{id} endpoint with cascade.
> **HL-MS2-FIX BUG 1 RESOLVED (2026-03-01):** Quiz page MIDI display — Added MIDI panel HTML (status, notes display, chord display) + JS (initMIDI, updateMIDIDevices, handleMIDIMessage, updateMIDINotesDisplay, midiToNoteName, scheduleMIDIIdentify) to quiz.html. CSS already existed in styles.css. Backend endpoint already existed.
> **HL-MS2-FIX BUG 2 RESOLVED (2026-03-01):** G9sus4 chord ID — Added '9sus4': [0, 5, 7, 10, 14] to CHORD_TEMPLATES in midi_parser.py. Existing bass-note preference (root_pos_bonus=50) correctly breaks ties in favor of bass note as root. G3,C4,D4,F4,A4 now returns G9sus4 instead of F6/9.
> **HL-MS2-FIX BUG 3 RESOLVED (2026-03-01):** Cmaj9 Roman numeral in Edit modal — Added GET /api/v1/analysis/roman?symbol=X&key=Y endpoint (analysis.py). updateAnalysisChordPreview() in song.html now calls this endpoint to recalculate modal-roman-auto field when dropdowns change. Added onchange to key context input.
> **HL-MS2-FIX BUG 4 RESOLVED (2026-03-01):** Quiz feedback timing — Changed setTimeout from 1500ms to 2000ms (correct) / 3000ms (incorrect) in both quiz.html and song.html.
> **HL-MS2-FIX BUG 5 RESOLVED (2026-03-01):** Quiz UX labels — quiz.html title changed to "Chord Quiz (Library)". song.html quiz radio button changed to "Song Practice" with "Practice: [Song Name]" header and tooltip.

### Architectural Gaps
| Gap | Description |
|-----|-------------|
| Auth not enforced on most endpoints | Routes accept `user_id` as query parameter rather than extracting from JWT. Source: `app/api/routes/quiz.py` line 18, `app/api/routes/progress.py` line 16 |
| No database migration framework | Uses hand-written idempotent migrations in `app/migrations.py`. No rollback capability. |
| CORS now explicit origins | Fixed v2.2.2: explicit allow_origins list (`harmonylab.rentyourcio.com` + Cloud Run frontend URL + localhost). Wildcard was broken with allow_credentials=True. |
| Inconsistent DB access pattern | Some routes use `Depends(get_db)`, others instantiate `DatabaseConnection(settings)` directly. |

---

## 14. Compliance Directives

All sourced from `CLAUDE.md`.

### Before ANY Work (LL-045)
1. Read entire CLAUDE.md file
2. State what you learned: "Backend service is harmonylab, frontend is harmonylab-frontend, database is HarmonyLab"
3. Never invent infrastructure values

Source: `CLAUDE.md` lines 148-151.

### Definition of Done (Mandatory for ALL Tasks)
- Code changes complete
- Tests pass (if applicable)
- All changes staged and committed: `git commit -m "type: description (vX.X.X)"`
- Pushed: `git push origin master`
- Backend deployed
- Frontend deployed
- Health check passes
- Version matches
- UAT checklist created and executed (for features)
- Handoff created with deployment verification

Source: `CLAUDE.md` lines 153-183.

### Before ANY Handoff (LL-030, LL-049)
1. Git commit and push (MANDATORY)
2. Deploy code (you own deployment)
3. Run tests: `pytest tests/ -v`
4. Verify with PINEAPPLE test
5. Include test output in handoff
6. Never say "complete" without proof

Source: `CLAUDE.md` lines 187-193.

### Locked Vocabulary (LL-049)
Words requiring proof (deployed revision + test output): "Complete", "Done", "Finished", "Ready", "Implemented", "Fixed", "Working", checkmark emoji next to features. Without proof, say: "Code written. Pending deployment and testing."

Source: `CLAUDE.md` lines 195-201.

### Forbidden Phrases
- "Test locally" (no localhost exists)
- "Let me know if you want me to deploy" (you own deployment)
- "Please run this command" (you run commands)

Source: `CLAUDE.md` lines 203-206.

### Handoff Bridge Protocol
All responses to Claude.ai/Corey MUST use the handoff bridge: Create file, run `handoff_send.py`, provide URL. No exceptions.

Source: `CLAUDE.md` lines 5-9.

### Handoff Lifecycle
1. Note ID (HO-XXXX) from handoff header
2. Archive handoff to `handoffs/archive/HO-XXXX_request.md`
3. Delete from inbox (garbage collect)
4. Completion response must include table with ID, Project, Task, Status, Commit, Handoff URL
5. Git commit format: `feat: [description] (HO-XXXX)` or `fix: [description] (HO-XXXX)`

Source: `CLAUDE.md` lines 14-50.

### Security Requirements
- NEVER hardcode secrets in code, handoffs, logs, or git
- ALWAYS use GCP Secret Manager
- Reference secrets by name, not value
- Rotate immediately if accidentally exposed

Source: `CLAUDE.md` lines 228-258.

---

## 15. Roadmap and Version History

### Version Timeline
| Version | Key Features | Source |
|---------|-------------|--------|
| Phase 0 | Foundation -- project structure, dependencies, models, basic routes | `ROADMAP.md` lines 5-15 |
| Sprint 1 | Core CRUD, Cloud Run deployment, MIDI parser, database schema, 36 endpoints | `PROJECT_STATUS.md` lines 12-13 |
| v1.3.0 | Harmonic analysis (music21), chord overrides, key regions. UAT had mixed results (14 pass, 13 fail). Re-scoped. | Handoff files in `handoffs/inbox/` |
| v1.8.0 | Google OAuth authentication (Users table, JWT, authlib). Current deployed version. | `main.py` line 17, `app/migrations.py` Migration 4, `app/api/routes/auth.py` |

### Roadmap Phases (from `ROADMAP.md`)
| Phase | Name | Status |
|-------|------|--------|
| Phase 0 | Foundation | Complete |
| Phase 1 | Core CRUD & Database | Complete (Sprint 1) |
| Phase 2 | File Import (MIDI/MusicXML) | **COMPLETE** (2026-02-21) — MIDI + MusicXML + MuseScore all supported via /score/* endpoints |
| Phase 3 | Playback System (Tone.js) | Not started -- design exists but no code |
| Phase 4 | Quiz System | Backend complete, no frontend |
| Phase 5 | Progress Tracking | Backend complete, no frontend |
| Phase 6 | UI Polish & Mobile | Not started |
| Phase 7 | Deployment | Complete (Cloud Run live) |
| Phase 8 | Data Population | **27+ songs in DB** (2026-02-27): 2 legacy MIDI + 15 seeded jazz standards + 10 imported from .mscz MuseScore files (Quizas, Amazing Grace, So What, My Foolish Heart, Nardis, Baubles Bangles and Beads, Bouree-Bach, Almost Like Being in Love, Amor em Paz, Manha de Carnaval). Batch import via ZIP available. |

### Re-scoped Plan (from handoff architectural decisions)
After v1.3.0 UAT failures, roadmap was re-scoped:
- v1.3.0 = Stability + analysis (no quiz UI, no progress dashboard, no audio)
- v1.4.0 = Quiz + progress (planned)
- v1.5.0 = Audio playback (planned)
- v1.8.2 = Analysis quality UAT (conditional pass), MIDI P0 resolved (deployed 2026-02-18)
- v1.8.3 = Import pipeline: MuseScore/MusicXML/MIDI universal import, batch ZIP import, 15 jazz standards seeded (deployed 2026-02-21)
- v1.8.4 = Rework sprint: MIDI crash fix (auth.js 5xx handling), chord modal + extensions + bass note, import diagnostic, showToast(), health component field (deployed 2026-02-21)
- v1.8.5 = Error logging standardization (deployed 2026-02-22)
- v1.8.6 = CHD-01 rework: chord dropdowns in Analysis view modal; IMP-03: .mscz MuseScore 4 voice nesting fix (deployed 2026-02-22)
- v2.0.0 = HL-MS1 Mega Sprint: 10 jazz standards imported (HL-008), chord granularity refinement (HL-012), annotated MuseScore export (HL-015), rhythm analysis + MIDI keyboard input (HL-017). MuseScore parser fixes: dual root numbering, harmonyInfo wrapper, N.C. handling. (deployed 2026-02-27)
- v2.0.1 = HL-MS1-FIX: 5 UAT failure fixes. (1) Note/timing visibility: score_parser extracts individual notes from MuseScore XML (handles MS3+MS4 voice formats), notes saved to MelodyNotes, Notes view tab in song.html, reparse-notes endpoint for existing songs. (2) Chord notation: normalizeChordDisplay() converts jazz font (^→maj, -→m, 0→dim, t→maj7). (3) MuseScore export: "Export .mscz" button in song.html. (4) Rhythm analysis: panel shows swing/straight feel, syncopation, source label. (5) Web MIDI: device detection, real-time chord identification via MIDI keyboard. (deployed 2026-02-27)
- v2.1.0 = HL-MS2: 3 UAT fixes + 6 features. (1) Song 65 fix: return empty analysis with helpful message instead of 404. (2) Note extraction [object Object] fix: send song_id as query param, robust error extraction. (3) Roman numeral "?" fix: strip parenthetical extensions, _fallback_roman() for music21 failures. (4) MIDI Quiz Mode: Listen/Quiz toggle, sequential/random chord drill, score tracking. (5) MIDI notes display: real-time note names alongside chord ID. (6) Altered chord templates: 7b9, 7#9, 7b13, 7#11, 7alt, 6/9, m6/9. (7) Delete song UI: button with confirmation dialog. (8) ISO timestamps on docs. (deployed 2026-02-28)

- v2.5.0 = HL-REIMPORT-FIX-001: Import pipeline fix, file provenance (hash, size, modified date), song versioning (duplicate detection, "(2)" suffix), silent failure prevention. Rich note data via song_notes table (Migration 5a). (deployed 2026-03-08)
- v2.6.0 = VERSION bump + import_count on imports endpoint. (deployed 2026-03-11)
- v2.7.0 = HL-MEGA-001: 4 bugs + 5 features (deployed 2026-03-12). Bugs: (1) HL-KEY-FIX-001: Key detection verified correct (C major for Corcovado, not G major). (2) HL-KEYCTR-DISP-001: Key center badge already displayed. (3) HL-TRANSPOSE-FIX-001: Transpose endpoint already functional. (4) HL-NOTES-BUG-001: Fixed notes endpoint to query song_notes table first (327 notes found), fallback to MelodyNotes for legacy data. Root cause: endpoint was only querying MelodyNotes with wrong column names. Features: (5) HL-CHORD-NOTES-001: Note breakdown in chord analysis modal via getChordNotes(). (6) HL-NOTES-CHORD-001: server-provided note_name in Notes table. (7) HL-BULK-DELETE-001: Multi-select checkboxes + DELETE /bulk/delete endpoint. (8) HL-PIANO-LABELS-001: Note name labels (C4, D4...) on piano roll LHS, C notes gold. (9) HL-PIANO-TOOLTIP-001: Canvas mousemove tooltip with note name, octave, MIDI#, duration, chord.

- v2.8.0 = HL-MEGA-002: 2 bugs + 2 features (deployed 2026-03-12). Bugs: (1) BUG-001: Key detection fixed — was using chord symbols only for Krumhansl-Schmuckler, now uses MIDI pitches from song_notes table when available (Corcovado: G major → C major, 0.81 conf). New `_detect_key_from_notes()` method in analysis_service.py. (2) BUG-002: Transpose now re-runs full chord analysis — shifts MIDI pitches by semitones, passes to analyze_song() with key_override=None for fresh key detection (was just renaming the key string). Features: (3) REQ-002: Chord modal shows actual MIDI notes per measure — "Notes in this Measure" table with Beat/Note/MIDI/Duration columns, fetched via GET /songs/{id}/notes?measure=N. (4) REQ-003: Chord assignment transparency — note_count badge ("4n") on each chord tile in analysis view, has_note_data flag in API response.

- v2.10.0 = HL-ALGO-RLHF-001: Jazz algorithm v1.1 + RLHF toggle + provenance (deployed 2026-03-13). 2 bugs + 3 features: (1) BUG-004/HL-006E: MIDI note count badges fixed — MIDI import now extracts individual notes via `extract_notes_from_track()` in midi_parser.py, wired through score_parser → song_notes table. MelodyNotes fallback added in analysis route. (2) BUG-003/HL-006A: Jazz chord detection v1.1 — 5 algorithm changes: jazz 7th bias (7th chords score +100 over triads when extensions present), rootless voicing detection (bass-less 3-5-7 → infer root, base score 1100), duration-weighted scoring (proportional to beat duration, <0.25 beats = 0.1), beat-position weighting (beat 1 = 2.0x, beat 3 = 1.5x, off-beats = 0.75x), cadence-weighted key detection (last 4 measures 3x, final measure 6x). (3) REQ-004/HL-006B: Chord provenance badges — S (grey) for score, A (blue) for algorithm, gold check for override. Source line in chord modal. (4) REQ-006/HL-006D: Rootless voicing explanation — shows in chord modal when root absent from MIDI notes and chord detected via rootless matching. (5) REQ-005/HL-006C: RLHF feedback loop — toggle OFF by default, cross-song learning from ChordAnalysisOverrides (pitch class set → correction evidence), activate/revert endpoints, rlhf_sessions table (Migration 7a), version display (Algorithm v1.1 | RLHF v1.0).

- v2.11.0 = HL-CLOSEOUT-001: Admin closes + score playback + jazz riff library (deployed 2026-03-13). Group A (5 admin closes): HL-034 melody display, HL-036 chord playback, HL-050 full song audio, HL-REIMP-001 import pipeline, HL-AUDIT-UI-FIX-001 audit page — all verified live and walked to done/closed. Group B (2 status resolutions): HL-033 full score capture (327 notes, 48 measures), HL-042 ii-V-I recognition (patterns endpoint detects ii-V-i on MIDI) — both verified working and closed. Group C (2 new features): (1) HL-035: Note-level score playback — Score mode toggle in playback transport fetches MIDI notes from /api/v1/songs/{id}/notes, schedules individual pitches via Tone.Part with Salamander sampler, respects currentTranspose offset, duration calculated from BPM. (2) HL-048: Jazz riff library — /api/v1/riffs/ endpoint with 10 curated riffs (ii-V-I, bebop scale, Parker turnaround, tritone sub, Coltrane changes, blues scale, rhythm changes, Autumn Leaves ii-V, modal vamp, chromatic approach), each with MIDI note data for Tone.js playback. Frontend riffs.html with card grid, key/tag filtering, play button per riff. Riffs nav link added to all pages.

- v2.12.0 = HL-REGRESSIONS-001: 3 regression fixes (deployed 2026-03-14). (1) Fix 1: Note count badges now display in both "analysis" and "chords" views (was only showing in analysis view, PL couldn't see badges in chords view). (2) Fix 2: Transpose chord symbol spelling — `transpose_chord_symbol()` now uses flat names for pitch classes 1/3/6/8/10 (Db/Eb/Gb/Ab/Bb), fixing roman numeral nonsense like `#IIMaj9` which should be `IIIMaj9`. Root cause: original logic used sharps for natural-root chords transposed up. (3) Fix 3: Score playback rework — `togglePlayPause()` now reloads `scorePart` when in score mode after stop (was only reloading chord `part`), play button shows "Score" label when in score mode.

- v2.13.0 = HL-TRANSPOSE-001: Transpose chord symbol display + roman numeral fix (deployed 2026-03-14). (1) Frontend chord symbol update: `renderAnalysis()` now writes transposed `ac.symbol` to a stored `symbolElement` reference. Previously, only roman numerals, colors, and badges were updated — chord symbol text was never touched after initial load. (2) Sharp roman numeral elimination: Post-process in `transpose_song()` converts `#III→bIV`, `#IV→bV`, `#V→bVI` etc. for both uppercase (major) and lowercase (minor) roman numerals. Regex matches `#(VII|...|i)` and maps to `b` + next degree. (3) Piano roll re-render: `setupPianoRoll()` now called in `renderAnalysis()` so piano roll reflects transposed chord tones.

### What's Next (updated 2026-03-14)
| ID | Feature | Priority | Status |
|----|---------|----------|--------|
| HL-003 | Show intervals on chord display | P2 | Open |
| HL-004 | Next-chord progression quiz UI | P2 | Open |
| HL-005 | Audio playback (Tone.js integration) | P2 | Open |
| HL-NEW-001 | MIDI Quiz Mode | P2 | **DONE** (v2.1.0) |
| HL-NEW-002 | MIDI notes display | P2 | **DONE** (v2.1.0) |
| HL-NEW-003 | Altered chord templates (7b9, 7#9, etc.) | P2 | **DONE** (v2.1.0) |
| HL-NEW-004 | Roman numeral "?" fix | P3 | **DONE** (v2.1.0) |
| HL-NEW-005 | Delete song UI | P3 | **DONE** (v2.1.0) |
| HL-015 | Annotated MuseScore export | P3 | **DONE** (v2.0.0) |
| HL-016 | Melody analysis | P3 | Done (v1.8.3) |
| HL-017 | Rhythm analysis + MIDI keyboard input | P3 | **DONE** (v2.0.0) |

Source: Handoff architectural decisions file in `handoffs/inbox/`.

### Target Song Repertoire
37 jazz standards listed in `HarmonyLab-Kickoff.md`. **27+ currently in DB** (2026-02-27 post v2.0.0): 15 seeded jazz standards + 10 imported from .mscz files (HL-MS1) + 2 legacy MIDI imports. Batch import via ZIP is now available for any additional file uploads.

---

## Documentation Sources Inventory

### Files Read and Cited

| File Path | Type | Key Content |
|-----------|------|-------------|
| `CLAUDE.md` | AI Instructions | Project identity, GCP values, deployment, secrets, compliance |
| `README.md` | Project overview | Architecture, tech stack summary |
| `ROADMAP.md` | Development roadmap | 8 phases, time estimates |
| `QUICKSTART.md` | Setup guide | Local development steps |
| `PROJECT-STATUS.md` | Status (older) | Dec 27, 2025 snapshot |
| `PROJECT_STATUS.md` | Status (current) | Jan 28, 2025, 36 endpoints, Sprint 1 complete |
| `SETUP-COMPLETE.md` | Setup summary | Initial project setup confirmation |
| `SPRINT2-COMPLETE.md` | Sprint 2 deliverables | Sprint 2 completion summary |
| `HarmonyLab-Kickoff.md` | Full project vision | 37-song repertoire, data architecture, UI/UX, quiz algorithm |
| `HARMONYLAB-CLOUD-MIGRATION.md` | Cloud migration guide | Cloud-first architecture decisions |
| `HARMONYLAB-DB-SETUP.md` | Database setup | Connection instructions, schema execution |
| `HARMONYLAB-SPRINT2-HANDOFF.md` | Sprint 2 handoff | Architect-to-coder handoff instructions |
| `HARMONYLAB-VSCODE-KICKOFF.md` | VS Code AI instructions | Coder-role AI instructions |
| `harmony-lab-infra-setup.md` | GCP infrastructure | Cloud Run, Cloud SQL, Secret Manager setup |
| `HarmonyLab_LeadSheet_Analysis_Design.md` | Feature design | v1.3.0 lead sheet analysis feature |
| `HarmonyLab_Sprint_Analysis_v1.3.0.md` | Sprint analysis | v1.3.0 sprint plan |
| `main.py` | App entry point | FastAPI app, VERSION, middleware, routers |
| `config/settings.py` | Configuration | Secret Manager integration, OAuth settings |
| `app/db/connection.py` | Database layer | Database and DatabaseConnection classes |
| `app/models/__init__.py` | Data models | All Pydantic models |
| `app/services/score_parser.py` | Universal parser | .mscz/.mscx (ET XML), .musicxml (music21), .mid (mido delegate). ParsedScore + ScoreChord dataclasses |
| `app/services/midi_parser.py` | MIDI parser | mido-based chord detection |
| `app/services/analysis_service.py` | Analysis | music21 harmonic analysis |
| `app/services/score_exporter.py` | MuseScore export | Generates annotated .mscx/.mscz with chord symbols + Roman numerals *(added 2026-02-27)* |
| `app/services/rhythm_analyzer.py` | Rhythm analysis | Swing/straight detection, syncopation, subdivision analysis *(added 2026-02-27)* |
| `app/services/auth_service.py` | Auth service | JWT token management |
| `app/migrations.py` | Migrations | 4 idempotent schema migrations |
| `app/api/routes/songs.py` | Songs API | CRUD endpoints |
| `app/api/routes/sections.py` | Sections API | Section management |
| `app/api/routes/vocabulary.py` | Vocabulary API | Chord/Roman numeral lookups |
| `app/api/routes/measures.py` | Measures API | Measure CRUD |
| `app/api/routes/chords.py` | Chords API | Chord CRUD + bulk create |
| `app/api/routes/progress.py` | Progress API | Progress tracking, stats, history |
| `app/api/routes/quiz.py` | Quiz API | Generate, submit, attempts |
| `app/api/routes/imports.py` | Imports API | MIDI import, MusicXML placeholder |
| `app/api/routes/analysis.py` | Analysis API | Harmonic analysis, overrides |
| `app/api/routes/exports.py` | Exports API | MuseScore export with analysis annotations *(added 2026-02-27)* |
| `app/api/routes/midi_input.py` | MIDI Input API | Real-time chord ID, rhythm analysis, Web MIDI *(added 2026-02-27)* |
| `app/api/routes/auth.py` | Auth API | Google OAuth, JWT, user management |
| `test_connection.py` | Test script | Database connection verification |
| `Dockerfile` | Container | Python 3.12 + ODBC Driver 17 |
| `requirements.txt` | Dependencies | 13 Python packages |
| `.env.example` | Env template | DB, API, CORS, GCS config vars |
| `.gitignore` | Git ignore | Standard Python + env exclusions |
| `.github/workflows/deploy.yml` | CI/CD | GitHub Actions, WIF, Cloud Run deploy |
| `.vscode/settings.json` | VS Code config | Peacock color settings |
| `HarmonyLab-Schema-v1.0.sql` | SQL schema | 9 tables, seed data, view, stored procedure |
| `HarmonyLab-Schema-CloudSQL.sql` | SQL schema (Cloud) | Cloud SQL compatible version |
| `frontend/Dockerfile` | Frontend container | Exists but not read (frontend source files missing) |
| `handoffs/inbox/*.md` | Handoff files | UAT results, investigation, architectural decisions |
| `handoffs/outbox/*.md` | Handoff files | Outbound handoffs |

### Files NOT Found / Missing
| Expected | Status |
|----------|--------|
| `frontend/` source files (HTML, JS, CSS) | EMPTY -- no tracked frontend source files. `frontend/Dockerfile` exists. |
| `tests/` directory | NOT DOCUMENTED -- no test files found in project. 0% coverage confirmed in `PROJECT_STATUS.md`. |
| `UI_DESIGN.md` | Referenced in `PROJECT_STATUS.md` line 76 but not found in project root |
| `TEST_PLAN.md` | Referenced in `PROJECT_STATUS.md` line 77 but not found in project root |
| `USER_GUIDE.md` | Referenced in `PROJECT_STATUS.md` line 78 but not found in project root |
| `.env` file | Not tracked (correctly in `.gitignore`). Template available as `.env.example`. |

---

*End of PROJECT_KNOWLEDGE.md*
